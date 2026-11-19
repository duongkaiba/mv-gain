#!/usr/bin/env python3
"""Check every numeric claim the drafts make against the generated tables.

Writing and analysis drifted apart at least once in this project, so the
manuscript is treated as untrusted text and re-checked against the CSVs. Each
check names the section it guards.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

PAPER = Path(__file__).resolve().parents[1]
CSV_DIR = PAPER / "paper_assets/results"
FAIL = []


def load(name, num_skip=()):
    rows = []
    for r in csv.DictReader((CSV_DIR / name).open(encoding="utf-8")):
        rows.append({k: (v if k in num_skip else _f(v)) for k, v in r.items()})
    return rows


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(label)


def close(a, b, tol=0.02):
    return abs(a - b) <= tol


agg = load("aggregation_summary.csv")
G = lambda d, a, f="s_auroc": next(r[f] for r in agg if r["detector"] == d and r["aggregation"] == a)
DETS = ["VisualAD-A", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN"]

print("Section 5.1")
for d, v in (("VisualAD-A", 3.98), ("AnomalyCLIP-VisA", 0.29),
             ("WinCLIP", 0.69), ("Cross-view NN", -7.51)):
    check(f"headroom {d} = {v:+.2f}", close(G(d, "oracle_mean", "delta_vs_mean"), v))
check("oracle max loses on all four detectors",
      all(G(d, "oracle_max", "delta_vs_mean") < 0 and G(d, "oracle_max", "ci_high") < 0
          for d in DETS))
lo = min(-G(d, "oracle_max", "delta_vs_mean") for d in DETS)
hi = max(-G(d, "oracle_max", "delta_vs_mean") for d in DETS)
check("oracle-max loss spans 5.16 to 34.09", close(lo, 5.16) and close(hi, 34.09),
      f"{lo:.2f}..{hi:.2f}")

print("Section 5.2")
check("max <= top2 <= top3 on all four detectors",
      all(G(d, "max") <= G(d, "top2") <= G(d, "top3") for d in DETS))
best = [d for d in DETS if G(d, "mean") == max(G(d, a) for a in ("mean", "max", "top2", "top3", "median"))]
check("mean is best fixed rule on exactly three of four", len(best) == 3,
      f"best on {best}")
check("only exception is VisualAD-A", set(DETS) - set(best) == {"VisualAD-A"})
check("that exception has CI containing zero",
      G("VisualAD-A", "top3", "ci_low") < 0 < G("VisualAD-A", "top3", "ci_high"))
check("no fixed rule beats mean significantly, 16 comparisons",
      not any(G(d, a, "ci_low") > 0 for d in DETS for a in ("max", "top2", "top3", "median")))

print("Section 5.3")
learned = load("learned_aggregation_summary.csv")
L = lambda d, m, f: next(r[f] for r in learned if r["detector"] == d and r["method"] == m)
check("no learned aggregator beats mean, 6 comparisons",
      not any(L(d, m, "ci_low") > 0
              for d in ("VisualAD-A", "VisualAD-Acontinued", "VisualAD-F")
              for m in ("logistic_regression", "gated_L_estimator")))
check("logistic on f_mv = -3.35 and significant",
      close(L("VisualAD-F", "logistic_regression", "delta_vs_mean"), -3.35)
      and L("VisualAD-F", "logistic_regression", "ci_high") < 0)

print("Section 5.4")
cmp_ = load("visualad_paired_comparisons.csv")
C = lambda c, m, f: next(r[f] for r in cmp_ if r["comparison"] == c and r["metric"] == m)
AC = "VisualAD-Acontinued - VisualAD-A"
FA = "VisualAD-F - VisualAD-Acontinued"
check("budget step image +1.04 significant",
      close(C(AC, "i_auroc", "difference"), 1.04) and C(AC, "i_auroc", "ci_low") > 0)
check("budget step object +0.44 not significant",
      close(C(AC, "s_auroc_mean", "difference"), 0.44) and C(AC, "s_auroc_mean", "ci_low") < 0)
check("method step image +3.44 significant",
      close(C(FA, "i_auroc", "difference"), 3.44) and C(FA, "i_auroc", "ci_low") > 0)
check("method step object +2.13 significant",
      close(C(FA, "s_auroc_mean", "difference"), 2.13) and C(FA, "s_auroc_mean", "ci_low") > 0)
ops = load("visualad_operating_points.csv")
O = lambda d, f: next(r[f] for r in ops if r["detector"] == d)
check("gap between f_base and f_mv object level is 2.57",
      close(O("VisualAD-F", "s_auroc_mean") - O("VisualAD-A", "s_auroc_mean"), 2.57))

print("Section 5.5")
kc = load("visualad_k_comparison.csv")
K = {int(r["k"]): r for r in kc}
check("gain at k=5 is +1.80 and significant",
      close(K[5]["difference"], 1.80) and K[5]["ci_low"] > 0)
check("largest gain at k=2, not k=1",
      max(K, key=lambda k: K[k]["difference"]) == 2)
check("k=3 and k=4 CIs contain zero",
      K[3]["ci_low"] < 0 < K[3]["ci_high"] and K[4]["ci_low"] < 0 < K[4]["ci_high"])
check("n per stratum is 28,28,29,30,30",
      [int(K[k]["n_categories"]) for k in range(1, 6)] == [28, 28, 29, 30, 30])
kp = load("k_profile.csv")
cv = sorted((r for r in kp if r["detector"] == "Cross-view NN"), key=lambda r: r["k"])
check("Cross-view NN drops from k=4 to k=5 by 3.17",
      close(cv[3]["s_auroc_mean"] - cv[4]["s_auroc_mean"], 3.17))
check("other three detectors rise from k=4 to k=5",
      all(sorted((r for r in kp if r["detector"] == d), key=lambda r: r["k"])[4]["s_auroc_mean"]
          > sorted((r for r in kp if r["detector"] == d), key=lambda r: r["k"])[3]["s_auroc_mean"]
          for d in ("VisualAD-Acontinued", "WinCLIP", "AnomalyCLIP-VisA")))

print("Section 6")
vs = load("variety_summary.csv")
V = lambda s, m, f: next(r[f] for r in vs if r["subset"] == s and r["metric"] == m)
check("Variety image +3.57 significant",
      close(V("all_160", "i_auroc", "difference"), 3.57) and V("all_160", "i_auroc", "ci_low") > 0)
check("Variety object +0.53 not significant",
      close(V("all_160", "s_auroc_mean", "difference"), 0.53)
      and V("all_160", "s_auroc_mean", "ci_low") < 0)
check("f_mv higher in 126 of 160 at image level",
      int(V("all_160", "i_auroc", "n_categories_F_higher")) == 126)
check("f_mv higher in 79 of 160 at object level",
      int(V("all_160", "s_auroc_mean", "n_categories_F_higher")) == 79)
check("141-category subset gives +0.47",
      close(V("eligible_141", "s_auroc_mean", "difference"), 0.47))
vagg = load("variety_aggregation_summary.csv")
VA = lambda d, a, f: next(r[f] for r in vagg if r["detector"] == d and r["aggregation"] == a)
check("Variety oracle headroom +0.02 with CI containing zero",
      close(VA("VisualAD-Acontinued", "oracle_mean", "delta_vs_mean"), 0.02)
      and VA("VisualAD-Acontinued", "oracle_mean", "ci_low") < 0
      < VA("VisualAD-Acontinued", "oracle_mean", "ci_high"))
check("every fixed rule loses significantly on Variety",
      all(VA("VisualAD-Acontinued", a, "ci_high") < 0 for a in ("max", "top2", "top3", "median")))
mix = load("variety_k_mix.csv")
share = {int(r["k"]): r["variety_share"] for r in mix}
check("Variety k=5 share is 90.6 percent", close(100 * share[5], 90.6, 0.1))
delta = np.array([r["realiad_delta_F_minus_Acont"] for r in sorted(mix, key=lambda r: r["k"])])
vw = np.array([r["variety_share"] for r in sorted(mix, key=lambda r: r["k"])])
check("k-mix reweighting predicts +1.77", close(float(vw @ delta), 1.77, 0.02))
conv = load("variety_conversion.csv")
base = np.array([r["baseline_s_auroc"] for r in conv])
check("72 of 160 categories are at or above 95", int((base >= 95).sum()) == 72)
check("their mean baseline is 98.86", close(base[base >= 95].mean(), 98.86))

cc = load("coupling_checks.csv", num_skip=("quantity", "note"))
Q = lambda q, f: next(r[f] for r in cc if r["quantity"] == q)
check("retracted absorption correlation is +0.64",
      close(Q("corr(aggregation_lift, gain_not_retained)", "observed"), 0.64, 0.01))
check("its permutation null is +0.79, so the observed value sits BELOW the null",
      close(Q("corr(aggregation_lift, gain_not_retained)", "null_mean"), 0.79, 0.01)
      and Q("corr(aggregation_lift, gain_not_retained)", "percentile_of_observed") < 1.0)
check("Table 7.1 correlation survives its own permutation null",
      close(Q("corr(aggregation_lift, oracle_headroom)", "observed"), -0.89, 0.01)
      and abs(Q("corr(aggregation_lift, oracle_headroom)", "null_mean")) < 0.4
      and Q("corr(aggregation_lift, oracle_headroom)", "percentile_of_observed") < 1.0)
sat = load("saturation_permutation.csv")
check("no saturation threshold survives its selection null",
      all(r["p_permutation"] > 0.05 for r in sat))
check("selection alone produces about +1 point at the reported threshold",
      close(next(r["null_mean"] for r in sat if r["threshold"] == 90), 0.97, 0.15))

print("Section 6, Variety baselines")
vbl = load("variety_baselines_summary.csv", num_skip=("detector", "aggregation"))
VB = lambda d, a, f: next(r[f] for r in vbl if r["detector"] == d and r["aggregation"] == a)
FAM = ("WinCLIP", "AnomalyCLIP-VisA", "Cross-view NN")
check("every fixed rule loses significantly on all three baseline families",
      all(VB(d, a, "ci_high") < 0 for d in FAM for a in ("max", "top2", "top3", "median")))
check("oracle headroom within a tenth of a point of zero on all three",
      all(abs(VB(d, "oracle_mean", "delta_vs_mean")) <= 0.10 + 1e-9 for d in FAM),
      " ".join(f"{d}={VB(d,'oracle_mean','delta_vs_mean'):+.2f}" for d in FAM))
check("each of those intervals contains zero",
      all(VB(d, "oracle_mean", "ci_low") < 0 < VB(d, "oracle_mean", "ci_high") for d in FAM))
check("each of those intervals lies within 0.75 points of zero",
      all(max(abs(VB(d, "oracle_mean", "ci_low")), abs(VB(d, "oracle_mean", "ci_high"))) < 0.75
          for d in FAM),
      "max |bound| = %.3f" % max(max(abs(VB(d, "oracle_mean", "ci_low")),
                                    abs(VB(d, "oracle_mean", "ci_high"))) for d in FAM))
check("oracle max loses significantly on all three",
      all(VB(d, "oracle_max", "ci_high") < 0 for d in FAM))
lo = min(-VB(d, "oracle_max", "delta_vs_mean") for d in FAM)
hi = max(-VB(d, "oracle_max", "delta_vs_mean") for d in FAM)
check("oracle-max loss on Variety spans 3.53 to 16.21", close(lo, 3.53) and close(hi, 16.21),
      f"{lo:.2f}..{hi:.2f}")
check("Cross-view NN headroom is no longer significantly negative on Variety",
      VB("Cross-view NN", "oracle_mean", "ci_high") > 0)

print("Section 6, low-visibility subset")
lowk = load("variety_lowk_headroom.csv", num_skip=("detector",))
L = lambda d, f: next(r[f] for r in lowk if r["detector"] == d)
LOWK = {"VisualAD-Acontinued": 1.96, "AnomalyCLIP-VisA": -0.85,
        "WinCLIP": -1.05, "Cross-view NN": 0.33}
for d, v in LOWK.items():
    check(f"low-k headroom {d} = {v:+.2f}", close(L(d, "delta_vs_mean"), v))
check("low-k subset keeps 753 anomalous objects in 66 categories",
      all(L(d, "n_anomalous_objects") == 753 and L(d, "n_categories") == 66 for d in LOWK))
check("every low-k interval contains zero",
      all(L(d, "ci_low") < 0 < L(d, "ci_high") for d in LOWK))
w = [L(d, "ci_high") - L(d, "ci_low") for d in LOWK]
check("low-k intervals are five to thirteen points wide",
      5 <= min(w) < 6 and 12 <= max(w) < 13, f"{min(w):.2f}..{max(w):.2f}")

print("Section 6, corrections of batch 1")
ratios = []
for d_ri, d_va, src in (("VisualAD-A", "VisualAD-Acontinued", VA),
                        ("AnomalyCLIP-VisA", "AnomalyCLIP-VisA", VB),
                        ("WinCLIP", "WinCLIP", VB), ("Cross-view NN", "Cross-view NN", VB)):
    for a in ("max", "top2", "top3", "median"):
        w_ri = G(d_ri, a, "ci_high") - G(d_ri, a, "ci_low")
        w_va = src(d_va, a, "ci_high") - src(d_va, a, "ci_low")
        ratios.append(w_ri / w_va)
ratios.sort()
med = 0.5 * (ratios[7] + ratios[8])
check("Variety fixed-rule intervals are narrower by a median factor of 1.4",
      close(med, 1.4, 0.05) and close(ratios[0], 0.98, 0.05) and close(ratios[-1], 2.20, 0.05),
      f"{ratios[0]:.2f}..{ratios[-1]:.2f} median {med:.2f}")
check("lift-headroom correlation rounds to -0.89",
      close(next(r["observed"] for r in load("coupling_checks.csv", num_skip=("quantity", "note"))
                 if "oracle_headroom" in r["quantity"]), -0.8949, 0.001))

print("Section 5.3, extra aggregator family")
ex = load("extra_aggregators.csv", num_skip=("group", "detector", "rule", "hyperparameter"))
X = lambda d, r, f: next(v[f] for v in ex if v["detector"] == d and v["rule"] == r)
check("the locked family has exactly 23 comparisons", len(ex) == 23, str(len(ex)))
agg_rows = [r for r in agg if r["detector"] in DETS
            and r["aggregation"] in ("max", "top2", "top3", "median")]
lrn = load("learned_aggregation_summary.csv", num_skip=("detector", "method", "source"))
lrn_rows = [r for r in lrn if r["method"] in
            ("logistic_regression", "gated_L_estimator")]
check("the family of 45 is 16 fixed, 6 learned and 23 new, each counted from its CSV",
      len(agg_rows) + len(lrn_rows) + len(ex) == 45,
      f"{len(agg_rows)} + {len(lrn_rows)} + {len(ex)}")
nominal = [v for v in ex if v["ci_low"] > 0]
check("exactly one new rule clears zero nominally", len(nominal) == 1,
      nominal[0]["detector"] + " / " + nominal[0]["rule"] if nominal else "none")
check("that rule is log-sum-exp on f_base at +0.93 [+0.21, +1.65]",
      nominal and nominal[0]["rule"] == "log-sum-exp"
      and nominal[0]["detector"] == "VisualAD-A"
      and close(nominal[0]["delta_vs_mean"], 0.93) and close(nominal[0]["ci_low"], 0.21)
      and close(nominal[0]["ci_high"], 1.65))
check("its Bonferroni interval is [-0.25, +2.11] and contains zero",
      close(X("VisualAD-A", "log-sum-exp", "bonf_ci_low"), -0.25)
      and close(X("VisualAD-A", "log-sum-exp", "bonf_ci_high"), 2.11))
check("no new rule survives Bonferroni over the family",
      all(v["bonf_ci_low"] < 0 for v in ex))
for d, v in (("f_base", -0.41), ("f_budget", -0.47), ("f_mv", -1.84)):
    check(f"camera-order logistic on {d} = {v:+.2f}",
          close(X(d, "logistic, camera order", "delta_vs_mean"), v))

print("Section 6.2, visibility reweighting")
km = load("kmix_reweight.csv", num_skip=("detector",))
K = lambda d, f: next(v[f] for v in km if v["detector"] == d)
for d, obs, mix in (("VisualAD-A", 3.98, 0.13), ("VisualAD-Acontinued", 4.22, 0.14),
                    ("Cross-view NN", -7.51, -0.41)):
    check(f"{d}: headroom {obs:+.2f} falls to {mix:+.2f} at the Variety k mix",
          close(K(d, "headroom_observed"), obs) and close(K(d, "headroom_variety_mix"), mix))
check("Cross-view NN reweighted interval contains zero",
      K("Cross-view NN", "mix_ci_low") < 0 < K("Cross-view NN", "mix_ci_high"))

print("Section 7.1, identifiability")
idf = load("identifiability.csv", num_skip=("detector",))
I = lambda d, f: next(v[f] for v in idf if v["detector"] == d)
DET5 = ["VisualAD-A", "VisualAD-Acontinued", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN"]
check("visibility AUROC on f_base is 75.5", close(I("VisualAD-A", "visibility_auroc"), 75.5, 0.1))
lo = min(I(d, "visibility_auroc") for d in DET5)
hi = max(I(d, "visibility_auroc") for d in DET5)
check("visibility AUROC spans 57.1 to 76.6", close(lo, 57.1, 0.1) and close(hi, 76.6, 0.1),
      f"{lo:.1f}..{hi:.1f}")
slo = min(I(d, "ceiling_sorted_vs_mean") for d in DET5)
shi = max(I(d, "ceiling_sorted_vs_mean") for d in DET5)
clo = min(I(d, "ceiling_camera_vs_mean") for d in DET5)
chi = max(I(d, "ceiling_camera_vs_mean") for d in DET5)
check("within-category ceiling spans +1.66 to +7.88 sorted",
      close(slo, 1.66) and close(shi, 7.88), f"{slo:+.2f}..{shi:+.2f}")
check("within-category ceiling spans +2.41 to +9.54 in camera order",
      close(clo, 2.41) and close(chi, 9.54), f"{clo:+.2f}..{chi:+.2f}")
check("every ceiling interval excludes zero",
      all(I(d, "sorted_ci_low") > 0 and I(d, "camera_ci_low") > 0 for d in DET5))

print("Section 4.5 and 5.5, clustering, multiplicity and trend")
ic = load("inference_checks.csv", num_skip=("check", "quantity"))
Q = lambda q, f: next(v[f] for v in ic if v["quantity"] == q)
check("ICC is 0.089 at the object level and 0.099 at the image level",
      close(Q("f_mv - f_budget, S-AUROC", "icc"), 0.089, 0.002)
      and close(Q("f_mv - f_budget, I-AUROC", "icc"), 0.099, 0.002))
check("design effects are 1.44 and 1.50",
      close(Q("f_mv - f_budget, S-AUROC", "design_effect"), 1.44, 0.01)
      and close(Q("f_mv - f_budget, I-AUROC", "design_effect"), 1.50, 0.01))
check("adjusted intervals still exclude zero",
      Q("f_mv - f_budget, S-AUROC", "adj_ci_low") > 0
      and Q("f_mv - f_budget, I-AUROC", "adj_ci_low") > 0,
      f"{Q('f_mv - f_budget, S-AUROC', 'adj_ci_low'):+.2f} and "
      f"{Q('f_mv - f_budget, I-AUROC', 'adj_ci_low'):+.2f}")
check("oracle headroom needs no widening, ICC is negative",
      Q("oracle headroom, f_base", "icc") < 0)
check("visibility trend slope is -0.28 with an interval containing zero",
      close(Q("trend slope of f_mv - f_budget on k", "estimate"), -0.276, 0.005)
      and Q("trend slope of f_mv - f_budget on k", "ci_low") < 0
      < Q("trend slope of f_mv - f_budget on k", "ci_high"))
check("contrast k<=2 minus k=5 is +1.07 with an interval containing zero",
      close(Q("contrast k<=2 minus k=5", "estimate"), 1.07, 0.01)
      and Q("contrast k<=2 minus k=5", "ci_low") < 0 < Q("contrast k<=2 minus k=5", "ci_high"))
check("largest Bonferroni upper limit over 16 fixed rules is +2.16",
      close(Q("Bonferroni upper limit, 16 fixed rules", "estimate"), 2.16))
check("Variety near-equivalence holds at any margin from 0.92 points",
      close(Q("smallest equivalence margin, Variety oracle", "estimate"), 0.92))

print("Section 5, inference-time context ablation")
ctx = load("context_ablation.csv", num_skip=("level", "quantity"))
C = lambda lv, q, f: next(r[f] for r in ctx if r["level"] == lv and r["quantity"] == q)
for q, v in (("macro real", 83.33), ("macro swap", 78.95), ("macro solo", 77.54)):
    check(f"I-AUROC {q} = {v}", close(C("i_auroc", q, "estimate"), v))
check("correct minus swapped is +4.38 [+2.38, +6.37] at the image level",
      close(C("i_auroc", "delta_identity", "estimate"), 4.38)
      and close(C("i_auroc", "delta_identity", "ci_low"), 2.38)
      and close(C("i_auroc", "delta_identity", "ci_high"), 6.37))
check("correct minus no context is +5.79 at the image level",
      close(C("i_auroc", "delta_context", "estimate"), 5.79))
check("the object-level swapped contrast is +0.86 and contains zero",
      close(C("s_auroc", "delta_identity", "estimate"), 0.86)
      and C("s_auroc", "delta_identity", "ci_low") < 0 < C("s_auroc", "delta_identity", "ci_high"))
check("the swapped contrast is the smaller and cleaner of the two",
      C("i_auroc", "delta_identity", "estimate") < C("i_auroc", "delta_context", "estimate"))

print("Section 5 and 8, readout sensitivity")
ro = load("readout_sensitivity.csv", num_skip=("detector",))
R = lambda d: sorted([r for r in ro if r["detector"] == d], key=lambda r: r["ratio"])
check("five readouts for each of the four families",
      all(len(R(d)) == 5 for d in ("VisualAD-A", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN")))
check("VisualAD headroom is positive and significant at every readout",
      all(r["headroom"] > 0 and r["ci_low"] > 0 for r in R("VisualAD-A")))
check("Cross-view NN point estimates are negative at every readout",
      all(r["headroom"] < 0 for r in R("Cross-view NN")))
lo = min(r["headroom"] for r in R("Cross-view NN"))
hi = max(r["headroom"] for r in R("Cross-view NN"))
check("Cross-view NN ranges from -1.49 to -16.10", close(hi, -1.49) and close(lo, -16.10),
      f"{lo:.2f}..{hi:.2f}")
base = {d: next(r["headroom"] for r in R(d) if abs(r["ratio"] - 0.01) < 1e-9)
        for d in ("VisualAD-A", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN")}
order0 = sorted(base, key=base.get)
check("the ordering of the four families is unchanged at every readout",
      all(sorted(base, key=lambda d: next(r["headroom"] for r in R(d)
          if abs(r["ratio"] - x) < 1e-12)) == order0
          for x in sorted({r["ratio"] for r in ro})))
check("neither AnomalyCLIP nor WinCLIP is significant at any readout",
      all(r["ci_low"] < 0 < r["ci_high"]
          for d in ("AnomalyCLIP-VisA", "WinCLIP") for r in R(d)))

print("Section 7")
role = load("discussion_aggregation_role.csv", num_skip=("operating_point", "dataset"))
x = np.array([r["aggregation_lift"] for r in role])
y = np.array([r["oracle_headroom"] for r in role])
check("eight operating points in Table 7.1", len(role) == 8)
check("lift vs headroom r = -0.89", close(np.corrcoef(x, y)[0, 1], -0.89, 0.01))
check("Real-IAD aggregation lift is +3.40 for f_budget",
      close(next(r["aggregation_lift"] for r in role
                 if r["operating_point"] == "VisualAD-Acontinued" and r["dataset"] == "Real-IAD"), 3.40))
check("Variety aggregation lift is +8.53 for f_budget",
      close(next(r["aggregation_lift"] for r in role
                 if r["operating_point"] == "VisualAD-Acontinued" and r["dataset"] == "Variety"), 8.53))

print("Appendix A")
sup = load("supplementary_metrics_summary.csv", num_skip=("comparison", "metric"))
S = lambda c, m, f: next(r[f] for r in sup if r["comparison"] == c and r["metric"] == m)
check("S-AP method step +2.27 significant",
      close(S("f_mv - f_budget", "s_ap", "difference"), 2.27)
      and S("f_mv - f_budget", "s_ap", "ci_low") > 0)
check("S-F1max method step +2.41 significant",
      close(S("f_mv - f_budget", "s_f1max", "difference"), 2.41)
      and S("f_mv - f_budget", "s_f1max", "ci_low") > 0)
check("budget step IS significant under S-AP",
      S("f_budget - f_base", "s_ap", "ci_low") > 0)
check("budget step is NOT significant under S-AUROC or S-F1max",
      S("f_budget - f_base", "s_auroc", "ci_low") < 0
      and S("f_budget - f_base", "s_f1max", "ci_low") < 0)

print()
print(f"{len(FAIL)} failed" if FAIL else "all claims verified")
for f in FAIL:
    print("  FAILED:", f)
raise SystemExit(1 if FAIL else 0)
