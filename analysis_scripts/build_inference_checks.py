#!/usr/bin/env python3
"""Three inferential checks the audit asked for, all from stored predictions.

1. Trend across visibility. The rare-evidence hypothesis predicts that the
   upstream gain shrinks as the defect becomes visible in more views. We regress
   the per-category f_mv - f_budget difference on k inside each category and test
   the slopes across categories, and we also contrast k <= 2 against k = 5.

2. Clustering by checkpoint. Six categories share each fold's checkpoint, so the
   30 category differences are not independent. We estimate the one-way
   intra-cluster correlation with folds as clusters, form the design effect
   1 + (m - 1) * ICC, and widen the interval by its square root.

3. Multiplicity. Bonferroni-adjusted simultaneous intervals for the family of
   16 fixed comparisons on Real-IAD and for the 4 Variety oracle comparisons,
   plus the smallest equivalence margin each near-equivalence claim still meets.
   For an equivalence claim a correction widens the interval, so it makes the
   claim harder, not easier.

Reads raw prediction NPZ files, aggregation_summary.csv and the two Variety
summaries; writes inference_checks.csv.
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

VARIANTS = {"f_base": "A", "f_budget": "A_continued", "f_mv": "F"}


def load(name, num_skip=()):
    out = []
    for r in csv.DictReader((CSV_DIR / name).open(encoding="utf-8")):
        row = {}
        for k, v in r.items():
            if k in num_skip:
                row[k] = v
            else:
                try:
                    row[k] = float(v)
                except (TypeError, ValueError):
                    row[k] = v
        out.append(row)
    return out


def ci_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    m, se = float(x.mean()), float(stats.sem(x))
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=m, scale=se)
    return m, float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue), len(x), se


def icc_oneway(values, groups):
    """One-way random-effects ICC(1) with folds as clusters."""
    values, groups = np.asarray(values, float), np.asarray(groups)
    g = sorted(set(groups.tolist()))
    n = np.array([int((groups == x).sum()) for x in g], float)
    means = np.array([values[groups == x].mean() for x in g])
    grand = values.mean()
    k = len(g)
    msb = float((n * (means - grand) ** 2).sum() / (k - 1))
    msw = float(sum(((values[groups == x] - values[groups == x].mean()) ** 2).sum()
                    for x in g) / (len(values) - k))
    n0 = (n.sum() - (n ** 2).sum() / n.sum()) / (k - 1)
    icc = (msb - msw) / (msb + (n0 - 1) * msw)
    return float(icc), float(n0)




def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def per_category():
    """{category: {"fold": f, variant: {"i": .., "s": .., "oracle": .., "k": {k: s_auroc}}}}"""
    out = {}
    for fold in range(5):
        for name, var in VARIANTS.items():
            paths = sorted((EXP / f"runs/fold_{fold:02d}/seed_00/{var}/eval").glob("predictions_fold*.npz"))
            paths = [p for p in paths if "variety" not in p.name]
            assert len(paths) == 1, paths
            z = np.load(paths[0], allow_pickle=True)
            cats, y, kk = z["category"], z["object_label"].astype(int), z["k"].astype(int)
            s, v, il = z["view_scores"], z["valid"].astype(bool), z["image_labels"].astype(bool)
            m = np.asarray([np.asarray(a)[np.asarray(b, bool)].mean() for a, b in zip(s, v)])
            o = []
            for a, b, l, t in zip(s, v, il, y):
                b = np.asarray(b, bool)
                sel = (np.asarray(l, bool) & b) if t else b
                o.append(np.asarray(a)[sel].mean())
            o = np.asarray(o)
            for c in sorted(set(cats.tolist())):
                q = cats == c
                e = out.setdefault(c, {"fold": fold}).setdefault(name, {})
                e["i"] = np.mean([auroc(s[q][v[q]], il[q][v[q]].astype(int))])
                e["s"] = auroc(m[q], y[q])
                e["oracle"] = auroc(o[q], y[q])
                per_k = {}
                for kv in range(1, 6):
                    sel = (y[q] == 0) | (kk[q] == kv)
                    per_k[kv] = auroc(m[q][sel], y[q][sel]) if (kk[q][y[q] == 1] == kv).any() else np.nan
                e["k"] = per_k
    return out

def main():
    rows = []
    cat = per_category()
    cats_all = sorted(cat)

    # ---- 1. trend across visibility ----------------------------------------
    slopes, contrasts = [], []
    for c in cats_all:
        diff = np.array([cat[c]["f_mv"]["k"][kv] - cat[c]["f_budget"]["k"][kv]
                         for kv in range(1, 6)])
        ok = np.isfinite(diff)
        if ok.sum() >= 3:
            slopes.append(float(np.polyfit(np.arange(1, 6)[ok], diff[ok], 1)[0]))
        low = diff[:2][np.isfinite(diff[:2])]
        if len(low) and np.isfinite(diff[4]):
            contrasts.append(float(low.mean() - diff[4]))
    for label, vals in (("trend slope of f_mv - f_budget on k", slopes),
                        ("contrast k<=2 minus k=5", contrasts)):
        m, lo, hi, p, n, _ = ci_t(vals)
        rows.append({"check": "visibility trend", "quantity": label, "n": n,
                     "estimate": m, "ci_low": lo, "ci_high": hi, "p_value": p})
        print(f"  {label:<38} {m:+.3f} [{lo:+.3f}, {hi:+.3f}]  p={p:.3f}  n={n}")

    # ---- 2. clustering by checkpoint ---------------------------------------
    print()
    pairs = {"f_mv - f_budget, S-AUROC": ("f_mv", "f_budget", "s"),
             "f_mv - f_budget, I-AUROC": ("f_mv", "f_budget", "i"),
             "oracle headroom, f_base": ("f_base", "f_base", "headroom")}
    for label, (a, b, metric) in pairs.items():
        cats = cats_all
        if metric == "headroom":
            d = np.array([cat[c][a]["oracle"] - cat[c][a]["s"] for c in cats])
        else:
            d = np.array([cat[c][a][metric] - cat[c][b][metric] for c in cats])
        folds = np.array([cat[c]["fold"] for c in cats])
        m, lo, hi, p, n, se = ci_t(d)
        icc, n0 = icc_oneway(d, folds)
        deff = max(1.0, 1 + (n0 - 1) * icc)
        half = (hi - lo) / 2 * np.sqrt(deff)
        rows.append({"check": "clustering", "quantity": label, "n": n,
                     "estimate": m, "ci_low": lo, "ci_high": hi, "p_value": p,
                     "icc": icc, "design_effect": deff,
                     "adj_ci_low": m - half, "adj_ci_high": m + half})
        print(f"  {label:<26} {m:+.2f} [{lo:+.2f}, {hi:+.2f}]  ICC={icc:+.3f}  "
              f"deff={deff:.2f}  adjusted [{m - half:+.2f}, {m + half:+.2f}]")

    # ---- 3. multiplicity ----------------------------------------------------
    print()
    agg = load("aggregation_summary.csv", num_skip=("detector", "aggregation"))
    G = lambda d, a, f: next(r[f] for r in agg if r["detector"] == d and r["aggregation"] == a)
    DETS = ["VisualAD-A", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN"]
    RULES = ["max", "top2", "top3", "median"]
    n_fam = len(DETS) * len(RULES)
    alpha = 0.05 / n_fam
    worst = 0.0
    for d in DETS:
        for a in RULES:
            m = G(d, a, "delta_vs_mean")
            half = (G(d, a, "ci_high") - G(d, a, "ci_low")) / 2
            scale = stats.t.ppf(1 - alpha / 2, 29) / stats.t.ppf(0.975, 29)
            worst = max(worst, m + half * scale)
    rows.append({"check": "multiplicity", "quantity": "Bonferroni upper limit, 16 fixed rules",
                 "n": n_fam, "estimate": worst})
    print(f"  16 fixed rules, Bonferroni: largest simultaneous upper limit {worst:+.2f}")

    vb = load("variety_baselines_summary.csv", num_skip=("detector", "aggregation"))
    va = load("variety_aggregation_summary.csv", num_skip=("detector", "aggregation"))
    allv = vb + va
    V = lambda d, a, f: next(r[f] for r in allv if r["detector"] == d and r["aggregation"] == a)
    FAM = ["VisualAD-Acontinued", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN"]
    scale = stats.t.ppf(1 - (0.05 / 4) / 2, 159) / stats.t.ppf(0.975, 159)
    margin = 0.0
    for d in FAM:
        m = V(d, "oracle_mean", "delta_vs_mean")
        half = (V(d, "oracle_mean", "ci_high") - V(d, "oracle_mean", "ci_low")) / 2 * scale
        margin = max(margin, abs(m) + half)
    rows.append({"check": "multiplicity", "quantity": "smallest equivalence margin, Variety oracle",
                 "n": 4, "estimate": margin})
    print(f"  4 Variety oracle comparisons, Bonferroni: near-equivalence holds "
          f"at any margin >= {margin:.2f} points")

    fields = ["check", "quantity", "n", "estimate", "ci_low", "ci_high", "p_value",
              "icc", "design_effect", "adj_ci_low", "adj_ci_high"]
    out = CSV_DIR / "inference_checks.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print("\nwrote", out.name)


if __name__ == "__main__":
    main()
