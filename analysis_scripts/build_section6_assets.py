#!/usr/bin/env python3
"""Build the cross-dataset tables of the Generalization section.

Every VisualAD fold produces one model; each model is evaluated on the same
16,000 Real-IAD Variety objects, so the 160 target categories are scored five
times by five independent source splits. The primary comparison averages the
five folds inside each category and then pairs across categories, which keeps
category as the sampling unit used throughout the paper. Per-fold differences
are reported separately so that no conclusion rests on one split.

All metrics are recomputed from raw prediction NPZ files.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"

VARIANTS = {"VisualAD-Acontinued": "A_continued", "VisualAD-F": "F"}
RULES = ("mean", "max", "top2", "top3", "median", "oracle_mean", "oracle_max")


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def aggregate(scores, valid, rule):
    out = []
    for s, v in zip(scores, valid):
        x = np.asarray(s)[np.asarray(v, bool)]
        if rule == "mean": out.append(x.mean())
        elif rule == "max": out.append(x.max())
        elif rule == "median": out.append(np.median(x))
        else: out.append(np.sort(x)[::-1][:int(rule[3:])].mean())
    return np.asarray(out)


def oracle(scores, valid, image_labels, object_labels, use_max):
    out = []
    for s, v, il, y in zip(scores, valid, image_labels, object_labels):
        v = np.asarray(v, bool)
        sel = (np.asarray(il, bool) & v) if y else v
        x = np.asarray(s)[sel]
        out.append(x.max() if use_max else x.mean())
    return np.asarray(out)


def ci_t(values):
    x = np.asarray(values, float); x = x[np.isfinite(x)]
    se = stats.sem(x)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=se)
    return float(x.mean()), float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue)


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("wrote", path.name)


def load(variant, fold):
    p = EXP / f"runs/fold_{fold:02d}/seed_00/{variant}/eval/predictions_variety.npz"
    z = np.load(p, allow_pickle=True)
    if not z["valid"].astype(bool).all():
        raise SystemExit(f"{p}: unexpected invalid views")
    return z, str(p.relative_to(ROOT))


def main():
    overlap = json.loads((EXP / "protocol/category_overlap.json").read_text())
    eligible = set(overlap["eligible_target_categories"])

    rows, provenance = [], []
    for name, variant in VARIANTS.items():
        for fold in range(5):
            z, rel = load(variant, fold)
            provenance.append({"detector": name, "fold": fold, "path": rel})
            cats, y = z["category"], z["object_label"].astype(int)
            s, v = z["view_scores"], z["valid"].astype(bool)
            il = z["image_labels"].astype(bool)
            for c in sorted(set(cats.tolist())):
                q = cats == c
                vals = {r: (oracle(s[q], v[q], il[q], y[q], r == "oracle_max")
                            if r.startswith("oracle") else aggregate(s[q], v[q], r))
                        for r in RULES}
                row = {"detector": name, "fold": fold, "category": c,
                       "eligible": int(c in eligible), "n_objects": int(q.sum()),
                       "i_auroc": auroc(s[q][v[q]], il[q][v[q]].astype(int))}
                row.update({f"s_auroc_{r}": auroc(vals[r], y[q]) for r in RULES})
                rows.append(row)

    fields = ["detector", "fold", "category", "eligible", "n_objects", "i_auroc"] + \
             [f"s_auroc_{r}" for r in RULES]
    write_csv(CSV_DIR / "variety_category_metrics.csv", rows, fields)
    write_csv(CSV_DIR / "variety_provenance.csv", provenance, ["detector", "fold", "path"])

    # ---- primary comparison: average folds inside a category, then pair -----
    def per_cat(det, metric):
        out = {}
        for r in rows:
            if r["detector"] == det:
                out.setdefault(r["category"], []).append(r[metric])
        return {c: float(np.mean(v)) for c, v in out.items()}

    summary = []
    for subset, keep in (("all_160", lambda c: True),
                         ("eligible_141", lambda c: c in eligible)):
        for metric in ("i_auroc", "s_auroc_mean"):
            ac, ff = per_cat("VisualAD-Acontinued", metric), per_cat("VisualAD-F", metric)
            cs = [c for c in sorted(ac) if keep(c)]
            d = np.array([ff[c] - ac[c] for c in cs])
            m, lo, hi, p = ci_t(d)
            summary.append({"subset": subset, "metric": metric, "n_categories": len(cs),
                            "Acontinued": float(np.mean([ac[c] for c in cs])),
                            "F": float(np.mean([ff[c] for c in cs])),
                            "difference": m, "ci_low": lo, "ci_high": hi, "p_value": p,
                            "n_categories_F_higher": int((d > 0).sum())})
    write_csv(CSV_DIR / "variety_summary.csv", summary,
              ["subset", "metric", "n_categories", "Acontinued", "F", "difference",
               "ci_low", "ci_high", "p_value", "n_categories_F_higher"])

    # ---- per fold, so no conclusion depends on one source split -------------
    per_fold = []
    for fold in range(5):
        for metric in ("i_auroc", "s_auroc_mean"):
            ac = {r["category"]: r[metric] for r in rows
                  if r["detector"] == "VisualAD-Acontinued" and r["fold"] == fold}
            ff = {r["category"]: r[metric] for r in rows
                  if r["detector"] == "VisualAD-F" and r["fold"] == fold}
            cs = sorted(ac)
            d = np.array([ff[c] - ac[c] for c in cs])
            m, lo, hi, p = ci_t(d)
            per_fold.append({"fold": fold, "metric": metric, "n_categories": len(cs),
                             "Acontinued": float(np.mean([ac[c] for c in cs])),
                             "F": float(np.mean([ff[c] for c in cs])),
                             "difference": m, "ci_low": lo, "ci_high": hi, "p_value": p})
    write_csv(CSV_DIR / "variety_per_fold.csv", per_fold,
              ["fold", "metric", "n_categories", "Acontinued", "F", "difference",
               "ci_low", "ci_high", "p_value"])

    # ---- aggregation rules on Variety, to test the Section 5 conclusion -----
    agg = []
    for det in VARIANTS:
        base = per_cat(det, "s_auroc_mean")
        for rule in RULES:
            vals = per_cat(det, f"s_auroc_{rule}")
            cs = sorted(base)
            d = np.array([vals[c] - base[c] for c in cs])
            if rule == "mean":
                m, lo, hi, p = 0.0, 0.0, 0.0, 1.0
            else:
                m, lo, hi, p = ci_t(d)
            agg.append({"detector": det, "aggregation": rule, "n_categories": len(cs),
                        "s_auroc": float(np.mean([vals[c] for c in cs])),
                        "delta_vs_mean": m, "ci_low": lo, "ci_high": hi, "p_vs_mean": p})
    write_csv(CSV_DIR / "variety_aggregation_summary.csv", agg,
              ["detector", "aggregation", "n_categories", "s_auroc", "delta_vs_mean",
               "ci_low", "ci_high", "p_vs_mean"])

    # ---- defect visibility mix, and what it predicts ------------------------
    z, _ = load("F", 0)
    k_anom = z["k"][z["object_label"].astype(int) == 1]
    var_mix = np.array([(k_anom == k).sum() for k in range(1, 6)], float)
    var_mix /= var_mix.sum()

    audit = json.loads((EXP / "protocol/data_audit_realiad.json").read_text())
    hist = {str(k): 0 for k in range(1, 6)}
    for c in audit["per_category"].values():
        for k, n in c["k_hist"].items():
            hist[k] += n
    src_mix = np.array([hist[str(k)] for k in range(1, 6)], float)
    src_mix /= src_mix.sum()

    with (CSV_DIR / "visualad_k_comparison.csv").open(encoding="utf-8") as fh:
        kd = {int(r["k"]): float(r["difference"]) for r in csv.DictReader(fh)}
    delta = np.array([kd[k] for k in range(1, 6)])

    mix = [{"k": k, "realiad_share": src_mix[k - 1], "variety_share": var_mix[k - 1],
            "realiad_delta_F_minus_Acont": delta[k - 1]} for k in range(1, 6)]
    write_csv(CSV_DIR / "variety_k_mix.csv", mix,
              ["k", "realiad_share", "variety_share", "realiad_delta_F_minus_Acont"])

    # ---- where the upstream gain is absorbed -------------------------------
    # For each category: how many points mean aggregation adds on top of the
    # image-level score (lift), and how many points of the upstream improvement
    # fail to survive that step (loss). A positive association between the two
    # is threshold-free evidence that the aggregation step absorbs the gain.
    ai, fi = per_cat("VisualAD-Acontinued", "i_auroc"), per_cat("VisualAD-F", "i_auroc")
    ac, ff = per_cat("VisualAD-Acontinued", "s_auroc_mean"), per_cat("VisualAD-F", "s_auroc_mean")
    cs = sorted(ac)
    conv = [{"category": c, "eligible": int(c in eligible),
             "baseline_s_auroc": ac[c], "available_room": 100 - ac[c],
             "image_delta": fi[c] - ai[c], "object_delta": ff[c] - ac[c],
             "aggregation_lift": ac[c] - ai[c],
             "delta_absorbed": (fi[c] - ai[c]) - (ff[c] - ac[c])} for c in cs]
    write_csv(CSV_DIR / "variety_conversion.csv", conv,
              ["category", "eligible", "baseline_s_auroc", "available_room",
               "image_delta", "object_delta", "aggregation_lift", "delta_absorbed"])

    lift = np.array([r["aggregation_lift"] for r in conv])
    absorbed = np.array([r["delta_absorbed"] for r in conv])
    base = np.array([r["baseline_s_auroc"] for r in conv])
    od = np.array([r["object_delta"] for r in conv])
    print(f"\ncorr(aggregation lift, delta absorbed) r={np.corrcoef(lift, absorbed)[0,1]:+.3f} "
          f"p={stats.pearsonr(lift, absorbed)[1]:.2e}")
    print(f"corr(baseline, object delta) r={np.corrcoef(base, od)[0,1]:+.3f}")

    # ---- post-hoc saturation sweep, reported over every threshold ----------
    sweep = []
    for t in (80, 85, 88, 90, 92, 95):
        m = base < t
        if m.sum() < 3:
            continue
        mm, lo, hi, p = ci_t(od[m])
        sweep.append({"threshold": t, "n_categories": int(m.sum()),
                      "mean_baseline": float(base[m].mean()), "difference": mm,
                      "ci_low": lo, "ci_high": hi, "p_value": p})
    m = base >= 95
    mm, lo, hi, p = ci_t(od[m])
    sweep.append({"threshold": -95, "n_categories": int(m.sum()),
                  "mean_baseline": float(base[m].mean()), "difference": mm,
                  "ci_low": lo, "ci_high": hi, "p_value": p})
    write_csv(CSV_DIR / "variety_saturation_sweep.csv", sweep,
              ["threshold", "n_categories", "mean_baseline", "difference",
               "ci_low", "ci_high", "p_value"])
    for r in sweep:
        tag = f"baseline < {r['threshold']}" if r["threshold"] > 0 else "baseline >= 95"
        print(f"  {tag:18s} n={r['n_categories']:3d} mean base={r['mean_baseline']:6.2f} "
              f"{r['difference']:+.2f} [{r['ci_low']:+.2f},{r['ci_high']:+.2f}] p={r['p_value']:.4f}")

    obs = next(r for r in summary if r["subset"] == "all_160" and r["metric"] == "s_auroc_mean")
    print(f"\nk-mix reweighting: Real-IAD mix predicts {float(src_mix @ delta):+.2f}, "
          f"Variety mix predicts {float(var_mix @ delta):+.2f}, observed {obs['difference']:+.2f}")
    for r in summary:
        print(f"  {r['subset']:14s} {r['metric']:14s} n={r['n_categories']:3d} "
              f"{r['Acontinued']:6.2f} -> {r['F']:6.2f}  {r['difference']:+.2f} "
              f"[{r['ci_low']:+.2f},{r['ci_high']:+.2f}] p={r['p_value']:.3f} "
              f"F higher in {r['n_categories_F_higher']}")
    for r in per_fold:
        if r["metric"] == "s_auroc_mean":
            print(f"  fold {r['fold']}: {r['difference']:+.2f} [{r['ci_low']:+.2f},"
                  f"{r['ci_high']:+.2f}] p={r['p_value']:.3f}")


if __name__ == "__main__":
    main()
