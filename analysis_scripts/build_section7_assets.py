#!/usr/bin/env python3
"""Synthesis table and figure for the Discussion.

The Discussion makes one claim that no single earlier section can make on its
own: across detector families and across datasets, the more work mean
aggregation already performs, the less headroom a better aggregator can reach.
This script assembles that comparison from the tables built for Sections 5
and 6, and draws the conceptual figure that accompanies it.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_section5_figures import CSV_DIR, FIG_DIR, read, save  # noqa: E402

LABEL = {"VisualAD-A": "VisualAD $f_\\mathrm{base}$",
         "VisualAD-Acontinued": "VisualAD $f_\\mathrm{budget}$",
         "VisualAD-F": "VisualAD $f_\\mathrm{mv}$", "WinCLIP": "WinCLIP",
         "AnomalyCLIP-VisA": "AnomalyCLIP", "Cross-view NN": "Cross-view NN"}


def ci_t(x):
    x = np.asarray(x, float)
    se = stats.sem(x)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=se)
    return float(x.mean()), float(lo), float(hi)


def collect():
    """One row per operating point: how much aggregation adds, and what is left."""
    cat, agg = read("category_metrics.csv"), read("aggregation_summary.csv")
    vcat, vagg = read("variety_category_metrics.csv"), read("variety_aggregation_summary.csv")
    rows = []

    for det in LABEL:
        rs = [r for r in cat if r["detector"] == det]
        lift = np.array([r["s_auroc_mean"] - r["i_auroc"] for r in rs])
        m, lo, hi = ci_t(lift)
        head = next(r for r in agg if r["detector"] == det and r["aggregation"] == "oracle_mean")
        rows.append({"operating_point": det, "dataset": "Real-IAD",
                     "n_categories": len(rs),
                     "i_auroc": float(np.mean([r["i_auroc"] for r in rs])),
                     "s_auroc": float(np.mean([r["s_auroc_mean"] for r in rs])),
                     "aggregation_lift": m, "lift_ci_low": lo, "lift_ci_high": hi,
                     "oracle_headroom": head["delta_vs_mean"],
                     "headroom_ci_low": head["ci_low"], "headroom_ci_high": head["ci_high"]})

    for det in ("VisualAD-Acontinued", "VisualAD-F"):
        per = {}
        for r in vcat:
            if r["detector"] == det:
                per.setdefault(r["category"], []).append(r)
        i = np.array([np.mean([x["i_auroc"] for x in v]) for v in per.values()])
        s = np.array([np.mean([x["s_auroc_mean"] for x in v]) for v in per.values()])
        m, lo, hi = ci_t(s - i)
        head = next(r for r in vagg if r["detector"] == det and r["aggregation"] == "oracle_mean")
        rows.append({"operating_point": det, "dataset": "Variety", "n_categories": len(per),
                     "i_auroc": float(i.mean()), "s_auroc": float(s.mean()),
                     "aggregation_lift": m, "lift_ci_low": lo, "lift_ci_high": hi,
                     "oracle_headroom": head["delta_vs_mean"],
                     "headroom_ci_low": head["ci_low"], "headroom_ci_high": head["ci_high"]})
    return rows


def schematic(ax):
    """Where multi-view information exists, and where it stops existing."""
    ax.set(xlim=(0, 10.2), ylim=(0.4, 5.35)); ax.axis("off")

    def box(x, y, w, h, text, fc, fs=6.8):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04",
                                    fc=fc, ec="#707070", lw=.7))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

    def arrow(x0, x1, y, color="#555555", lw=.9):
        ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                     mutation_scale=9, lw=lw, color=color))

    for j in range(5):
        box(0.15, 3.45 - .62 * j, 1.05, .5, f"view {j+1}", "#e8eef4")
    box(1.75, 1.35, 1.35, 2.4, "upstream\nscoring\n$f$", "#cfe0ee")
    for j in range(5):
        ax.add_patch(plt.Circle((3.85, 3.50 - .60 * j), .155, fc="#f6c6b8",
                                ec="#707070", lw=.7))
    ax.text(3.85, .72, "$s_1 \\ldots s_5$", ha="center", fontsize=7)
    box(4.70, 1.35, 1.30, 2.4, "aggregation\n$g$", "#f2d4c9")
    ax.add_patch(plt.Circle((6.60, 2.55), .24, fc="#c0392b", ec="#707070", lw=.7))
    ax.text(6.60, 2.55, "$S$", ha="center", va="center", fontsize=7.5, color="white")
    ax.text(6.60, 2.16, "object score", ha="center", va="top", fontsize=6.4)

    arrow(1.28, 1.70, 2.55); arrow(3.18, 3.62, 2.55)
    arrow(4.10, 4.65, 2.55); arrow(6.05, 6.31, 2.55)

    # Information available at each stage, drawn to the scale of what survives.
    ax.plot([1.75, 3.10], [4.72, 4.72], lw=5.5, color="#2c6ca0", solid_capstyle="butt")
    ax.text(2.42, 4.88, "visibility, geometry,\ncorrespondence, reliability",
            ha="center", va="bottom", fontsize=6.2, color="#2c6ca0")
    ax.plot([3.72, 3.98], [4.72, 4.72], lw=5.5, color="#c0392b", solid_capstyle="butt")
    ax.text(4.10, 4.88, "five\nnumbers", ha="left", va="bottom",
            fontsize=6.2, color="#c0392b")
    arrow(3.20, 3.66, 4.72, color="#c0392b", lw=1.1)
    ax.text(3.43, 4.52, "information bottleneck", ha="center", va="top",
            fontsize=6.4, color="#c0392b")

    box(7.30, 3.00, 2.85, 1.10,
        "Little left to gain here\nno rule beats the mean;\nVariety oracle headroom $+0.02$", "#eef3f7", 6.3)
    box(7.30, 0.85, 2.85, 1.10,
        "Open observation, Variety:\nimage $+3.57$, object $+0.53$\nno mechanism established", "#fbeee9", 6.3)
    ax.plot([6.02, 7.26], [3.35, 3.55], lw=.7, color="#a0a0a0")
    ax.plot([6.02, 7.26], [1.70, 1.40], lw=.7, color="#a0a0a0")


OFFSET = {("VisualAD-A", "Real-IAD"): (7, 5),
          ("VisualAD-Acontinued", "Real-IAD"): (-8, 9),
          ("VisualAD-F", "Real-IAD"): (-4, -15),
          ("WinCLIP", "Real-IAD"): (8, 2),
          ("AnomalyCLIP-VisA", "Real-IAD"): (7, 6),
          ("Cross-view NN", "Real-IAD"): (-10, 9),
          ("VisualAD-Acontinued", "Variety"): (7, -3),
          ("VisualAD-F", "Variety"): (2, -13)}


def regularity(ax, rows):
    x = np.array([r["aggregation_lift"] for r in rows])
    y = np.array([r["oracle_headroom"] for r in rows])
    r, p = stats.pearsonr(x, y)
    xs = np.linspace(x.min() - .8, x.max() + .8, 10)
    b, a = np.polyfit(x, y, 1)
    ax.plot(xs, a + b * xs, color="#aaaaaa", lw=1.1, zorder=1)
    ax.axhline(0, color="#555555", lw=.8, zorder=0)
    for row in rows:
        variety = row["dataset"] == "Variety"
        col = "#c0392b" if variety else "#1b4f72"
        ax.errorbar(row["aggregation_lift"], row["oracle_headroom"],
                    yerr=[[row["oracle_headroom"] - row["headroom_ci_low"]],
                          [row["headroom_ci_high"] - row["oracle_headroom"]]],
                    fmt="s" if variety else "o", ms=5, capsize=2, elinewidth=.8,
                    color=col, zorder=3)
        tag = LABEL[row["operating_point"]] + (", Variety" if variety else "")
        ax.annotate(tag, (row["aggregation_lift"], row["oracle_headroom"]),
                    textcoords="offset points",
                    xytext=OFFSET[(row["operating_point"], row["dataset"])],
                    fontsize=6.0, color=col)
    ax.text(.03, .07, f"$r$ = {r:+.2f}, $p$ = {p:.3f}, $n$ = {len(rows)} operating points",
            transform=ax.transAxes, fontsize=6.6, color="#444444")
    ax.set(xlabel="Points mean aggregation adds over image level",
           ylabel="Oracle-mean headroom left")
    ax.grid(alpha=.18, lw=.6)
    ax.set_xlim(x.min() - 1.4, x.max() + 2.2)
    ax.set_ylim(y.min() - 5.0, y.max() + 3.4)


def main():
    rows = collect()
    fields = list(rows[0])
    with (CSV_DIR / "discussion_aggregation_role.csv").open("w", newline="",
                                                            encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("wrote discussion_aggregation_role.csv")

    x = np.array([r["aggregation_lift"] for r in rows])
    y = np.array([r["oracle_headroom"] for r in rows])
    r, p = stats.pearsonr(x, y); rs = stats.spearmanr(x, y)
    keep = np.array([r_["operating_point"] != "Cross-view NN" for r_ in rows])
    r2, p2 = stats.pearsonr(x[keep], y[keep]); rs2 = stats.spearmanr(x[keep], y[keep])
    print(f"lift vs headroom  r={r:+.3f} p={p:.4f}  rho={rs.statistic:+.3f} p={rs.pvalue:.4f}  n={len(x)}")
    print(f"  without Cross-view NN  r={r2:+.3f} p={p2:.4f}  rho={rs2.statistic:+.3f} "
          f"p={rs2.pvalue:.4f}  n={keep.sum()}")
    for row in rows:
        print(f"  {LABEL[row['operating_point']]:22s} {row['dataset']:9s} "
              f"lift {row['aggregation_lift']:+6.2f} [{row['lift_ci_low']:+.2f},"
              f"{row['lift_ci_high']:+.2f}]  headroom {row['oracle_headroom']:+6.2f}")

    plt.rcParams.update({"font.size": 8, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 300,
                         "pdf.fonttype": 42})
    fig = plt.figure(figsize=(7.0, 5.4))
    gs = fig.add_gridspec(2, 1, hspace=.12, height_ratios=[1, 1.15])
    schematic(fig.add_subplot(gs[0]))
    regularity(fig.add_subplot(gs[1]), rows)
    save("fig7_1_scalar_bottleneck")


if __name__ == "__main__":
    main()
