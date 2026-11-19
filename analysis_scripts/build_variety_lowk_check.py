#!/usr/bin/env python3
"""Oracle headroom on Variety restricted to low-visibility objects (k < 5).

More than 90% of anomalous Variety objects show the defect in all five views, so
for most objects the oracle removes nothing and coincides with the mean by
construction. This script repeats the oracle-mean vs mean comparison of
Section 6.2 after dropping anomalous objects with k = 5. Normal objects are
always kept: k is only defined for anomalous objects, and AUROC needs both
classes. Category remains the sampling unit.

Reads raw prediction NPZ files only; writes paper_assets/results/variety_lowk_headroom.csv.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import stats

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"

# VisualAD is the trained family: one model per source fold, five folds averaged
# inside a category before pairing, exactly as in build_section6_assets.py.
VISUALAD = ("VisualAD-Acontinued", [EXP / f"runs/fold_{f:02d}/seed_00/A_continued/eval/predictions_variety.npz"
                                    for f in range(5)])
BASELINES = {
    "AnomalyCLIP-VisA": EXP / "baselines/anomalyclip_visa/variety/seed_00/AnomalyCLIP/eval/predictions_variety.npz",
    "WinCLIP": EXP / "baselines/winclip/variety/seed_00/WinCLIP/eval/predictions_variety.npz",
    "Cross-view NN": EXP / "baselines/crossview_nn/variety/seed_00/CrossViewNN/eval/predictions_variety.npz",
}


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def scores_mean(s, v):
    return np.asarray([np.asarray(a)[np.asarray(b, bool)].mean() for a, b in zip(s, v)])


def scores_oracle_mean(s, v, il, y):
    out = []
    for a, b, l, lab in zip(s, v, il, y):
        b = np.asarray(b, bool)
        sel = (np.asarray(l, bool) & b) if lab else b
        out.append(np.asarray(a)[sel].mean())
    return np.asarray(out)


def per_category_delta(path):
    """Return {category: oracle_mean_auroc - mean_auroc} on the k < 5 subset."""
    z = np.load(path, allow_pickle=True)
    cats, y, k = z["category"], z["object_label"].astype(int), z["k"].astype(int)
    s, v, il = z["view_scores"], z["valid"].astype(bool), z["image_labels"].astype(bool)
    keep = (y == 0) | (k < 5)
    cats, y, s, v, il = cats[keep], y[keep], s[keep], v[keep], il[keep]
    m, o = scores_mean(s, v), scores_oracle_mean(s, v, il, y)
    out = {}
    for c in sorted(set(cats.tolist())):
        q = cats == c
        a_m, a_o = auroc(m[q], y[q]), auroc(o[q], y[q])
        if np.isfinite(a_m) and np.isfinite(a_o):
            out[c] = a_o - a_m
    return out, int((y == 1).sum())


def ci_t(x):
    x = np.asarray(x, float)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    return float(x.mean()), float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue)


def main():
    rows = []

    name, paths = VISUALAD
    folds = [per_category_delta(p) for p in paths]
    n_anom = folds[0][1]
    if any(f[1] != n_anom for f in folds):
        raise SystemExit("folds disagree on the number of retained anomalous objects")
    common = sorted(set.intersection(*[set(f[0]) for f in folds]))
    d = np.array([np.mean([f[0][c] for f in folds]) for c in common])
    m, lo, hi, p = ci_t(d)
    rows.append({"detector": name, "n_categories": len(common), "n_anomalous_objects": n_anom,
                 "delta_vs_mean": m, "ci_low": lo, "ci_high": hi, "p_vs_mean": p})

    for name, path in BASELINES.items():
        per_cat, n_anom = per_category_delta(path)
        d = np.array([per_cat[c] for c in sorted(per_cat)])
        m, lo, hi, p = ci_t(d)
        rows.append({"detector": name, "n_categories": len(per_cat), "n_anomalous_objects": n_anom,
                     "delta_vs_mean": m, "ci_low": lo, "ci_high": hi, "p_vs_mean": p})

    fields = ["detector", "n_categories", "n_anomalous_objects",
              "delta_vs_mean", "ci_low", "ci_high", "p_vs_mean"]
    out = CSV_DIR / "variety_lowk_headroom.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("wrote", out.name)
    for r in rows:
        print(f"  {r['detector']:<20} n_cat={r['n_categories']:>3}  n_anom={r['n_anomalous_objects']:>4}  "
              f"{r['delta_vs_mean']:+.2f} [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]")


if __name__ == "__main__":
    main()
