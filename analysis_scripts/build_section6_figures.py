#!/usr/bin/env python3
"""Figures for the Generalization section. Reads only the CSV tables."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_section5_figures import CSV_DIR, FIG_DIR, forest, read, save  # noqa: E402


def fig_transfer(sec5, var):
    """What survives the move to a new dataset, at each evaluation level.

    The second panel of the first draft plotted the aggregation lift against
    the part of the upstream gain that did not survive it. Those two axes share
    a term by construction, so the panel has been removed; Section 6.5 reports
    the permutation null instead.
    """
    fig, ax = plt.subplots(figsize=(4.6, 2.4))
    rows = []
    for m, tag in (("i_auroc", "Image level"), ("s_auroc_mean", "Object level")):
        r5 = next(x for x in sec5 if x["comparison"] == "VisualAD-F - VisualAD-Acontinued"
                  and x["metric"] == m)
        r6 = next(x for x in var if x["subset"] == "all_160" and x["metric"] == m)
        rows.append((f"{tag}, Real-IAD", r5["difference"], r5["ci_low"], r5["ci_high"], "#1b4f72"))
        rows.append((f"{tag}, Variety", r6["difference"], r6["ci_low"], r6["ci_high"], "#c0392b"))
    forest(ax, [r[0] for r in rows], [r[1] for r in rows],
           [r[2] for r in rows], [r[3] for r in rows], [r[4] for r in rows])
    ax.axhline(1.5, color="#cccccc", lw=.6)
    ax.set_xlabel("$f_\\mathrm{mv}$ - $f_\\mathrm{budget}$ (AUROC points)")
    save("fig6_1_transfer")


def fig_aggregation(sec5_agg, var_agg):
    """The aggregation conclusion on 160 unseen categories."""
    rules = ["max", "top2", "top3", "median", "oracle_mean"]
    names = {"max": "Max", "top2": "Top-2", "top3": "Top-3", "median": "Median",
             "oracle_mean": "Oracle mean"}
    fig, ax = plt.subplots(figsize=(4.6, 2.5))
    labels, vals, los, his, colors = [], [], [], [], []
    for rule in rules:
        for src, tag, col in ((sec5_agg, "Real-IAD", "#1b4f72"),
                              (var_agg, "Variety", "#c0392b")):
            r = next(x for x in src if x["detector"] == "VisualAD-Acontinued"
                     and x["aggregation"] == rule)
            labels.append(f"{names[rule]}, {tag}")
            vals.append(r["delta_vs_mean"]); los.append(r["ci_low"]); his.append(r["ci_high"])
            colors.append(col)
    forest(ax, labels, vals, los, his, colors)
    for i in range(1, len(rules)):
        ax.axhline(len(labels) - 2 * i - .5, color="#e0e0e0", lw=.6)
    ax.set_xlabel("S-AUROC vs. mean (points)")
    handles = [Line2D([], [], marker="o", color="#555", ls="none", mfc="#555", ms=5),
               Line2D([], [], marker="o", color="#555", ls="none", mfc="white", ms=5)]
    fig.legend(handles, ["95% CI excludes zero", "95% CI includes zero"],
               loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(.5, -.16))
    save("fig6_2_aggregation_transfer")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_transfer(read("visualad_paired_comparisons.csv"), read("variety_summary.csv"))
    fig_aggregation(read("aggregation_summary.csv"), read("variety_aggregation_summary.csv"))


if __name__ == "__main__":
    main()
