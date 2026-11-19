#!/usr/bin/env python3
"""Is the upstream gain of f_mv produced by cross-view context at inference?

Applies the thresholds fixed in archive/protocol/DECISION_RULE_CONTEXT_ABLATION.md,
committed before the runs. Three scoring modes over identical objects:

  real  view scored inside its own five views
  solo  view scored alone
  swap  view scored with the four views of a different normal object

Category is the sampling unit. Reads the ablation NPZ files and the stored
f_mv / f_budget predictions; writes context_ablation.csv.
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
ABL = EXP / "ablations/context"
CSV_DIR = PAPER / "paper_assets/results"
MODES = ("real", "solo", "swap")
METHOD_GAP = 3.44          # f_mv - f_budget at the image level, from Table 7
TOL = 1e-4


def auroc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    npos, nneg = int(labels.sum()), int((labels == 0).sum())
    if npos == 0 or nneg == 0:
        return np.nan
    r = stats.rankdata(scores)
    return 100 * float(r[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def ci_t(x):
    x = np.asarray(x, float)
    m, se = float(x.mean()), float(stats.sem(x))
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=m, scale=se)
    return m, float(lo), float(hi), float(stats.ttest_1samp(x, 0).pvalue)


def gate(z, fold):
    """The real mode must reproduce the stored f_mv predictions exactly."""
    p = sorted((EXP / f"runs/fold_{fold:02d}/seed_00/F/eval").glob("predictions_fold*.npz"))
    p = [q for q in p if "variety" not in q.name]
    assert len(p) == 1, p
    ref = np.load(p[0], allow_pickle=True)
    key = {f"{c}/{s}": i for i, (c, s) in enumerate(zip(ref["category"], ref["sample_id"]))}
    idx = [key[f"{c}/{s}"] for c, s in zip(z["category"], z["sample_id"])]
    d = float(np.abs(z["view_scores_real"] - ref["view_scores"][idx]).max())
    if d > TOL:
        raise SystemExit(f"fold {fold}: real mode differs from the stored run by {d:.2e}; "
                         "the decision rule says stop before reading any result")
    return d


def main():
    paths = sorted(glob.glob(str(ABL / "fold_*/context_ablation_fold*.npz")))
    if not paths:
        raise SystemExit(f"no ablation files under {ABL}")

    per_cat = {m: {} for m in MODES}          # mode -> category -> I-AUROC
    per_cat_s = {m: {} for m in MODES}        # mode -> category -> S-AUROC(mean)
    gates, n_obj = [], 0
    for path in paths:
        fold = int(Path(path).stem.replace("context_ablation_fold", ""))
        z = np.load(path, allow_pickle=True)
        gates.append((fold, gate(z, fold)))
        cats, y = z["category"], z["object_label"].astype(int)
        v, il = z["valid"].astype(bool), z["image_labels"].astype(bool)
        n_obj += len(y)
        for m in MODES:
            if f"view_scores_{m}" not in z:
                continue
            s = z[f"view_scores_{m}"]
            obj = np.asarray([row[mask].mean() for row, mask in zip(s, v)])
            for c in sorted(set(cats.tolist())):
                q = cats == c
                per_cat[m][c] = auroc(s[q][v[q]], il[q][v[q]].astype(int))
                per_cat_s[m][c] = auroc(obj[q], y[q])

    print("Correctness gate, real mode against the stored run")
    for fold, d in sorted(gates):
        print(f"  fold {fold}: max|diff| = {d:.2e}")
    cats = sorted(per_cat["real"])
    print(f"\n{len(cats)} categories, {n_obj} objects\n")

    rows = []
    for level, table in (("i_auroc", per_cat), ("s_auroc", per_cat_s)):
        for m in MODES:
            if not table[m]:
                continue
            vals = np.array([table[m][c] for c in cats])
            rows.append({"level": level, "quantity": f"macro {m}", "n": len(cats),
                         "estimate": float(vals.mean()), "ci_low": "", "ci_high": "",
                         "p_value": ""})
            print(f"  {level:<8} macro {m:<5} = {vals.mean():.2f}")
        for a, b, name in (("real", "solo", "delta_context"),
                           ("real", "swap", "delta_identity")):
            if not table[a] or not table[b]:
                continue
            d = np.array([table[a][c] - table[b][c] for c in cats])
            m_, lo, hi, p = ci_t(d)
            rows.append({"level": level, "quantity": name, "n": len(cats),
                         "estimate": m_, "ci_low": lo, "ci_high": hi, "p_value": p})
            print(f"  {level:<8} {name:<15} {m_:+.2f} [{lo:+.2f}, {hi:+.2f}]  p={p:.4f}")
        print()

    out = CSV_DIR / "context_ablation.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["level", "quantity", "n", "estimate",
                                           "ci_low", "ci_high", "p_value"])
        w.writeheader(); w.writerows(rows)
    print("wrote", out.name)

    R = lambda q: next(r for r in rows if r["level"] == "i_auroc" and r["quantity"] == q)
    print("\nDecision, applying the locked rule")
    dc = R("delta_context")
    print(f"  method gap f_mv - f_budget = {METHOD_GAP:+.2f}, half = {METHOD_GAP/2:+.2f}")
    print(f"  delta_context = {dc['estimate']:+.2f} [{dc['ci_low']:+.2f}, {dc['ci_high']:+.2f}]")
    if dc["estimate"] >= METHOD_GAP / 2 and dc["ci_low"] > 0:
        print("  -> outcome 1: cross-view context at inference is the main cause")
    elif abs(dc["estimate"]) < 1.0 and dc["ci_low"] < 0 < dc["ci_high"]:
        print("  -> outcome 2: context at inference is NOT the cause; rename the claim")
    else:
        print("  -> outcome 3: partial, report the number and claim no direction")
    try:
        di = R("delta_identity")
        print(f"  delta_identity = {di['estimate']:+.2f} "
              f"[{di['ci_low']:+.2f}, {di['ci_high']:+.2f}]")
        if abs(di["estimate"]) < 1.0 and di["ci_low"] < 0 < di["ci_high"]:
            print("  -> outcome 4: the specific context does not matter, any context works")
        elif di["estimate"] >= 1.0 and di["ci_low"] > 0:
            print("  -> outcome 5: the object's own context does matter")
        else:
            print("  -> identity: between the two thresholds, report as measured")
    except StopIteration:
        pass


if __name__ == "__main__":
    main()
