#!/usr/bin/env python3
"""How much of the near-zero Variety headroom is predicted by visibility alone?

Variety is dominated by objects whose defect is visible in every view (90.6% at
k = 5), so an oracle that may drop blind views removes almost nothing there. The
question this script answers is quantitative: if Real-IAD, whose visibility mix
is spread across k = 1..5, is reweighted to the Variety mix, how much of its
oracle headroom survives?

Method. Inside each category, anomalous objects are weighted so that the weighted
visibility distribution matches the Variety one; normal objects keep weight 1.
AUROC becomes a weighted Mann-Whitney statistic over anomalous-normal pairs.
Strata absent from a category are dropped and the target renormalised over the
strata present, so the weights are always proper. Category is the sampling unit,
as everywhere else.

Reads raw prediction NPZ files and variety_k_mix.csv; writes kmix_reweight.csv.
"""
from __future__ import annotations

import csv
import glob
from pathlib import Path

import numpy as np
from scipy import stats

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"

DETECTORS = {
    "VisualAD-A": str(EXP / "runs/fold_*/seed_00/A/eval/predictions_fold*.npz"),
    "VisualAD-Acontinued": str(EXP / "runs/fold_*/seed_00/A_continued/eval/predictions_fold*.npz"),
    "AnomalyCLIP-VisA": str(EXP / "baselines/anomalyclip_visa/fold_*/seed_00/AnomalyCLIP/eval/predictions_fold*_shard*of2.npz"),
    "WinCLIP": str(EXP / "baselines/winclip/fold_*/seed_00/WinCLIP/eval/predictions_fold*.npz"),
    "Cross-view NN": str(EXP / "baselines/crossview_nn/fold_*/seed_00/CrossViewNN/eval/predictions_fold*.npz"),
}


def weighted_auroc(pos, neg, w):
    """Weighted Mann-Whitney AUROC, ties counted as half, scale 0-100."""
    pos, neg, w = np.asarray(pos, float), np.asarray(neg, float), np.asarray(w, float)
    if len(pos) == 0 or len(neg) == 0 or w.sum() <= 0:
        return np.nan
    order = np.argsort(neg)
    neg_sorted = neg[order]
    below = np.searchsorted(neg_sorted, pos, side="left")
    equal = np.searchsorted(neg_sorted, pos, side="right") - below
    conc = below + 0.5 * equal
    return 100 * float((w * conc).sum()) / (w.sum() * len(neg))


def mean_scores(s, v):
    return np.asarray([np.asarray(a)[np.asarray(b, bool)].mean() for a, b in zip(s, v)])


def oracle_scores(s, v, il, y):
    out = []
    for a, b, l, lab in zip(s, v, il, y):
        b = np.asarray(b, bool)
        sel = (np.asarray(l, bool) & b) if lab else b
        out.append(np.asarray(a)[sel].mean())
    return np.asarray(out)


def load_target_mix():
    rows = list(csv.DictReader((CSV_DIR / "variety_k_mix.csv").open(encoding="utf-8")))
    return {int(r["k"]): float(r["variety_share"]) for r in rows}


def category_rows(pattern):
    """Yield (category, mean_scores, oracle_scores, object_label, k) per category."""
    for path in sorted(glob.glob(pattern)):
        z = np.load(path, allow_pickle=True)
        cats, y, k = z["category"], z["object_label"].astype(int), z["k"].astype(int)
        s, v, il = z["view_scores"], z["valid"].astype(bool), z["image_labels"].astype(bool)
        m, o = mean_scores(s, v), oracle_scores(s, v, il, y)
        for c in sorted(set(cats.tolist())):
            q = cats == c
            yield c, m[q], o[q], y[q], k[q]


def weights_for(k_anom, target):
    """Weights matching the target visibility mix, renormalised over present strata."""
    present = sorted(set(int(x) for x in k_anom))
    tgt = {kk: target.get(kk, 0.0) for kk in present}
    total = sum(tgt.values())
    if total <= 0:
        return None
    tgt = {kk: v / total for kk, v in tgt.items()}
    counts = {kk: int((k_anom == kk).sum()) for kk in present}
    return np.asarray([tgt[int(x)] / counts[int(x)] for x in k_anom], float)


def ci_t(x):
    x = np.asarray(x, float)
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    return float(x.mean()), float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue)


def main():
    target = load_target_mix()
    rows = []
    for name, pattern in DETECTORS.items():
        plain, reweighted, n_cat = [], [], 0
        for c, m, o, y, k in category_rows(pattern):
            pos, neg = y == 1, y == 0
            if pos.sum() == 0 or neg.sum() == 0:
                continue
            w_flat = np.ones(int(pos.sum()))
            w_mix = weights_for(k[pos], target)
            if w_mix is None:
                continue
            d_plain = (weighted_auroc(o[pos], o[neg], w_flat)
                       - weighted_auroc(m[pos], m[neg], w_flat))
            d_mix = (weighted_auroc(o[pos], o[neg], w_mix)
                     - weighted_auroc(m[pos], m[neg], w_mix))
            if np.isfinite(d_plain) and np.isfinite(d_mix):
                plain.append(d_plain); reweighted.append(d_mix); n_cat += 1
        a, alo, ahi, ap = ci_t(plain)
        b, blo, bhi, bp = ci_t(reweighted)
        rows.append({"detector": name, "n_categories": n_cat,
                     "headroom_observed": a, "obs_ci_low": alo, "obs_ci_high": ahi, "obs_p": ap,
                     "headroom_variety_mix": b, "mix_ci_low": blo, "mix_ci_high": bhi, "mix_p": bp})
        print(f"  {name:<22} observed {a:+.2f} [{alo:+.2f}, {ahi:+.2f}]   "
              f"Variety mix {b:+.2f} [{blo:+.2f}, {bhi:+.2f}]   n_cat={n_cat}")

    fields = ["detector", "n_categories", "headroom_observed", "obs_ci_low", "obs_ci_high",
              "obs_p", "headroom_variety_mix", "mix_ci_low", "mix_ci_high", "mix_p"]
    out = CSV_DIR / "kmix_reweight.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("wrote", out.name)


if __name__ == "__main__":
    main()
