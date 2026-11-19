#!/usr/bin/env python3
"""The evaluation protocol, drawn from the locked fold file itself.

Panel (a) shows how the 30 Real-IAD categories become five leave-category-out
folds: near-duplicate categories are first bundled into semantic units so that
no pair can straddle a split, and each category is tested exactly once.
Panel (b) shows why all five folds are reported rather than one, using the
measured per-fold spread of the baseline detector.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
FIG_DIR = PAPER / "paper_assets/figures"
CSV_DIR = PAPER / "paper_assets/results"

FILL = {"train": "#e8eef4", "val": "#fdebd0", "test": "#f6c6b8"}
EDGE = {"train": "#9fb6c8", "val": "#e0a94a", "test": "#c0392b"}


def per_fold_baseline():
    """Macro S-AUROC of the equal-budget control, recomputed per fold."""
    from scipy import stats
    out = []
    for f in range(5):
        z = np.load(EXP / f"runs/fold_{f:02d}/seed_00/A/eval/predictions_fold{f}.npz",
                    allow_pickle=True)
        s = z["view_scores"].mean(1)
        y = z["object_label"].astype(int)
        c = z["category"]
        vals = []
        for cat in sorted(set(c.tolist())):
            m = c == cat
            yy, ss = y[m], s[m]
            npos, nneg = int(yy.sum()), int((yy == 0).sum())
            r = stats.rankdata(ss)
            vals.append(100 * (r[yy == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))
        out.append(float(np.mean(vals)))
    return out


def main():
    folds = json.loads((EXP / "protocol/folds.json").read_text())
    groups = folds["groups"]
    pairs = folds["semantic_groups"]
    cats = sorted(folds["categories"])
    scores = per_fold_baseline()

    plt.rcParams.update({"font.size": 8, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 300,
                         "pdf.fonttype": 42})
    fig = plt.figure(figsize=(7.0, 4.6))
    gs = fig.add_gridspec(2, 1, hspace=.30, height_ratios=[1.75, 1])

    # ---- panel a: the fold matrix ------------------------------------------
    ax = fig.add_subplot(gs[0])
    ax.set(xlim=(-2.2, len(cats) + 6.0), ylim=(-4.6, 5.3)); ax.axis("off")
    role = {}
    for i, f in enumerate(folds["folds"]):
        for r in ("train", "val", "test"):
            for c in f[r]:
                role[(i, c)] = r
    bundled = {c for p in pairs for c in p}
    for j, c in enumerate(cats):
        for i in range(5):
            r = role[(i, c)]
            ax.add_patch(FancyBboxPatch((j + .08, 4.3 - i * .74), .84, .62,
                                        boxstyle="round,pad=0.01",
                                        fc=FILL[r], ec=EDGE[r], lw=.55))
        ax.text(j + .5, .52, c.replace("_", " "), rotation=90, ha="center",
                va="top", fontsize=5.1,
                color="#c0392b" if c in bundled else "#555555")
    for i in range(5):
        ax.text(-.15, 4.61 - i * .74, f"fold {i}", ha="right", va="center", fontsize=6.8)

    legend = (("train", "18 train", 4.55), ("val", "6 validation", 3.75),
              ("test", "6 test", 2.95))
    for r, text, y in legend:
        ax.add_patch(FancyBboxPatch((len(cats) + .55, y - .21), .55, .42,
                                    boxstyle="round,pad=0.01",
                                    fc=FILL[r], ec=EDGE[r], lw=.55))
        ax.text(len(cats) + 1.30, y, text, fontsize=6.3, va="center", color=EDGE[r])
    ax.text(-2.1, -4.25,
            f"Category names in red belong to one of the {len(pairs)} semantic bundles that "
            "are never split across folds,\nfor example plastic nut with plastic plug. "
            "Each category is tested exactly once.",
            fontsize=6.1, color="#555555", va="bottom")

    # ---- panel b: why every fold is reported --------------------------------
    ax = fig.add_subplot(gs[1])
    x = np.arange(5)
    ax.bar(x, scores, .52, color="#1b4f72", zorder=3)
    mean = float(np.mean(scores))
    ax.axhline(mean, color="#c0392b", lw=1.0, ls="--", zorder=4)
    ax.text(-.62, 94.6, f"dashed line: mean {mean:.2f}", fontsize=6.4, color="#c0392b", va="top")
    for xi, v in zip(x, scores):
        ax.text(xi, v + .5, f"{v:.2f}", ha="center", fontsize=6.6)
    lo, hi = min(scores), max(scores)
    ax.annotate("", xy=(5.05, lo), xytext=(5.05, hi),
                arrowprops=dict(arrowstyle="<->", lw=.9, color="#555555"))
    ax.text(5.22, (lo + hi) / 2,
            f"spread {hi - lo:.2f} points,\n{(hi - lo) / 2.13:.1f} times the largest\nmethod effect measured",
            fontsize=6.3, va="center", color="#555555")
    ax.set(xticks=x, xticklabels=[f"fold {i}" for i in x],
           ylabel="Macro S-AUROC", ylim=(70, 96), xlim=(-.75, 7.2))
    ax.tick_params(labelsize=6.8)
    ax.yaxis.label.set_size(7.5)
    ax.grid(axis="y", alpha=.18, lw=.6, zorder=0)
    plt.savefig(FIG_DIR / "fig4_1_protocol.pdf", bbox_inches="tight")
    plt.savefig(FIG_DIR / "fig4_1_protocol.png", bbox_inches="tight")
    plt.close()
    print("wrote fig4_1_protocol")
    print("  per-fold:", " ".join(f"{s:.2f}" for s in scores),
          f" spread={max(scores)-min(scores):.2f}")

    with (CSV_DIR / "protocol_fold_spread.csv").open("w", newline="",
                                                     encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fold", "n_test_categories", "s_auroc_mean"])
        w.writeheader()
        for i, s in enumerate(scores):
            w.writerow({"fold": i, "n_test_categories": len(folds["folds"][i]["test"]),
                        "s_auroc_mean": s})
    print("wrote protocol_fold_spread.csv")


if __name__ == "__main__":
    main()
