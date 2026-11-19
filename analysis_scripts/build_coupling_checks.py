#!/usr/bin/env python3
"""Permutation nulls for the derived quantities the analysis uses.

Two of the quantities this study computes are differences of differences across
two evaluation levels, and such quantities share terms by construction. A
correlation between them therefore has a non-zero null, and comparing it to
zero is meaningless. Likewise, selecting categories by their baseline score and
then measuring a change from that baseline induces regression to the mean, so
the subgroup effect also has a non-zero null.

This script computes those nulls explicitly. It exists because the first draft
of Section 6.5 reported both quantities against a null of zero and drew a
mechanism conclusion that the nulls do not support.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

PAPER = Path(__file__).resolve().parents[1]
CSV_DIR = PAPER / "paper_assets/results"
N_PERM = 20000
SEED = 0


def load(name, text=()):
    out = []
    for r in csv.DictReader((CSV_DIR / name).open(encoding="utf-8")):
        out.append({k: (v if k in text else float(v)) for k, v in r.items()})
    return out


def per_category(rows, detector, metric):
    acc = {}
    for r in rows:
        if r["detector"] == detector:
            acc.setdefault(r["category"], []).append(r[metric])
    return np.array([np.mean(acc[c]) for c in sorted(acc)])


def main():
    rng = np.random.default_rng(SEED)
    out = []
    v = load("variety_category_metrics.csv", text=("detector", "category"))
    Ib = per_category(v, "VisualAD-Acontinued", "i_auroc")
    Sb = per_category(v, "VisualAD-Acontinued", "s_auroc_mean")
    Im = per_category(v, "VisualAD-F", "i_auroc")
    Sm = per_category(v, "VisualAD-F", "s_auroc_mean")

    # ---- 1. lift of the control vs the part of the upstream gain not retained
    Lb, Lm = Sb - Ib, Sm - Im
    absorbed = (Im - Ib) - (Sm - Sb)
    assert np.abs(absorbed - (Lb - Lm)).max() < 1e-9, "identity broken"
    obs = float(np.corrcoef(Lb, absorbed)[0, 1])
    sim = np.array([np.corrcoef(Lb, Lb - rng.permutation(Lm))[0, 1]
                    for _ in range(N_PERM)])
    out.append({"quantity": "corr(aggregation_lift, gain_not_retained)",
                "observed": obs, "null_mean": float(sim.mean()),
                "null_lo": float(np.percentile(sim, 2.5)),
                "null_hi": float(np.percentile(sim, 97.5)),
                "percentile_of_observed": float(100 * (sim < obs).mean()),
                "note": "shares the lift term by construction; observed sits below the null"})

    # ---- 2. baseline vs the change measured from that same baseline ---------
    obs = float(np.corrcoef(Sb, Sm - Sb)[0, 1])
    sim = np.array([np.corrcoef(Sb, rng.permutation(Sm) - Sb)[0, 1] for _ in range(N_PERM)])
    out.append({"quantity": "corr(baseline, object_delta)", "observed": obs,
                "null_mean": float(sim.mean()), "null_lo": float(np.percentile(sim, 2.5)),
                "null_hi": float(np.percentile(sim, 97.5)),
                "percentile_of_observed": float(100 * (sim < obs).mean()),
                "note": "regression to the mean; observed is far weaker than the null"})

    # ---- 3. Table 7.1, which shares only the object-level term --------------
    role = load("discussion_aggregation_role.csv", text=("operating_point", "dataset"))
    I = np.array([r["i_auroc"] for r in role]); S = np.array([r["s_auroc"] for r in role])
    H = np.array([r["oracle_headroom"] for r in role]); O = S + H
    obs = float(np.corrcoef(S - I, H)[0, 1])
    sim = np.array([np.corrcoef(S - I, O[rng.permutation(len(S))] - S)[0, 1]
                    for _ in range(N_PERM)])
    out.append({"quantity": "corr(aggregation_lift, oracle_headroom)", "observed": obs,
                "null_mean": float(sim.mean()), "null_lo": float(np.percentile(sim, 2.5)),
                "null_hi": float(np.percentile(sim, 97.5)),
                "percentile_of_observed": float(100 * (sim < obs).mean()),
                "note": "null is near zero, so this relationship is not an artefact"})

    with (CSV_DIR / "coupling_checks.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

    # ---- 4. subgroup selected on the baseline, under label exchange ---------
    sub = []
    for t in (80, 85, 88, 90, 92, 95):
        mask = Sb < t
        obs = float((Sm - Sb)[mask].mean())
        sim = []
        for _ in range(5000):
            flip = rng.random(len(Sb)) < .5
            b = np.where(flip, Sm, Sb); m = np.where(flip, Sb, Sm)
            sel = b < t
            if sel.any():
                sim.append((m - b)[sel].mean())
        sim = np.array(sim)
        sub.append({"threshold": t, "n_categories": int(mask.sum()), "observed": obs,
                    "null_mean": float(sim.mean()), "null_sd": float(sim.std()),
                    "p_permutation": float((np.abs(sim) >= abs(obs)).mean())})
    with (CSV_DIR / "saturation_permutation.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sub[0])); w.writeheader(); w.writerows(sub)

    for r in out:
        print(f"{r['quantity']:46s} obs {r['observed']:+.3f}  null "
              f"{r['null_mean']:+.3f} [{r['null_lo']:+.3f},{r['null_hi']:+.3f}]  "
              f"pct {r['percentile_of_observed']:.1f}")
    print()
    for r in sub:
        print(f"  baseline < {r['threshold']}: n={r['n_categories']:3d} obs {r['observed']:+.2f}  "
              f"null {r['null_mean']:+.2f}+-{r['null_sd']:.2f}  p_perm={r['p_permutation']:.3f}")
    print("\nwrote coupling_checks.csv, saturation_permutation.csv")


if __name__ == "__main__":
    main()
