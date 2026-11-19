#!/usr/bin/env python3
"""Publication figures for the Results section.

Each figure serves one claim of the section. Figures carry no internal title:
the caption is authoritative, as required by the Elsevier CAS layout. All
inference uses category as the sampling unit, consistent with the CSV tables.

Reads the CSV tables produced by build_section5_assets.py and
build_learned_aggregation.py, plus raw predictions for the score-distribution
panel. Writes PDF (vector, for LaTeX) and PNG (for review).
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import stats

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
ASSETS = PAPER / "paper_assets"
CSV_DIR, FIG_DIR = ASSETS / "results", ASSETS / "figures"

DETECTORS = ["VisualAD-A", "WinCLIP", "AnomalyCLIP-VisA", "Cross-view NN"]
COLOR = {"VisualAD-A": "#1b4f72", "VisualAD-Acontinued": "#1b4f72",
         "VisualAD-F": "#c0392b", "WinCLIP": "#e67e22",
         "AnomalyCLIP-VisA": "#27ae60", "Cross-view NN": "#7d3c98"}


# CSV keys stay stable so that the tables remain reproducible; only the label
# shown to the reader changes, to match the function notation of Section 3.
DISPLAY = {
    "VisualAD-A": "VisualAD $f_\\mathrm{base}$",
    "VisualAD-Acontinued": "VisualAD $f_\\mathrm{budget}$",
    "VisualAD-F": "VisualAD $f_\\mathrm{mv}$",
    "WinCLIP": "WinCLIP",
    "AnomalyCLIP-VisA": "AnomalyCLIP-VisA",
    "Cross-view NN": "Cross-view NN",
}

plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": .7, "figure.dpi": 150, "savefig.dpi": 300,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})


def read(name):
    with (CSV_DIR / name).open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def save(name):
    plt.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight")
    plt.close()
    print("wrote", name)


def forest(ax, labels, values, los, his, colors=None, marker="o"):
    """Horizontal effect plot, top row first, with a reference line at zero."""
    y = np.arange(len(labels))[::-1]
    colors = colors or ["#1b4f72"] * len(labels)
    for yi, v, lo, hi, c in zip(y, values, los, his, colors):
        solid = lo > 0 or hi < 0
        ax.plot([lo, hi], [yi, yi], color=c, lw=1.4, solid_capstyle="butt")
        ax.plot([lo, lo, np.nan, hi, hi], [yi - .13, yi + .13, np.nan,
                                           yi - .13, yi + .13], color=c, lw=1.0)
        ax.plot(v, yi, marker, color=c, ms=5,
                markerfacecolor=c if solid else "white", markeredgewidth=1.2)
    ax.axvline(0, color="#555555", lw=.8, zorder=0)
    ax.set_yticks(y, labels)
    ax.set_ylim(-.6, len(labels) - .4)
    ax.grid(axis="x", alpha=.18, lw=.6)


# --------------------------------------------------------------- Figure 5.1
def fig_oracle_headroom(agg):
    """Section 5.1: the value of privileged visibility depends on the detector."""
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.2), sharey=True,
                             gridspec_kw={"wspace": .10})
    for ax, rule, title in zip(axes, ("oracle_mean", "oracle_max"),
                               ("Oracle mean vs. mean", "Oracle max vs. mean")):
        rows = [next(r for r in agg if r["detector"] == d and r["aggregation"] == rule)
                for d in DETECTORS]
        forest(ax, [DISPLAY[d] for d in DETECTORS], [r["delta_vs_mean"] for r in rows],
               [r["ci_low"] for r in rows], [r["ci_high"] for r in rows],
               [COLOR[d] for d in DETECTORS])
        ax.set_xlabel("S-AUROC difference (points)")
        ax.set_title(title, pad=6)
    axes[0].set_xlim(-11, 7)
    save("fig5_1_oracle_headroom")


# --------------------------------------------------------------- Figure 5.2
def fig_aggregation_rules(agg, learned):
    """Sections 5.2 and 5.3: no fixed or learned rule beats the mean."""
    fixed = ["max", "top2", "top3", "median"]
    names = {"max": "Max", "top2": "Top-2", "top3": "Top-3", "median": "Median",
             "logistic_regression": "Logistic", "gated_L_estimator": "Gated-L"}
    fig = plt.figure(figsize=(7.0, 3.9))
    gs = fig.add_gridspec(4, 2, wspace=.52, hspace=.78, width_ratios=[1.25, 1],
                          bottom=.20, top=.94)

    lo_all = min(r["ci_low"] for r in agg
                 if r["aggregation"] in fixed) - 1.5
    left = None
    for i, d in enumerate(DETECTORS):
        ax = fig.add_subplot(gs[i, 0], sharex=left)
        left = left or ax
        rows = [next(x for x in agg if x["detector"] == d and x["aggregation"] == r)
                for r in fixed]
        forest(ax, [names[r] for r in fixed], [r["delta_vs_mean"] for r in rows],
               [r["ci_low"] for r in rows], [r["ci_high"] for r in rows],
               [COLOR[d]] * len(fixed))
        ax.set_title(DISPLAY[d], loc="left", pad=3.5, fontsize=7.5, color=COLOR[d])
        ax.set_xlim(lo_all, 3)
        if i < len(DETECTORS) - 1:
            ax.tick_params(labelbottom=False)
    left.figure.axes[-1].set_xlabel("S-AUROC vs. mean (points)")

    ax = fig.add_subplot(gs[:, 1])
    order = ["VisualAD-A", "VisualAD-Acontinued", "VisualAD-F"]
    short = {"VisualAD-A": "$f_\\mathrm{base}$",
             "VisualAD-Acontinued": "$f_\\mathrm{budget}$",
             "VisualAD-F": "$f_\\mathrm{mv}$"}
    labels, vals, los, his, colors = [], [], [], [], []
    for d in order:
        for m in ("logistic_regression", "gated_L_estimator"):
            r = next(x for x in learned if x["detector"] == d and x["method"] == m)
            labels.append(f"{names[m]}, {short[d]}")
            vals.append(r["delta_vs_mean"]); los.append(r["ci_low"]); his.append(r["ci_high"])
            colors.append(COLOR[d])
    forest(ax, labels, vals, los, his, colors)
    ax.set_title("Learned aggregators, VisualAD family", loc="left", pad=3.5, fontsize=7.5)
    ax.set_xlabel("S-AUROC vs. mean (points)")

    handles = [Line2D([], [], marker="o", color="#555", ls="none", mfc="#555", ms=5),
               Line2D([], [], marker="o", color="#555", ls="none", mfc="white", ms=5)]
    fig.legend(handles, ["95% CI excludes zero", "95% CI includes zero"],
               loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(.5, .01))
    save("fig5_2_aggregation_rules")


# --------------------------------------------------------------- Figure 5.3
def fig_upstream(comparisons, cat):
    """Section 5.4: the gain of F is already present before aggregation."""
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5),
                             gridspec_kw={"wspace": .32, "width_ratios": [1.15, 1]})

    ax = axes[0]
    pairs = [("VisualAD-Acontinued - VisualAD-A",
              "$f_\\mathrm{budget}$ - $f_\\mathrm{base}$"),
             ("VisualAD-F - VisualAD-Acontinued",
              "$f_\\mathrm{mv}$ - $f_\\mathrm{budget}$")]
    labels, vals, los, his, colors = [], [], [], [], []
    for key, tag in pairs:
        for metric, mtag in (("i_auroc", "image"), ("s_auroc_mean", "object")):
            r = next(x for x in comparisons if x["comparison"] == key and x["metric"] == metric)
            labels.append(f"{tag}, {mtag} level")
            vals.append(r["difference"]); los.append(r["ci_low"]); his.append(r["ci_high"])
            colors.append("#7f8c8d" if "budget}$ -" in tag else "#c0392b")
    forest(ax, labels, vals, los, his, colors)
    ax.set_xlabel("AUROC difference (points), 30 paired categories")

    ax = axes[1]
    ac = {r["category"]: r["s_auroc_mean"] for r in cat if r["detector"] == "VisualAD-Acontinued"}
    ff = {r["category"]: r["s_auroc_mean"] for r in cat if r["detector"] == "VisualAD-F"}
    keys = sorted(ac)
    x, y = np.array([ac[k] for k in keys]), np.array([ff[k] for k in keys])
    lim = [min(x.min(), y.min()) - 3, 100.5]
    ax.plot(lim, lim, color="#555555", lw=.8, zorder=0)
    ax.scatter(x, y, s=16, c=np.where(y >= x, "#c0392b", "#7f8c8d"),
               edgecolor="white", linewidth=.5, zorder=3)
    ax.set(xlim=lim, ylim=lim, xlabel="$f_\\mathrm{budget}$ S-AUROC per category",
           ylabel="$f_\\mathrm{mv}$ S-AUROC per category")
    ax.set_aspect("equal")
    ax.text(.04, .87, f"$f_\\mathrm{{mv}}$ higher in {int((y >= x).sum())} of {len(keys)} categories",
            transform=ax.transAxes, fontsize=7, color="#c0392b")
    ax.grid(alpha=.18, lw=.6)
    save("fig5_3_upstream_gain")


# --------------------------------------------------------------- Figure 5.4
def fig_visibility(kprof, kcomp):
    """Section 5.5: the gain of F is not concentrated at low k."""
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8),
                             gridspec_kw={"wspace": .30, "width_ratios": [1.1, 1]})

    ax = axes[0]
    for d in ["VisualAD-Acontinued"] + DETECTORS[1:]:
        rows = sorted((r for r in kprof if r["detector"] == d), key=lambda r: r["k"])
        k = np.array([r["k"] for r in rows]); v = np.array([r["s_auroc_mean"] for r in rows])
        lo = np.array([r["ci_low"] for r in rows]); hi = np.array([r["ci_high"] for r in rows])
        ax.errorbar(k, v, yerr=[v - lo, hi - v], marker="o", ms=4, lw=1.6,
                    capsize=2.5, elinewidth=.8, color=COLOR[d],
                    label=DISPLAY[d])
    ax.set(xlabel="Defect-visible views $k$", ylabel="Macro S-AUROC", xticks=range(1, 6))
    ax.set_ylim(top=ax.get_ylim()[1] + .17 * (ax.get_ylim()[1] - ax.get_ylim()[0]))
    ax.legend(frameon=False, loc="upper left", handlelength=1.4, ncol=2,
              columnspacing=1.0, labelspacing=.25, borderaxespad=.15)
    ax.grid(axis="y", alpha=.18, lw=.6)

    ax = axes[1]
    rows = sorted(kcomp, key=lambda r: r["k"])
    k = np.array([r["k"] for r in rows]); v = np.array([r["difference"] for r in rows])
    lo = np.array([r["ci_low"] for r in rows]); hi = np.array([r["ci_high"] for r in rows])
    ax.axhline(0, color="#555555", lw=.8, zorder=0)
    for ki, vi, li, hi_ in zip(k, v, lo, hi):
        solid = li > 0 or hi_ < 0
        ax.plot([ki, ki], [li, hi_], color="#c0392b", lw=1.4)
        ax.plot(ki, vi, "o", color="#c0392b", ms=5,
                markerfacecolor="#c0392b" if solid else "white", markeredgewidth=1.2)
    span = hi.max() - lo.min()
    ax.set_ylim(lo.min() - .08 * span, hi.max() + .26 * span)
    top = ax.get_ylim()[1]
    for r, h in zip(rows, hi):
        ax.text(r["k"], top - .04 * span, f"n={int(r['n_categories'])}",
                ha="center", va="top", fontsize=6.3, color="#666666")
    ax.set(xlabel="Defect-visible views $k$",
           ylabel="$f_\\mathrm{mv}$ - $f_\\mathrm{budget}$ (S-AUROC points)", xticks=range(1, 6))
    ax.set_xlim(.55, 5.45)
    ax.grid(axis="y", alpha=.18, lw=.6)
    save("fig5_4_visibility")


# --------------------------------------------------------------- Figure 5.5
def fig_signal(signal):
    """Section 5.6: F widens the class separation faster than the noise."""
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5),
                             gridspec_kw={"wspace": .34, "width_ratios": [1.2, 1]})

    # Panel a: object scores standardized inside each category, pooled.
    ax = axes[0]
    NAME = {"A_continued": r"$f_\mathrm{budget}$", "F": r"$f_\mathrm{mv}$"}
    for det, ls in (("A_continued", "--"), ("F", "-")):
        normal, anomaly = [], []
        for f in range(5):
            z = np.load(EXP / f"runs/fold_{f:02d}/seed_00/{det}/eval/predictions_fold{f}.npz",
                        allow_pickle=True)
            s = z["view_scores"].mean(1)
            y, cats = z["object_label"].astype(int), z["category"]
            for c in sorted(set(cats.tolist())):
                m = cats == c
                ref = s[m & (y == 0)]
                zz = (s[m] - ref.mean()) / ref.std(ddof=1)
                normal.append(zz[y[m] == 0]); anomaly.append(zz[y[m] == 1])
        grid = np.linspace(-4, 12, 400)
        for vals, color, tag in ((np.concatenate(normal), "#2c3e50", "normal"),
                                 (np.concatenate(anomaly), "#c0392b", "anomalous")):
            ax.plot(grid, stats.gaussian_kde(vals)(grid), ls, color=color, lw=1.3,
                    label=f"{tag}, {NAME[det]}")
    ax.set(xlabel="Object score, standardized by the normal class of its category",
           ylabel="Density", xlim=(-4, 12))
    ax.legend(frameon=False, ncol=1, handlelength=1.6, loc="upper right",
              labelspacing=.25, borderaxespad=.2)
    ax.grid(alpha=.18, lw=.6)

    # Panel b: paired per-category change from the equal-budget control.
    ax = axes[1]
    metrics = [("normal_std", "Normal spread"), ("anomaly_normal_gap", "Anomaly-normal gap"),
               ("d_prime", "$d'$")]
    labels, vals, los, his = [], [], [], []
    for key, tag in metrics:
        base = {r["category"]: r[key] for r in signal if r["detector"] == "VisualAD-Acontinued"}
        new = {r["category"]: r[key] for r in signal if r["detector"] == "VisualAD-F"}
        rel = np.array([100 * (new[c] - base[c]) / base[c] for c in sorted(base)])
        se = stats.sem(rel)
        lo, hi = stats.t.interval(0.95, len(rel) - 1, loc=rel.mean(), scale=se)
        labels.append(tag); vals.append(rel.mean()); los.append(lo); his.append(hi)
    forest(ax, labels, vals, los, his, ["#c0392b"] * 3)
    ax.set_xlabel("$f_\\mathrm{mv}$ vs. $f_\\mathrm{budget}$, relative change (%)")
    save("fig5_5_signal")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    agg = read("aggregation_summary.csv")
    learned = read("learned_aggregation_summary.csv")
    cat = read("category_metrics.csv")
    fig_oracle_headroom(agg)
    fig_aggregation_rules(agg, learned)
    fig_upstream(read("visualad_paired_comparisons.csv"), cat)
    fig_visibility(read("k_profile.csv"), read("visualad_k_comparison.csv"))
    fig_signal(read("signal_statistics_by_category.csv"))


if __name__ == "__main__":
    main()
