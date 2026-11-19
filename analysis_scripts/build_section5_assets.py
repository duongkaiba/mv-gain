#!/usr/bin/env python3
"""Build paper-ready CSV tables and figures for the Vietnamese Results section.

All metrics are recomputed from raw prediction NPZ files. Statistical inference
uses category as the sampling unit. The script never modifies raw predictions.
"""
from __future__ import annotations

import csv
import glob
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
OUT = PAPER / "paper_assets"
CSV_DIR = OUT / "results"
FIG_DIR = OUT / "figures"

DETECTORS = {
    "VisualAD-A": str(EXP / "runs/fold_*/seed_00/A/eval/predictions_fold*.npz"),
    "VisualAD-Acontinued": str(EXP / "runs/fold_*/seed_00/A_continued/eval/predictions_fold*.npz"),
    "VisualAD-F": str(EXP / "runs/fold_*/seed_00/F/eval/predictions_fold*.npz"),
    "WinCLIP": str(EXP / "baselines/winclip/fold_*/seed_00/WinCLIP/eval/predictions_fold*.npz"),
    "Cross-view NN": str(EXP / "baselines/crossview_nn/fold_*/seed_00/CrossViewNN/eval/predictions_fold*.npz"),
    "AnomalyCLIP-VisA": str(EXP / "baselines/anomalyclip_visa/fold_*/seed_00/AnomalyCLIP/eval/predictions_fold*_shard*of2.npz"),
}
RULES = ("mean", "max", "top2", "top3", "median", "oracle_mean", "oracle_max")


def auroc(scores, labels):
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    if labels.sum() == 0 or (labels == 0).sum() == 0:
        return np.nan
    return float(stats.rankdata(scores)[labels == 1].sum() - labels.sum() *
                 (labels.sum() + 1) / 2) / float(labels.sum() * (labels == 0).sum())


def aggregate(scores, valid, rule):
    out = []
    for s, v in zip(scores, valid):
        x = np.asarray(s)[np.asarray(v, dtype=bool)]
        if rule == "mean": out.append(x.mean())
        elif rule == "max": out.append(x.max())
        elif rule == "median": out.append(np.median(x))
        elif rule.startswith("top"):
            n = int(rule[3:])
            out.append(np.sort(x)[::-1][:n].mean())
        else: raise ValueError(rule)
    return np.asarray(out)


def oracle(scores, valid, image_labels, object_labels, use_max=False):
    out = []
    for s, v, il, y in zip(scores, valid, image_labels, object_labels):
        v = np.asarray(v, dtype=bool)
        selected = (np.asarray(il, dtype=bool) & v) if y else v
        x = np.asarray(s)[selected]
        out.append(x.max() if use_max else x.mean())
    return np.asarray(out)


