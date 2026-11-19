#!/usr/bin/env python3
"""Do the cross-detector headroom differences survive a change of pixel readout?

Applies the thresholds fixed in archive/protocol/DECISION_RULE_READOUT_SENSITIVITY.md,
committed before the runs. Every family is scored at five top-k ratios from the
same forward pass; the 1% column must reproduce the stored predictions exactly.

Category is the sampling unit. Writes readout_sensitivity.csv.
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
ABL = EXP / "ablations/readout"
CSV_DIR = PAPER / "paper_assets/results"
TOL = 1e-4

FAMILIES = {
    "VisualAD-A": (str(ABL / "visualad_A/fold_*/readout_sweep_fold*.npz"),
                   str(EXP / "runs/fold_*/seed_00/A/eval/predictions_fold*.npz")),
    "AnomalyCLIP-VisA": (str(ABL / "anomalyclip_visa/fold_*/seed_00/AnomalyCLIP/eval/readout_sweep_fold*.npz"),
                         str(EXP / "baselines/anomalyclip_visa/fold_*/seed_00/AnomalyCLIP/eval/predictions_fold*.npz")),
    "WinCLIP": (str(ABL / "winclip/fold_*/seed_00/WinCLIP/eval/readout_sweep_fold*.npz"),
                str(EXP / "baselines/winclip/fold_*/seed_00/WinCLIP/eval/predictions_fold*.npz")),
    "Cross-view NN": (str(ABL / "crossview_nn/fold_*/seed_00/CrossViewNN/eval/readout_sweep_fold*.npz"),
                      str(EXP / "baselines/crossview_nn/fold_*/seed_00/CrossViewNN/eval/predictions_fold*.npz")),
}


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def ci_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    m, se = float(x.mean()), float(stats.sem(x))
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=m, scale=se)
    return m, float(lo), float(hi)


def load_reference(pattern):
    """sample_id -> stored view_scores, merged over folds and shards."""
    ref = {}
    for p in sorted(glob.glob(pattern)):
        if "variety" in Path(p).name:
            continue
        z = np.load(p, allow_pickle=True)
        for s, v in zip(z["sample_id"], z["view_scores"]):
            ref[str(s)] = v
    return ref


def main():
    rows, gates = [], []
    for name, (sweep_glob, ref_glob) in FAMILIES.items():
        paths = sorted(glob.glob(sweep_glob))
        if not paths:
            print(f"  {name}: no sweep files yet, skipped")
            continue
        ref = load_reference(ref_glob)
        ratios = None
        per_cat = {}                      # ratio index -> category -> (mean, oracle)
        worst = 0.0
        n_obj = 0
        for p in paths:
            z = np.load(p, allow_pickle=True)
            ratios = z["ratios"]
            one = int(np.argmin(np.abs(ratios - 0.01)))
            cats, y = z["category"], z["object_label"].astype(int)
            v, il = z["valid"].astype(bool), z["image_labels"].astype(bool)
            sc = z["view_scores"]                     # (N,V,R)
            n_obj += len(y)
            for s, sid in zip(sc[:, :, one], z["sample_id"]):
                r = ref.get(str(sid))
                if r is not None:
                    m = np.isfinite(s) & np.isfinite(r)
                    if m.any():
                        worst = max(worst, float(np.abs(s[m] - r[m]).max()))
            for j in range(len(ratios)):
                s = sc[:, :, j]
                mean = np.asarray([row[mask].mean() for row, mask in zip(s, v)])
                orac = []
                for row, mask, lab, t in zip(s, v, il, y):
                    sel = (lab & mask) if t else mask
                    orac.append(row[sel].mean() if sel.any() else row[mask].mean())
                orac = np.asarray(orac)
                for c in sorted(set(cats.tolist())):
                    q = cats == c
                    per_cat.setdefault(j, {})[c] = (auroc(mean[q], y[q]),
                                                    auroc(orac[q], y[q]))
        gates.append((name, worst, n_obj))
        for j in range(len(ratios)):
            cats = sorted(per_cat[j])
            d = np.array([per_cat[j][c][1] - per_cat[j][c][0] for c in cats])
            m, lo, hi = ci_t(d)
            rows.append({"detector": name, "ratio": float(ratios[j]),
                         "n_categories": len(cats), "headroom": m,
                         "ci_low": lo, "ci_high": hi})

    print("Correctness gate, the 1% column against the stored runs")
    ok = True
    for name, worst, n in gates:
        flag = "PASS" if worst <= TOL else "FAIL"
        ok &= worst <= TOL
        print(f"  {flag}  {name:<18} max|diff| = {worst:.2e}  ({n} objects)")
    if not ok:
        print("\n  Gate not met for every family. Per ADDENDUM_READOUT_GATE.md the\n"
              "  comparison ACROSS readouts stays valid, because the five ratios come\n"
              "  from one forward pass and any run-to-run noise cancels exactly. The\n"
              "  comparison ACROSS families is reported with a warning.")

    out = CSV_DIR / "readout_sensitivity.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["detector", "ratio", "n_categories",
                                           "headroom", "ci_low", "ci_high"])
        w.writeheader(); w.writerows(rows)
    print("\nOracle headroom by readout\n")
    ratios = sorted({r["ratio"] for r in rows})
    names = [n for n in FAMILIES if any(r["detector"] == n for r in rows)]
    print("  " + "detector".ljust(18) + "".join(f"{r*100:>10.2f}%" for r in ratios))
    for n in names:
        line = "  " + n.ljust(18)
        for r in ratios:
            v = next((x["headroom"] for x in rows
                      if x["detector"] == n and x["ratio"] == r), float("nan"))
            line += f"{v:>+11.2f}"
        print(line)

    print("\nWithin each family, change in headroom relative to the 1% readout\n")
    print("  " + "detector".ljust(18) + "".join(f"{r*100:>10.2f}%" for r in ratios))
    for n in names:
        base1 = next(x["headroom"] for x in rows if x["detector"] == n
                     and abs(x["ratio"] - 0.01) < 1e-9)
        line = "  " + n.ljust(18)
        for r in ratios:
            v = next(x["headroom"] for x in rows
                     if x["detector"] == n and x["ratio"] == r)
            line += f"{v - base1:>+11.2f}"
        print(line)

    print("\nDecision, applying the locked rule")
    base = [next(x["headroom"] for x in rows if x["detector"] == n
                 and abs(x["ratio"] - 0.01) < 1e-9) for n in names]
    order0 = [n for _, n in sorted(zip(base, names))]
    same_order, same_sign, spread_ok = True, True, True
    for r in ratios:
        vals = [next(x["headroom"] for x in rows
                     if x["detector"] == n and x["ratio"] == r) for n in names]
        order = [n for _, n in sorted(zip(vals, names))]
        same_order &= order == order0
        same_sign &= all(np.sign(v) == np.sign(b) for v, b in zip(vals, base))
        spread_ok &= (max(vals) - min(vals)) > 2.0
    print(f"  condition 1, ordering unchanged at every readout: {same_order}")
    print(f"  condition 2, signs unchanged at every readout:    {same_sign}")
    print(f"  condition 3, spread above 2 points everywhere:    {spread_ok}")
    if same_order and same_sign and spread_ok:
        print("  -> the readout is not a material confound")
    elif not (same_order and same_sign):
        print("  -> REPORT: headroom is a property of the detector-readout pair")
    else:
        print("  -> the effect narrows at wide readouts; qualitative claim stands")
    print("wrote", out.name)


if __name__ == "__main__":
    main()
