#!/usr/bin/env python3
"""Five further score-level fusion rules and one camera-aware learned aggregator.

Runs exactly the family fixed in archive/protocol/DECISION_RULE_NEW_AGGREGATORS.md, which
was written and committed before this script was run. Rules, hyperparameter grids,
metric, sampling unit and decision threshold all come from that file; nothing here
was chosen after seeing a result, and every rule tried is reported.

Group A (no labels, hyperparameter by leave-one-fold-out), all four families:
  A1 power mean over within-category rank-normalised scores, p in {1,2,4,8,16}
  A2 log-sum-exp over raw scores, tau in {0.25,0.5,1,2,4}
  A3 product rule over rank-normalised scores
  A4 noisy-OR over rank-normalised scores
  A5 per-camera z-score, statistics from training-fold categories, then mean
Group B (learned, leave-one-fold-out), three VisualAD operating points:
  B1 logistic regression on the five scores in camera order, without sorting

Rank normalisation uses only the score distribution of the category being scored,
never its labels, so the rules remain valid zero-shot aggregators.

Reads raw prediction NPZ files; writes extra_aggregators.csv.
"""
from __future__ import annotations

import csv
import glob
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
CSV_DIR = PAPER / "paper_assets/results"
N_NEW_COMPARISONS = 23          # fixed in the decision-rule file

FAMILIES = {
    "VisualAD-A": str(EXP / "runs/fold_*/seed_00/A/eval/predictions_fold*.npz"),
    "AnomalyCLIP-VisA": str(EXP / "baselines/anomalyclip_visa/fold_*/seed_00/AnomalyCLIP/eval/predictions_fold*_shard*of2.npz"),
    "WinCLIP": str(EXP / "baselines/winclip/fold_*/seed_00/WinCLIP/eval/predictions_fold*.npz"),
    "Cross-view NN": str(EXP / "baselines/crossview_nn/fold_*/seed_00/CrossViewNN/eval/predictions_fold*.npz"),
}
OPERATING_POINTS = {
    "f_base": str(EXP / "runs/fold_*/seed_00/A/eval/predictions_fold*.npz"),
    "f_budget": str(EXP / "runs/fold_*/seed_00/A_continued/eval/predictions_fold*.npz"),
    "f_mv": str(EXP / "runs/fold_*/seed_00/F/eval/predictions_fold*.npz"),
}
P_GRID = (1, 2, 4, 8, 16)
TAU_GRID = (0.25, 0.5, 1.0, 2.0, 4.0)
EPS = 1e-9


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def read_folds(pattern):
    """[{category: (scores, valid, labels)} per fold], in fold order.

    AnomalyCLIP writes two shards per fold; the fold index comes from the
    directory name, so shards of one fold merge into one dictionary.
    """
    out = [dict() for _ in range(5)]
    paths = sorted(glob.glob(pattern))
    assert paths, pattern
    for path in paths:
        fold = int(next(part for part in Path(path).parts
                        if part.startswith("fold_")).split("_")[1])
        z = np.load(path, allow_pickle=True)
        cats, y = z["category"], z["object_label"].astype(int)
        s, v = z["view_scores"].astype(float), z["valid"].astype(bool)
        for c in sorted(set(cats.tolist())):
            q = cats == c
            assert c not in out[fold], f"category {c} appears twice in fold {fold}"
            out[fold][c] = (s[q], v[q], y[q])
    assert all(len(f) for f in out), pattern
    return out


def rank_unit(s, v):
    """Within-category rank of every valid view score, mapped into (0,1)."""
    u = np.full(s.shape, np.nan)
    flat = s[v]
    u[v] = (stats.rankdata(flat) - 0.5) / len(flat)
    return u


def agg_mean(s, v, **_):
    return np.asarray([row[m].mean() for row, m in zip(s, v)])


def agg_power(s, v, p=1, **_):
    u = rank_unit(s, v)
    return np.asarray([(row[m] ** p).mean() ** (1.0 / p) for row, m in zip(u, v)])


def agg_lse(s, v, tau=1.0, **_):
    out = []
    for row, m in zip(s, v):
        x = row[m] / tau
        out.append(tau * (x.max() + np.log(np.exp(x - x.max()).sum())))
    return np.asarray(out)


def agg_product(s, v, **_):
    u = rank_unit(s, v)
    return np.asarray([np.log(row[m] + EPS).sum() for row, m in zip(u, v)])


def agg_noisy_or(s, v, **_):
    u = rank_unit(s, v)
    return np.asarray([-np.log(1.0 - row[m] + EPS).sum() for row, m in zip(u, v)])


def agg_zcam(s, v, stats_=None, **_):
    mu, sd = stats_
    z = (s - mu) / sd
    return np.asarray([row[m].mean() for row, m in zip(z, v)])


def camera_stats(folds, idx):
    """Per-camera mean and sd pooled over the categories of the given folds."""
    rows = [s for f in idx for c, (s, v, y) in folds[f].items()]
    X = np.concatenate(rows, axis=0)
    return X.mean(0), X.std(0) + EPS


