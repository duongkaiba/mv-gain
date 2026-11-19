#!/usr/bin/env python3
"""Recompute learned scalar-score aggregators from raw prediction NPZ files.

Two aggregators are fitted on the five sorted view scores of an object:

  * logistic regression on the raw sorted scores;
  * a gated L-estimator whose softmax gate is computed from the per-object
    standardized sorted scores, so the output is a convex combination of the
    five scores and is invariant to a per-object shift.

Both are fitted with leave-one-fold-out cross-validation over the five
leave-category-out folds, so every category is scored by a model that never
saw it. Outputs are written at category level, which is the sampling unit
used for all inference in the paper.

This script supersedes the hard-coded summary previously carried in
build_section5_assets.py.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from scipy import stats
from sklearn.linear_model import LogisticRegression

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"

VARIANTS = {"VisualAD-A": "A",
            "VisualAD-Acontinued": "A_continued",
            "VisualAD-F": "F"}
SEED = 0
EPOCHS = 300
LR = 3e-3


class GatedL(nn.Module):
    """Convex combination of order statistics with a shift-invariant gate."""

    def __init__(self, n_views: int = 5, hidden: int = 16):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(n_views, hidden), nn.Tanh(),
                                 nn.Linear(hidden, n_views))

    def forward(self, x):
        mu = x.mean(1, keepdim=True)
        sd = x.std(1, keepdim=True) + 1e-6
        return (torch.softmax(self.net((x - mu) / sd), 1) * x).sum(1)


def auroc(scores, labels) -> float:
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return float("nan")
    ranks = stats.rankdata(scores)
    return float(ranks[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def ci_t(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    se = stats.sem(x)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=se)
    return float(x.mean()), float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue)


def load_variant(variant: str):
    """Return sorted view scores, labels, category and fold index per object."""
    sorted_scores, labels, categories, folds = [], [], [], []
    for f in range(5):
        path = EXP / f"runs/fold_{f:02d}/seed_00/{variant}/eval/predictions_fold{f}.npz"
        z = np.load(path, allow_pickle=True)
        valid = z["valid"].astype(bool)
        if not valid.all():
            raise SystemExit(f"{path}: invalid views are not handled by this script")
        x = -np.sort(-z["view_scores"].astype(np.float32), axis=1)
        sorted_scores.append(x)
        labels.append(z["object_label"].astype(int))
        categories.append(z["category"])
        folds.append(np.full(len(x), f))
    return (np.concatenate(sorted_scores), np.concatenate(labels),
            np.concatenate(categories), np.concatenate(folds))


def fit_gated(x_train, y_train, cat_train):
    torch.manual_seed(SEED)
    model = GatedL(x_train.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    xt = torch.tensor(x_train)
    yt = torch.tensor(y_train).float()
    groups = [np.where(cat_train == c)[0] for c in sorted(set(cat_train.tolist()))]
    for _ in range(EPOCHS):
        opt.zero_grad()
        loss = 0.0
        for idx in groups:
            score = model(xt[idx])
            pos, neg = score[yt[idx] > 0], score[yt[idx] == 0]
            # Per-category pairwise ranking loss: the metric is a within-category
            # AUROC, so the objective must not compare objects across categories.
            loss = loss + nn.functional.softplus(-(pos[:, None] - neg[None, :])).mean()
        (loss / len(groups)).backward()
        opt.step()
    return model


def main():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    per_category, summary = [], []

    for name, variant in VARIANTS.items():
        x, y, cat, fold = load_variant(variant)
        rows = {}
        for held_out in range(5):
            te, tr = fold == held_out, fold != held_out
            logistic = LogisticRegression(max_iter=2000).fit(x[tr], y[tr])
            score_lr = logistic.decision_function(x[te])
            gated = fit_gated(x[tr], y[tr], cat[tr])
            with torch.no_grad():
                score_gl = gated(torch.tensor(x[te])).numpy()
            for c in sorted(set(cat[te].tolist())):
                m = cat[te] == c
                rows[c] = {
                    "detector": name, "category": c, "held_out_fold": held_out,
                    "n_objects": int(m.sum()),
                    "s_auroc_mean": 100 * auroc(x[te][m].mean(1), y[te][m]),
                    "s_auroc_top2": 100 * auroc(x[te][m][:, :2].mean(1), y[te][m]),
                    "s_auroc_logistic": 100 * auroc(score_lr[m], y[te][m]),
                    "s_auroc_gated": 100 * auroc(score_gl[m], y[te][m]),
                }
        ordered = [rows[c] for c in sorted(rows)]
        per_category += ordered

        base = np.array([r["s_auroc_mean"] for r in ordered])
        for method, key in (("mean", "s_auroc_mean"), ("top2", "s_auroc_top2"),
                            ("logistic_regression", "s_auroc_logistic"),
                            ("gated_L_estimator", "s_auroc_gated")):
            vals = np.array([r[key] for r in ordered])
            if method == "mean":
                delta, lo, hi, p = 0.0, 0.0, 0.0, 1.0
            else:
                delta, lo, hi, p = ci_t(vals - base)
            summary.append({"detector": name, "method": method,
                            "n_categories": len(vals), "s_auroc": vals.mean(),
                            "delta_vs_mean": delta, "ci_low": lo, "ci_high": hi,
                            "p_vs_mean": p,
                            "source": "recomputed from raw predictions"})
        print(f"{name}: " + "  ".join(
            f"{s['method']}={s['s_auroc']:.2f}({s['delta_vs_mean']:+.2f})"
            for s in summary if s["detector"] == name))

    with (CSV_DIR / "learned_aggregation_by_category.csv").open("w", newline="",
                                                               encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_category[0]))
        w.writeheader(); w.writerows(per_category)
    with (CSV_DIR / "learned_aggregation_summary.csv").open("w", newline="",
                                                            encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    print(f"\nwrote {CSV_DIR/'learned_aggregation_by_category.csv'}")
    print(f"wrote {CSV_DIR/'learned_aggregation_summary.csv'}")


if __name__ == "__main__":
    main()
