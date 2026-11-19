#!/usr/bin/env python3
"""Aggregation analysis of the three independent detector families on Variety.

The three families are training-free or use a fixed published checkpoint, so one
inference pass covers all 160 categories. Each is scored on exactly the same
16,000 sample_ids as the VisualAD checkpoints, which is what makes the four
families comparable on the same rows.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import stats

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
B = ROOT / "research/mv_zsad_experiments/baselines"
CSV_DIR = PAPER / "paper_assets/results"

SOURCES = {
    "WinCLIP": B / "winclip/variety/seed_00/WinCLIP/eval/predictions_variety.npz",
    "AnomalyCLIP-VisA": B / "anomalyclip_visa/variety/seed_00/AnomalyCLIP/eval/predictions_variety.npz",
    "Cross-view NN": B / "crossview_nn/variety/seed_00/CrossViewNN/eval/predictions_variety.npz",
}
RULES = ("mean", "max", "top2", "top3", "median", "oracle_mean", "oracle_max")


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def combine(scores, valid, rule, image_labels=None, object_labels=None):
    out = []
    for i, (s, v) in enumerate(zip(scores, valid)):
        v = np.asarray(v, bool)
        if rule.startswith("oracle"):
            sel = (np.asarray(image_labels[i], bool) & v) if object_labels[i] else v
            x = np.asarray(s)[sel]
            out.append(x.max() if rule == "oracle_max" else x.mean())
            continue
        x = np.asarray(s)[v]
        out.append({"mean": x.mean, "max": x.max}.get(rule, lambda: None)() if rule in ("mean", "max")
                   else np.median(x) if rule == "median"
                   else np.sort(x)[::-1][:int(rule[3:])].mean())
    return np.asarray(out)


def ci_t(x):
    se = stats.sem(x)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=se)
    return float(x.mean()), float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue)


def main():
    ref = None
    rows, summary = [], []
    for name, path in SOURCES.items():
        z = np.load(path, allow_pickle=True)
        ids = set(z["sample_id"].tolist())
        if ref is None:
            ref = ids
        elif ids != ref:
            raise SystemExit(f"{name}: sample_id set differs from the other detectors")
        cats, y = z["category"], z["object_label"].astype(int)
        sc, va = z["view_scores"], z["valid"].astype(bool)
        il = z["image_labels"].astype(bool)
        per = {}
        for c in sorted(set(cats.tolist())):
            q = cats == c
            per[c] = {r: auroc(combine(sc[q], va[q], r, il[q], y[q]), y[q]) for r in RULES}
            per[c]["i_auroc"] = auroc(sc[q][va[q]], il[q][va[q]].astype(int))
            rows.append({"detector": name, "category": c, **per[c]})
        keys = sorted(per)
        base = np.array([per[c]["mean"] for c in keys])
        for r in RULES:
            vals = np.array([per[c][r] for c in keys])
            if r == "mean":
                m, lo, hi, p = 0.0, 0.0, 0.0, 1.0
            else:
                m, lo, hi, p = ci_t(vals - base)
            summary.append({"detector": name, "aggregation": r, "n_categories": len(keys),
                            "s_auroc": float(vals.mean()), "delta_vs_mean": m,
                            "ci_low": lo, "ci_high": hi, "p_vs_mean": p})
        print(f"{name:18s} mean {base.mean():6.2f}  "
              + "  ".join(f"{r}={next(s['delta_vs_mean'] for s in summary if s['detector']==name and s['aggregation']==r):+.2f}"
                          for r in ("max", "top2", "top3", "median", "oracle_mean")))

    with (CSV_DIR / "variety_baselines_by_category.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (CSV_DIR / "variety_baselines_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    print("\nwrote variety_baselines_by_category.csv, variety_baselines_summary.csv")
    print("all three detectors scored on an identical sample_id set")


if __name__ == "__main__":
    main()
