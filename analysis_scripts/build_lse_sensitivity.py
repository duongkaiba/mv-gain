#!/usr/bin/env python3
"""Post-hoc sensitivity of log-sum-exp pooling to its temperature.

NOT part of the family locked in archive/protocol/DECISION_RULE_NEW_AGGREGATORS.md. That
family selected the temperature on the four training folds, which is the right
thing to do for a deployable rule but inflates the variance of the resulting
comparison. An external audit asked what happens at a fixed temperature, and the
answer changes how the central claim must be worded, so it is reported in full
here and marked post-hoc wherever it appears. See
archive/protocol/ADDENDUM_LSE_SENSITIVITY.md.

Two grids are run.

  absolute   tau in raw score units, as in the locked run. Not comparable across
             detector families, whose score scales differ by more than an order
             of magnitude; this is a flaw of the locked design and is the reason
             log-sum-exp looked inert on the untrained families.
  scaled     tau expressed in units of the within-category standard deviation of
             the valid view scores, which makes one grid mean the same thing for
             every family.

Reads raw prediction NPZ files; writes lse_sensitivity.csv.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import stats

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_extra_aggregators import (  # noqa: E402
    FAMILIES, OPERATING_POINTS, N_NEW_COMPARISONS, agg_mean, auroc, read_folds)

PAPER = Path(__file__).resolve().parents[1]
CSV_DIR = PAPER / "paper_assets/results"
TAU_ABS = (0.25, 0.5, 1.0, 2.0, 4.0)
TAU_REL = (0.25, 0.5, 1.0, 2.0, 4.0)


def lse(s, v, tau):
    out = []
    for row, m in zip(s, v):
        x = row[m] / tau
        out.append(tau * (x.max() + np.log(np.exp(x - x.max()).sum())))
    return np.asarray(out)


def lse_scaled(s, v, rel):
    """Temperature set to rel times the spread of this category's view scores."""
    sd = float(np.std(s[v]))
    return lse(s, v, max(rel * sd, 1e-6))


def ci_bonf(x, n_family=N_NEW_COMPARISONS):
    x = np.asarray(x, float)
    m, se, df = float(x.mean()), float(stats.sem(x)), len(x) - 1
    lo, hi = stats.t.interval(0.95, df, loc=m, scale=se)
    scale = stats.t.ppf(1 - (0.05 / n_family) / 2, df) / stats.t.ppf(0.975, df)
    half = (hi - lo) / 2 * scale
    return m, float(lo), float(hi), m - half, m + half


def main():
    targets = dict(OPERATING_POINTS)
    for name, pattern in FAMILIES.items():
        if name != "VisualAD-A":
            targets[name] = pattern

    rows = []
    for name, pattern in targets.items():
        folds = read_folds(pattern)
        for grid, fn, taus in (("absolute", lambda s, v, t: lse(s, v, t), TAU_ABS),
                               ("scaled", lse_scaled, TAU_REL)):
            for tau in taus:
                d = []
                for f in range(5):
                    for c, (s, v, y) in folds[f].items():
                        d.append(auroc(fn(s, v, tau), y) - auroc(agg_mean(s, v), y))
                m, lo, hi, blo, bhi = ci_bonf(d)
                rows.append({"detector": name, "grid": grid, "tau": tau,
                             "n_categories": len(d), "delta_vs_mean": m,
                             "ci_low": lo, "ci_high": hi,
                             "bonf_ci_low": blo, "bonf_ci_high": bhi,
                             "beats_mean_bonferroni": int(blo > 0)})
                print(f"  {name:<18} {grid:<8} tau={tau:<5} {m:+.2f} "
                      f"[{lo:+.2f},{hi:+.2f}]  Bonf [{blo:+.2f},{bhi:+.2f}]"
                      + ("  BEATS MEAN" if blo > 0 else ""))

    fields = ["detector", "grid", "tau", "n_categories", "delta_vs_mean",
              "ci_low", "ci_high", "bonf_ci_low", "bonf_ci_high",
              "beats_mean_bonferroni"]
    out = CSV_DIR / "lse_sensitivity.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("\nwrote", out.name)

    best = max(rows, key=lambda r: r["delta_vs_mean"])
    sig = [r for r in rows if r["beats_mean_bonferroni"]]
    print(f"largest gain anywhere: {best['delta_vs_mean']:+.2f} "
          f"({best['detector']}, {best['grid']} tau={best['tau']})")
    print(f"cells beating the mean under Bonferroni: {len(sig)} of {len(rows)}")


if __name__ == "__main__":
    main()