def ci_t(x):
    x = np.asarray(x, float)
    m, se = float(x.mean()), float(stats.sem(x))
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=m, scale=se)
    p = float(stats.ttest_1samp(x, 0).pvalue)
    df = len(x) - 1
    scale = stats.t.ppf(1 - (0.05 / N_NEW_COMPARISONS) / 2, df) / stats.t.ppf(0.975, df)
    half = (hi - lo) / 2 * scale
    return m, lo, hi, p, m - half, m + half


def evaluate_group_a(name, folds):
    rows = []
    for rule, fn, grid, key in (("power mean", agg_power, P_GRID, "p"),
                                ("log-sum-exp", agg_lse, TAU_GRID, "tau"),
                                ("product", agg_product, (None,), None),
                                ("noisy-OR", agg_noisy_or, (None,), None),
                                ("per-camera z-score", agg_zcam, (None,), None)):
        deltas, chosen = [], []
        for f in range(5):
            train = [i for i in range(5) if i != f]
            kw = {}
            if rule == "per-camera z-score":
                kw["stats_"] = camera_stats(folds, train)
            if grid != (None,):
                best, best_score = grid[0], -np.inf
                for g in grid:
                    vals = []
                    for t in train:
                        for c, (s, v, y) in folds[t].items():
                            vals.append(auroc(fn(s, v, **{key: g}, **kw), y))
                    m = float(np.nanmean(vals))
                    if m > best_score:
                        best, best_score = g, m
                kw[key] = best
                chosen.append(best)
            for c, (s, v, y) in folds[f].items():
                deltas.append(auroc(fn(s, v, **kw), y) - auroc(agg_mean(s, v), y))
        m, lo, hi, p, blo, bhi = ci_t(deltas)
        rows.append({"group": "A", "detector": name, "rule": rule,
                     "hyperparameter": "|".join(str(x) for x in chosen) if chosen else "",
                     "n_categories": len(deltas), "delta_vs_mean": m,
                     "ci_low": lo, "ci_high": hi, "p_vs_mean": p,
                     "bonf_ci_low": blo, "bonf_ci_high": bhi})
        print(f"  {name:<20} {rule:<20} {m:+7.2f} [{lo:+6.2f}, {hi:+6.2f}]"
              f"  Bonf [{blo:+6.2f}, {bhi:+6.2f}]"
              + (f"  chosen {chosen}" if chosen else ""))
    return rows


def evaluate_group_b(name, folds):
    deltas = []
    for f in range(5):
        train = [i for i in range(5) if i != f]
        X = np.concatenate([s for t in train for c, (s, v, y) in folds[t].items()])
        Y = np.concatenate([y for t in train for c, (s, v, y) in folds[t].items()])
        mu, sd = X.mean(0), X.std(0) + EPS
        clf = LogisticRegression(max_iter=5000)
        clf.fit((X - mu) / sd, Y)
        for c, (s, v, y) in folds[f].items():
            score = clf.decision_function((s - mu) / sd)
            deltas.append(auroc(score, y) - auroc(agg_mean(s, v), y))
    m, lo, hi, p, blo, bhi = ci_t(deltas)
    print(f"  {name:<20} {'logistic, camera order':<20} {m:+7.2f} [{lo:+6.2f}, {hi:+6.2f}]"
          f"  Bonf [{blo:+6.2f}, {bhi:+6.2f}]")
    return [{"group": "B", "detector": name, "rule": "logistic, camera order",
             "hyperparameter": "", "n_categories": len(deltas), "delta_vs_mean": m,
             "ci_low": lo, "ci_high": hi, "p_vs_mean": p,
             "bonf_ci_low": blo, "bonf_ci_high": bhi}]


def main():
    rows = []
    print("Group A: five label-free rules on four detector families")
    for name, pattern in FAMILIES.items():
        rows += evaluate_group_a(name, read_folds(pattern))
    print("\nGroup B: camera-aware logistic regression on three operating points")
    for name, pattern in OPERATING_POINTS.items():
        rows += evaluate_group_b(name, read_folds(pattern))

    assert len(rows) == N_NEW_COMPARISONS, f"{len(rows)} rows, expected {N_NEW_COMPARISONS}"
    fields = ["group", "detector", "rule", "hyperparameter", "n_categories",
              "delta_vs_mean", "ci_low", "ci_high", "p_vs_mean", "bonf_ci_low", "bonf_ci_high"]
    out = CSV_DIR / "extra_aggregators.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("\nwrote", out.name)

    print("\nDecision, applying the locked rule")
    c1 = [r for r in rows if r["ci_low"] > 0]
    c2 = [r for r in rows if r["bonf_ci_low"] > 0]
    print(f"  condition 1, 95% interval excludes zero upward: {len(c1)} of {len(rows)}")
    for r in c1:
        print(f"      {r['detector']} / {r['rule']}  {r['delta_vs_mean']:+.2f}")
    print(f"  condition 2, survives Bonferroni over {N_NEW_COMPARISONS}: {len(c2)} of {len(rows)}")
    for r in c2:
        print(f"      {r['detector']} / {r['rule']}  {r['delta_vs_mean']:+.2f}")
    print("  scenario", 3 if c2 else (2 if c1 else 1), "of the decision-rule file")


if __name__ == "__main__":
    main()
