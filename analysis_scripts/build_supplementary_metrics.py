#!/usr/bin/env python3
"""Robustness of the main comparison under two further object-level metrics.

S-AUROC is the primary metric of the paper because it is invariant to the class
ratio, which varies across the 30 Real-IAD categories and would otherwise mix a
method effect with a data-structure effect under macro-averaging. That choice
should not be load-bearing, so this script recomputes the central comparison
under S-AP and S-F1max from the same stored object scores. No extra inference
is required.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import average_precision_score, precision_recall_curve

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"

VARIANTS = {"VisualAD-A": "A", "VisualAD-Acontinued": "A_continued", "VisualAD-F": "F"}
PRETTY = {"VisualAD-A": "f_base", "VisualAD-Acontinued": "f_budget", "VisualAD-F": "f_mv"}


def auroc(s, y):
    npos, nneg = int(y.sum()), int((y == 0).sum())
    r = stats.rankdata(s)
    return 100 * float(r[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def f1max(y, s):
    p, r, _ = precision_recall_curve(y, s)
    return 100 * float(np.nanmax(2 * p * r / np.clip(p + r, 1e-12, None)))


def main():
    per = {}
    for name, variant in VARIANTS.items():
        rows = {}
        for f in range(5):
            z = np.load(EXP / f"runs/fold_{f:02d}/seed_00/{variant}/eval/predictions_fold{f}.npz",
                        allow_pickle=True)
            s = z["view_scores"].mean(1)
            y = z["object_label"].astype(int)
            cats = z["category"]
            for c in sorted(set(cats.tolist())):
                m = cats == c
                rows[c] = {"s_auroc": auroc(s[m], y[m]),
                           "s_ap": 100 * average_precision_score(y[m], s[m]),
                           "s_f1max": f1max(y[m], s[m])}
        per[name] = rows

    cats = sorted(per["VisualAD-A"])
    out = [{"detector": PRETTY[n], "category": c, **{k: v for k, v in per[n][c].items()}}
           for n in VARIANTS for c in cats]
    with (CSV_DIR / "supplementary_metrics_by_category.csv").open("w", newline="",
                                                                 encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["detector", "category", "s_auroc", "s_ap", "s_f1max"])
        w.writeheader(); w.writerows(out)

    summary = []
    for left, right in (("VisualAD-A", "VisualAD-Acontinued"),
                        ("VisualAD-Acontinued", "VisualAD-F")):
        for metric in ("s_auroc", "s_ap", "s_f1max"):
            a = np.array([per[left][c][metric] for c in cats])
            b = np.array([per[right][c][metric] for c in cats])
            d = b - a
            se = stats.sem(d)
            lo, hi = stats.t.interval(0.95, len(d) - 1, loc=d.mean(), scale=se)
            summary.append({"comparison": f"{PRETTY[right]} - {PRETTY[left]}",
                            "metric": metric, "n_categories": len(cats),
                            "left": float(a.mean()), "right": float(b.mean()),
                            "difference": float(d.mean()), "ci_low": float(lo),
                            "ci_high": float(hi),
                            "p_value": float(stats.ttest_1samp(d, 0).pvalue),
                            "n_right_higher": int((d > 0).sum())})
    with (CSV_DIR / "supplementary_metrics_summary.csv").open("w", newline="",
                                                             encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)

    # Rank agreement: if the three metrics ordered categories differently, a
    # macro-average of them would not be comparable at all.
    base = np.array([per["VisualAD-Acontinued"][c]["s_auroc"] for c in cats])
    for metric in ("s_ap", "s_f1max"):
        other = np.array([per["VisualAD-Acontinued"][c][metric] for c in cats])
        print(f"Spearman(S-AUROC, {metric}) across categories = "
              f"{stats.spearmanr(base, other).statistic:+.3f}")
    for r in summary:
        print(f"  {r['comparison']:24s} {r['metric']:9s} {r['left']:6.2f} -> {r['right']:6.2f}  "
              f"{r['difference']:+.2f} [{r['ci_low']:+.2f},{r['ci_high']:+.2f}] "
              f"p={r['p_value']:.4f}  higher in {r['n_right_higher']}/30")
    print("wrote supplementary_metrics_by_category.csv, supplementary_metrics_summary.csv")


if __name__ == "__main__":
    main()