def ci_t(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan, np.nan
    se = stats.sem(x)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=se)
    p = stats.ttest_1samp(x, 0).pvalue
    return lo, hi, p


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def load_detector(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(pattern)
    keys = ["category", "object_label", "k", "valid", "image_labels", "view_scores"]
    chunks = [np.load(p, allow_pickle=True) for p in files]
    data = {k: np.concatenate([z[k] for z in chunks]) for k in keys}
    return files, data


def category_rows(detector, data):
    rows = []
    cats = data["category"]
    for category in sorted(set(cats.tolist())):
        q = cats == category
        y = data["object_label"][q].astype(int)
        s, v = data["view_scores"][q], data["valid"][q].astype(bool)
        il = data["image_labels"][q].astype(bool)
        values = {r: (oracle(s, v, il, y, r == "oracle_max") if r.startswith("oracle")
                      else aggregate(s, v, r)) for r in RULES}
        image_y, image_s = il[v].astype(int), s[v]
        row = {"detector": detector, "category": category,
               "n_objects": int(q.sum()), "i_auroc": 100 * auroc(image_s, image_y)}
        row.update({f"s_auroc_{r}": 100 * auroc(values[r], y) for r in RULES})
        rows.append(row)
    return rows


def k_rows(detector, data):
    rows = []
    cats = data["category"]
    for k in range(1, 6):
        vals = []
        for category in sorted(set(cats.tolist())):
            base = cats == category
            keep = base & ((data["object_label"] == 0) |
                           ((data["object_label"] == 1) & (data["k"] == k)))
            y = ((data["object_label"][keep] == 1) & (data["k"][keep] == k)).astype(int)
            # A category contributes whenever AUROC is defined. MIN_STRATUM in
            # the locked evaluator applies to the complete fold stratum, not
            # separately to each category after folds are concatenated.
            if y.sum() == 0 or (y == 0).sum() == 0:
                continue
            score = aggregate(data["view_scores"][keep], data["valid"][keep], "mean")
            vals.append(100 * auroc(score, y))
        lo, hi, _ = ci_t(vals)
        rows.append({"detector": detector, "k": k, "n_categories": len(vals),
                     "s_auroc_mean": np.mean(vals), "ci_low": lo, "ci_high": hi})
    return rows


def signal_rows(detector, data):
    rows = []
    cats = data["category"]
    score = aggregate(data["view_scores"], data["valid"], "mean")
    for category in sorted(set(cats.tolist())):
        q = cats == category
        normal = score[q & (data["object_label"] == 0)]
        anomaly = score[q & (data["object_label"] == 1)]
        gap = anomaly.mean() - normal.mean()
        pooled = math.sqrt(0.5 * (normal.var(ddof=1) + anomaly.var(ddof=1)))
        rows.append({"detector": detector, "category": category,
                     "normal_std": normal.std(ddof=1), "anomaly_normal_gap": gap,
                     "d_prime": gap / pooled})
    return rows


def main():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    provenance, cat_all, k_all, sig_all = [], [], [], []
    loaded = {}
    for detector, pattern in DETECTORS.items():
        files, data = load_detector(pattern)
        loaded[detector] = data
        for p in files:
            provenance.append({"detector": detector, "role": "raw_predictions",
                               "path": str(Path(p).relative_to(ROOT))})
        cat_all += category_rows(detector, data)
        k_all += k_rows(detector, data)
        if detector in ("VisualAD-A", "VisualAD-Acontinued", "VisualAD-F"):
            sig_all += signal_rows(detector, data)

    write_csv(CSV_DIR / "data_provenance.csv", provenance, ["detector", "role", "path"])
    cat_fields = ["detector", "category", "n_objects", "i_auroc"] + [f"s_auroc_{r}" for r in RULES]
    write_csv(CSV_DIR / "category_metrics.csv", cat_all, cat_fields)
    write_csv(CSV_DIR / "k_profile.csv", k_all,
              ["detector", "k", "n_categories", "s_auroc_mean", "ci_low", "ci_high"])
    write_csv(CSV_DIR / "signal_statistics_by_category.csv", sig_all,
              ["detector", "category", "normal_std", "anomaly_normal_gap", "d_prime"])

    # Aggregation summaries and paired inference relative to mean.
    summaries = []
    for detector in DETECTORS:
        rows = [r for r in cat_all if r["detector"] == detector]
        mean = np.array([r["s_auroc_mean"] for r in rows])
        for rule in RULES:
            vals = np.array([r[f"s_auroc_{rule}"] for r in rows])
            diff = vals - mean
            lo, hi, p = (0.0, 0.0, 1.0) if rule == "mean" else ci_t(diff)
            summaries.append({"detector": detector, "aggregation": rule,
                              "n_categories": len(vals), "s_auroc": vals.mean(),
                              "delta_vs_mean": diff.mean(), "ci_low": lo,
                              "ci_high": hi, "p_vs_mean": p})
    write_csv(CSV_DIR / "aggregation_summary.csv", summaries,
              ["detector", "aggregation", "n_categories", "s_auroc",
               "delta_vs_mean", "ci_low", "ci_high", "p_vs_mean"])

    # VisualAD upstream operating points and paired differences.
    ops = []
    for detector in ("VisualAD-A", "VisualAD-Acontinued", "VisualAD-F"):
        rows = [r for r in cat_all if r["detector"] == detector]
        ops.append({"detector": detector, "n_categories": len(rows),
                    "i_auroc": np.mean([r["i_auroc"] for r in rows]),
                    "s_auroc_mean": np.mean([r["s_auroc_mean"] for r in rows])})
    write_csv(CSV_DIR / "visualad_operating_points.csv", ops,
              ["detector", "n_categories", "i_auroc", "s_auroc_mean"])

    comparisons = []
    by_det = {d: {r["category"]: r for r in cat_all if r["detector"] == d}
              for d in ("VisualAD-A", "VisualAD-Acontinued", "VisualAD-F")}
    for left, right in (("VisualAD-A", "VisualAD-Acontinued"),
                        ("VisualAD-Acontinued", "VisualAD-F")):
        for metric in ("i_auroc", "s_auroc_mean"):
            cats = sorted(set(by_det[left]) & set(by_det[right]))
            diff = np.array([by_det[right][c][metric] - by_det[left][c][metric] for c in cats])
            lo, hi, p = ci_t(diff)
            comparisons.append({"comparison": f"{right} - {left}", "metric": metric,
                                "n_categories": len(cats), "difference": diff.mean(),
                                "ci_low": lo, "ci_high": hi, "p_value": p})
    write_csv(CSV_DIR / "visualad_paired_comparisons.csv", comparisons,
              ["comparison", "metric", "n_categories", "difference",
               "ci_low", "ci_high", "p_value"])

    # F vs equal-budget control within each k stratum.
    f_by = {(r["detector"], r["k"]): r for r in k_all}
    k_compare = []
    ac, ff = loaded["VisualAD-Acontinued"], loaded["VisualAD-F"]
    for k in range(1, 6):
        per_cat = []
        cats = sorted(set(ac["category"].tolist()))
        for c in cats:
            vals = []
            for data in (ac, ff):
                base = data["category"] == c
                keep = base & ((data["object_label"] == 0) |
                               ((data["object_label"] == 1) & (data["k"] == k)))
                y = ((data["object_label"][keep] == 1) & (data["k"][keep] == k)).astype(int)
                if y.sum() == 0 or (y == 0).sum() == 0: break
                vals.append(100 * auroc(aggregate(data["view_scores"][keep], data["valid"][keep], "mean"), y))
            if len(vals) == 2: per_cat.append(vals[1] - vals[0])
        lo, hi, p = ci_t(per_cat)
        k_compare.append({"k": k, "n_categories": len(per_cat),
                          "Acontinued": f_by[("VisualAD-Acontinued", k)]["s_auroc_mean"],
                          "F": f_by[("VisualAD-F", k)]["s_auroc_mean"],
                          "difference": np.mean(per_cat), "ci_low": lo,
                          "ci_high": hi, "p_value": p})
    write_csv(CSV_DIR / "visualad_k_comparison.csv", k_compare,
              ["k", "n_categories", "Acontinued", "F", "difference",
               "ci_low", "ci_high", "p_value"])

    # Learned aggregators are recomputed by build_learned_aggregation.py, which
    # owns learned_aggregation_summary.csv and its category-level companion.
    # That script is run separately because it fits torch models.

    make_figures(summaries, k_all, comparisons, sig_all)


def savefig(name):
    plt.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.savefig(FIG_DIR / f"{name}.png", dpi=240, bbox_inches="tight")
    plt.close()


def make_figures(summaries, k_rows_all, comparisons, signal):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 140})
    dets = ["VisualAD-A", "WinCLIP", "AnomalyCLIP-VisA", "Cross-view NN"]
    rules = ["max", "top2", "top3", "median", "oracle_mean", "oracle_max"]
    mat = np.array([[next(r["delta_vs_mean"] for r in summaries
                          if r["detector"] == d and r["aggregation"] == a)
                     for a in rules] for d in dets])
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    lim = max(abs(mat.min()), abs(mat.max()))
    im = ax.imshow(mat, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat[i,j]:+.1f}", ha="center", va="center",
                    color="white" if abs(mat[i,j]) > .55 * lim else "black", fontsize=8)
    ax.set_xticks(range(len(rules)), ["Max", "Top-2", "Top-3", "Median", "Oracle mean", "Oracle max"])
    ax.set_yticks(range(len(dets)), dets)
    ax.set_title("S-AUROC difference relative to mean aggregation")
    fig.colorbar(im, ax=ax, label="Delta AUROC", fraction=.025, pad=.02)
    savefig("fig5_aggregation_heatmap")

    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    colors = {"VisualAD-Acontinued": "#1f77b4", "WinCLIP": "#ff7f0e",
              "AnomalyCLIP-VisA": "#2ca02c", "Cross-view NN": "#9467bd"}
    for d in colors:
        rows = sorted((r for r in k_rows_all if r["detector"] == d), key=lambda x: x["k"])
        x = np.array([r["k"] for r in rows]); y = np.array([r["s_auroc_mean"] for r in rows])
        lo = np.array([r["ci_low"] for r in rows]); hi = np.array([r["ci_high"] for r in rows])
        ax.plot(x, y, marker="o", lw=1.8, label=d, color=colors[d])
        ax.fill_between(x, lo, hi, alpha=.10, color=colors[d])
    ax.set(xlabel="Number of defect-visible views (k)", ylabel="Macro S-AUROC", xticks=range(1,6))
    ax.legend(frameon=False, ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=.2)
    savefig("fig5_k_profiles")

    fig, ax = plt.subplots(figsize=(5.7, 2.8))
    rows = [r for r in comparisons if r["comparison"] == "VisualAD-F - VisualAD-Acontinued"]
    labels = ["Image level", "Object level"]
    y = np.arange(2)
    vals = np.array([next(r["difference"] for r in rows if r["metric"] == m)
                     for m in ("i_auroc", "s_auroc_mean")])
    los = np.array([next(r["ci_low"] for r in rows if r["metric"] == m)
                    for m in ("i_auroc", "s_auroc_mean")])
    his = np.array([next(r["ci_high"] for r in rows if r["metric"] == m)
                    for m in ("i_auroc", "s_auroc_mean")])
    ax.errorbar(vals, y, xerr=[vals-los, his-vals], fmt="o", color="#1f4e79", capsize=3)
    ax.axvline(0, color="black", lw=.8)
    ax.set(yticks=y, yticklabels=labels, xlabel="F - equal-budget control (AUROC points)")
    ax.grid(axis="x", alpha=.2)
    savefig("fig5_upstream_gain")

    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    dets = ["VisualAD-A", "VisualAD-Acontinued", "VisualAD-F"]
    metrics = [("normal_std", "Normal spread"), ("anomaly_normal_gap", "Anomaly-normal gap"),
               ("d_prime", "d-prime")]
    x = np.arange(3); width = .23
    for i, d in enumerate(dets):
        rows = [r for r in signal if r["detector"] == d]
        vals = [np.mean([r[m] for r in rows]) for m, _ in metrics]
        # Normalize within metric to A for a readable common axis.
        bases = [np.mean([r[m] for r in signal if r["detector"] == "VisualAD-A"]) for m, _ in metrics]
        ax.bar(x + (i-1)*width, np.array(vals)/np.array(bases), width, label=d)
    ax.set_xticks(x, [lab for _, lab in metrics])
    ax.set_ylabel("Relative to VisualAD-A")
    ax.axhline(1, color="black", lw=.7)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=.2)
    savefig("fig5_signal_characterization")


if __name__ == "__main__":
    main()
