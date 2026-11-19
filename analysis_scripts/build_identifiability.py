#!/usr/bin/env python3
"""Is the oracle headroom out of reach because the information is absent from the
five scalars, or because no rule that must generalise across categories finds it?

Two measurements, both on Real-IAD, both macro-averaged by category.

1. Visibility recoverability. Within anomalous objects, can the per-view score
   tell a view that sees the defect from a view that does not? Objects with k = 5
   contribute no negative view, so the statistic is computed on k < 5 objects.
   An AUROC well above 50 means the latent visibility variable is partly
   recoverable from the scores themselves.

2. Within-category ceiling. A logistic regression on the five view scores fitted
   and evaluated inside the same category, by two-fold cross-validation over the
   objects of that category. This is NOT a valid zero-shot aggregator: it sees
   labels of the category it scores. It is a reference ceiling for what the scalar
   family can express when generalisation across categories is not required.
   Reported for sorted scores and for camera-ordered scores, since sorting is what
   the paper's deployable learned aggregators do.

Reads raw prediction NPZ files; writes identifiability.csv.
"""
from __future__ import annotations

import csv
import glob
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"
SEED = 0

DETECTORS = {
    "VisualAD-A": str(EXP / "runs/fold_*/seed_00/A/eval/predictions_fold*.npz"),
    "VisualAD-Acontinued": str(EXP / "runs/fold_*/seed_00/A_continued/eval/predictions_fold*.npz"),
    "VisualAD-F": str(EXP / "runs/fold_*/seed_00/F/eval/predictions_fold*.npz"),
    "AnomalyCLIP-VisA": str(EXP / "baselines/anomalyclip_visa/fold_*/seed_00/AnomalyCLIP/eval/predictions_fold*_shard*of2.npz"),
    "WinCLIP": str(EXP / "baselines/winclip/fold_*/seed_00/WinCLIP/eval/predictions_fold*.npz"),
    "Cross-view NN": str(EXP / "baselines/crossview_nn/fold_*/seed_00/CrossViewNN/eval/predictions_fold*.npz"),
}


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def ci_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    return float(x.mean()), float(lo), float(hi), len(x)


def visibility_auroc(s, v, il, y):
    """Per-view score against per-view defect presence, inside anomalous objects."""
    sc, lab = [], []
    for a, b, l, t in zip(s, v, il, y):
        if not t:
            continue
        b = np.asarray(b, bool)
        a, l = np.asarray(a)[b], np.asarray(l, bool)[b]
        if l.all() or not l.any():
            continue
        sc.append(a); lab.append(l.astype(int))
    if not sc:
        return np.nan
    return auroc(np.concatenate(sc), np.concatenate(lab))


def ceiling(X, y, seed=SEED):
    """Two-fold within-category CV AUROC of a logistic regression on X."""
    if y.sum() < 2 or (y == 0).sum() < 2:
        return np.nan
    out = np.empty(len(y), float)
    skf = StratifiedKFold(n_splits=2, shuffle=True, random_state=seed)
    for tr, te in skf.split(X, y):
        if y[tr].sum() == 0 or (y[tr] == 0).sum() == 0:
            return np.nan
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        clf = LogisticRegression(max_iter=2000)
        clf.fit((X[tr] - mu) / sd, y[tr])
        out[te] = clf.decision_function((X[te] - mu) / sd)
    return auroc(out, y)


def main():
    rows = []
    for name, pattern in DETECTORS.items():
        vis, d_sorted, d_camera = [], [], []
        for path in sorted(glob.glob(pattern)):
            z = np.load(path, allow_pickle=True)
            cats, y = z["category"], z["object_label"].astype(int)
            s, v, il = z["view_scores"], z["valid"].astype(bool), z["image_labels"].astype(bool)
            m = np.asarray([np.asarray(a)[np.asarray(b, bool)].mean() for a, b in zip(s, v)])
            for c in sorted(set(cats.tolist())):
                q = cats == c
                vis.append(visibility_auroc(s[q], v[q], il[q], y[q]))
                base = auroc(m[q], y[q])
                Xc = np.where(v[q], s[q], np.nan)
                Xc = np.where(np.isnan(Xc), np.nanmean(Xc, axis=1, keepdims=True), Xc)
                Xs = np.sort(Xc, axis=1)[:, ::-1]
                d_camera.append(ceiling(Xc, y[q]) - base)
                d_sorted.append(ceiling(Xs, y[q]) - base)
        a, alo, ahi, na = ci_t(vis)
        b, blo, bhi, nb = ci_t(d_sorted)
        d, dlo, dhi, nd = ci_t(d_camera)
        rows.append({"detector": name,
                     "visibility_auroc": a, "vis_ci_low": alo, "vis_ci_high": ahi,
                     "n_categories_visibility": na,
                     "ceiling_sorted_vs_mean": b, "sorted_ci_low": blo, "sorted_ci_high": bhi,
                     "ceiling_camera_vs_mean": d, "camera_ci_low": dlo, "camera_ci_high": dhi,
                     "n_categories_ceiling": nd})
        print(f"  {name:<22} visibility AUROC {a:5.1f} [{alo:.1f}, {ahi:.1f}]   "
              f"ceiling sorted {b:+.2f} [{blo:+.2f}, {bhi:+.2f}]   "
              f"camera {d:+.2f} [{dlo:+.2f}, {dhi:+.2f}]")

    fields = ["detector", "visibility_auroc", "vis_ci_low", "vis_ci_high",
              "n_categories_visibility", "ceiling_sorted_vs_mean", "sorted_ci_low",
              "sorted_ci_high", "ceiling_camera_vs_mean", "camera_ci_low", "camera_ci_high",
              "n_categories_ceiling"]
    out = CSV_DIR / "identifiability.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("wrote", out.name)


if __name__ == "__main__":
    main()
