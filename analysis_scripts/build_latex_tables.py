#!/usr/bin/env python3
"""Emit every data-driven LaTeX table from the generated CSV tables.

Numbers in the manuscript must never be typed by hand. Each table below is
written from the same CSV that verify_claims.py checks, so a change in the
experiments propagates to the paper without a transcription step.

Outputs go to tex/tables/*.tex and are pulled in from main_review.tex and supplementary.tex with \\input.
"""
from __future__ import annotations

import csv
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
CSV_DIR = PAPER / "paper_assets/results"
OUT = PAPER / "tex/tables"

NAME = {"VisualAD-A": r"VisualAD $f_{\mathrm{base}}$",
        "VisualAD-Acontinued": r"VisualAD $f_{\mathrm{budget}}$",
        "VisualAD-F": r"VisualAD $f_{\mathrm{mv}}$",
        "WinCLIP": "WinCLIP", "AnomalyCLIP-VisA": "AnomalyCLIP-VisA",
        "Cross-view NN": "Cross-view NN"}
ORDER = ["VisualAD-A", "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN"]


def load(name, text=()):
    rows = []
    for r in csv.DictReader((CSV_DIR / name).open(encoding="utf-8")):
        rows.append({k: (v if k in text or v == "" else float(v)) for k, v in r.items()})
    return rows


def ci(row, key="delta_vs_mean", lo="ci_low", hi="ci_high", star=True):
    """Signed effect with its interval, starred when the interval clears zero.

    Everything stays inside one math group so that the signs typeset as minus
    rather than hyphen, and so that no two math groups end up adjacent.
    """
    mark = r"^{\ast}" if star and (row[lo] > 0 or row[hi] < 0) else ""
    return (f"${row[key]:+.2f}{mark}$ "
            f"[${row[lo]:+.2f}$,\\,${row[hi]:+.2f}$]")


def write(name, caption, label, header, body, note=None, star_note=True, cols=None,
          wide=True, size=None):
    """wide=True spans both columns, which every table carrying an interval needs.

    Type size is chosen from the column count so that the widest tables still
    fit the text block without an overfull box.
    """
    cols = cols or "l" + "r" * (header.count("&"))
    if size is None:
        size = r"\footnotesize" if header.count("&") >= 5 else r"\small"
    env = "table*" if wide else "table"
    lines = [rf"\begin{{{env}}}[pos=t]", r"\centering", size,
             rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             rf"\begin{{tabular}}{{{cols}}}", r"\toprule", header + r" \\",
             r"\midrule", *[r + r" \\" for r in body], r"\bottomrule",
             r"\end{tabular}"]
    tail = []
    if star_note:
        tail.append(r"$^{\ast}$ the 95\% interval excludes zero.")
    if note:
        tail.append(note)
    if tail:
        # \par is required: without it the note runs alongside the tabular
        # instead of starting a new line under it.
        # A minipage keeps the note left-aligned inside the centred float and
        # stops it from being typeset as a centred fragment.
        lines.append(r"\par\smallskip")
        lines.append(r"\begin{minipage}{\linewidth}\footnotesize\raggedright")
        lines.append(" ".join(tail))
        lines.append(r"\end{minipage}")
    lines.append(rf"\end{{{env}}}")
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    agg = load("aggregation_summary.csv", text=("detector", "aggregation"))
    G = lambda d, a: next(r for r in agg if r["detector"] == d and r["aggregation"] == a)
    cat = load("category_metrics.csv", text=("detector", "category"))
    iauroc = {d: sum(r["i_auroc"] for r in cat if r["detector"] == d)
                 / sum(1 for r in cat if r["detector"] == d) for d in NAME}

    # ---- oracle references -------------------------------------------------
    write("tab_oracle.tex",
          "Oracle references against mean aggregation on Real-IAD, 30 categories, "
          "five folds. The headroom column is the paired difference between oracle "
          "mean and mean.",
          "tab:oracle",
          r"Detector & I-AUROC & Mean & Oracle mean & Headroom [95\% CI] & Oracle max & "
          r"Oracle max $-$ mean [95\% CI]",
          [f"{NAME[d]} & {iauroc[d]:.2f} & {G(d,'mean')['s_auroc']:.2f} & "
           f"{G(d,'oracle_mean')['s_auroc']:.2f} & {ci(G(d,'oracle_mean'))} & "
           f"{G(d,'oracle_max')['s_auroc']:.2f} & {ci(G(d,'oracle_max'))}" for d in ORDER])

    # ---- fixed rules -------------------------------------------------------
    write("tab_fixed_rules.tex",
          "Fixed aggregation rules against mean on Real-IAD. The mean column is "
          "absolute S-AUROC; the remaining columns are paired differences, so a "
          "negative entry is worse than mean.",
          "tab:fixed",
          r"Detector & Mean & Max & Top-2 & Top-3 & Median",
          [f"{NAME[d]} & \\textbf{{{G(d,'mean')['s_auroc']:.2f}}} & " +
           " & ".join(f"${G(d,a)['delta_vs_mean']:+.2f}" +
                      (r"^{\ast}$" if G(d, a)["ci_low"] > 0 or G(d, a)["ci_high"] < 0 else "$")
                      for a in ("max", "top2", "top3", "median")) for d in ORDER],
          wide=False)

    # ---- one aggregation table replacing the separate oracle/fixed pair ----
    # Sections 5.1 and 5.2 share their row index, so a single table carries both
    # and saves the reader a cross-reference.
    write("tab_aggregation.tex",
          "Aggregation on Real-IAD, 30 categories, five folds. The I-AUROC and mean "
          "columns are absolute values; every other column is a paired S-AUROC "
          "difference against the mean, so a negative entry is worse than averaging. The two oracle columns "
          "are privileged references that read the ground-truth masks and are not "
          "deployable aggregators.",
          "tab:aggregation",
          r"Detector & I-AUROC & Mean & Max & Top-2 & Top-3 & Median & "
          r"Oracle mean & Oracle max",
          [f"{NAME[d]} & {iauroc[d]:.2f} & \\textbf{{{G(d,'mean')['s_auroc']:.2f}}} & " +
           " & ".join(f"${G(d,a)['delta_vs_mean']:+.2f}" +
                      (r"^{\ast}$" if G(d, a)["ci_low"] > 0 or G(d, a)["ci_high"] < 0 else "$")
                      for a in ("max", "top2", "top3", "median", "oracle_mean", "oracle_max"))
           for d in ORDER])

    # ---- learned aggregators ----------------------------------------------
    learned = load("learned_aggregation_summary.csv", text=("detector", "method", "source"))
    L = lambda d, m: next(r for r in learned if r["detector"] == d and r["method"] == m)
    write("tab_learned.tex",
          "Learned aggregators against mean, across the three upstream operating "
          "points of the VisualAD family. Top-2 is retained as a fixed-rule "
          "reference.",
          "tab:learned",
          r"Upstream scorer & Mean & Top-2 [95\% CI] & Logistic regression [95\% CI] & "
          r"Gated L-estimator [95\% CI]",
          [f"{NAME[d]} & {L(d,'mean')['s_auroc']:.2f} & {ci(L(d,'top2'))} & "
           f"{ci(L(d,'logistic_regression'))} & {ci(L(d,'gated_L_estimator'))}"
           for d in ("VisualAD-A", "VisualAD-Acontinued", "VisualAD-F")])

    # ---- upstream ladder ---------------------------------------------------
    cmp_ = load("visualad_paired_comparisons.csv", text=("comparison", "metric"))
    C = lambda c, m: next(r for r in cmp_ if r["comparison"] == c and r["metric"] == m)
    pretty = {"VisualAD-Acontinued - VisualAD-A":
              r"$f_{\mathrm{budget}} - f_{\mathrm{base}}$",
              "VisualAD-F - VisualAD-Acontinued":
              r"$f_{\mathrm{mv}} - f_{\mathrm{budget}}$"}
    write("tab_upstream.tex",
          "Paired differences between consecutive upstream operating points, on 30 "
          "categories. I-AUROC scores each image independently; S-AUROC scores the "
          "object after mean aggregation.",
          "tab:upstream",
          r"Comparison & Metric & Difference [95\% CI] & $p$",
          [f"{pretty[c]} & {'I-AUROC' if m=='i_auroc' else 'S-AUROC'} & "
           f"{ci(C(c,m), 'difference', 'ci_low', 'ci_high')} & {C(c,m)['p_value']:.2g}"
           for c in pretty for m in ("i_auroc", "s_auroc_mean")], cols="llrr")

    # ---- defect visibility -------------------------------------------------
    kc = load("visualad_k_comparison.csv")
    # Not \input anywhere: the supplementary version tab_kcompare_supp.tex is the
    # one typeset. Kept for reference with its own label so the two never collide.
    write("tab_k_compare.tex",
          "The upstream operating point against its equal-budget control, stratified "
          "by the number of defect-visible views $k$. A category enters a stratum "
          "only when AUROC is defined there, so $n$ varies.",
          "tab:kcompare_unused",
          r"$k$ & $n$ & $f_{\mathrm{budget}}$ & $f_{\mathrm{mv}}$ & Difference [95\% CI] & $p$",
          [f"{int(r['k'])} & {int(r['n_categories'])} & {r['Acontinued']:.2f} & "
           f"{r['F']:.2f} & {ci(r,'difference','ci_low','ci_high')} & {r['p_value']:.3f}"
           for r in sorted(kc, key=lambda r: r["k"])])

    kp = load("k_profile.csv", text=("detector",))
    K = lambda d, k: next(r for r in kp if r["detector"] == d and r["k"] == k)
    cols = ["VisualAD-Acontinued", "AnomalyCLIP-VisA", "Cross-view NN", "WinCLIP"]
    write("tab_k_profile.tex",
          "Macro S-AUROC by $k$ across the four detector families, under mean "
          "aggregation.",
          "tab:kprofile",
          r"$k$ & $n$ & " + " & ".join(NAME[d] for d in cols),
          [f"{k} & {int(K(cols[0],k)['n_categories'])} & " +
           " & ".join(f"{K(d,k)['s_auroc_mean']:.2f}" for d in cols) for k in range(1, 6)],
          star_note=False, wide=False, size=r"\footnotesize")

    # ---- cross dataset -----------------------------------------------------
    vagg = load("variety_aggregation_summary.csv", text=("detector", "aggregation"))
    VA = lambda a: next(r for r in vagg if r["detector"] == "VisualAD-Acontinued"
                        and r["aggregation"] == a)
    labels = {"max": "Max", "top2": "Top-2", "top3": "Top-3", "median": "Median",
              "oracle_mean": "Oracle mean"}
    body = [rf"Mean (reference) & {G('VisualAD-Acontinued','mean')['s_auroc']:.2f} & "
            rf"{VA('mean')['s_auroc']:.2f}"]
    body += [f"{labels[a]} & {ci(G('VisualAD-Acontinued',a))} & {ci(VA(a))}" for a in labels]
    write("tab_cross_dataset.tex",
          "Aggregation rules against mean on the equal-budget control, Real-IAD "
          "versus 160 unseen Real-IAD Variety categories. The oracle row is the "
          "tightest measurement in the study.",
          "tab:crossdata",
          r"Rule & Real-IAD (30 cat.) & Variety (160 cat.)", body)

    # ---- the headline cross-dataset table, all four detector families ------
    vb = load("variety_baselines_summary.csv", text=("detector", "aggregation"))
    VB = lambda d, a: next(r for r in vb if r["detector"] == d and r["aggregation"] == a)
    labels = {"max": "Max", "top2": "Top-2", "top3": "Top-3", "median": "Median",
              "oracle_mean": "Oracle mean", "oracle_max": "Oracle max"}
    fams = [("VisualAD $f_{\\mathrm{budget}}$", lambda a: VA(a)),
            ("AnomalyCLIP-VisA", lambda a: VB("AnomalyCLIP-VisA", a)),
            ("WinCLIP", lambda a: VB("WinCLIP", a)),
            ("Cross-view NN", lambda a: VB("Cross-view NN", a))]
    body = [" & ".join(["Mean (reference)"] + [f"{g('mean')['s_auroc']:.2f}" for _, g in fams])]
    body += [" & ".join([labels[a]] + [ci(g(a)) for _, g in fams]) for a in labels]
    write("tab_variety_all.tex",
          "Aggregation rules against mean on 160 unseen Real-IAD Variety categories, "
          "across all four detector families scored on an identical set of objects. "
          "The mean row is absolute S-AUROC; every other row is a paired difference, "
          "so a negative entry is worse than averaging.",
          "tab:varietyall",
          "Rule & " + " & ".join(n for n, _ in fams), body)

    vs = load("variety_summary.csv", text=("subset", "metric"))
    write("tab_transfer.tex",
          "The upstream operating point against its equal-budget control on both "
          "datasets and at both evaluation levels. The last column counts categories "
          "in which $f_{\\mathrm{mv}}$ scores higher.",
          "tab:transfer",
          r"Dataset & Level & $f_{\mathrm{budget}}$ & $f_{\mathrm{mv}}$ & "
          r"Difference [95\% CI] & $p$ & Higher in",
          [f"{d} & {'Image' if r['metric']=='i_auroc' else 'Object'} & "
           f"{r['Acontinued']:.2f} & {r['F']:.2f} & "
           f"{ci(r,'difference','ci_low','ci_high')} & {r['p_value']:.2g} & "
           f"{int(r['n_categories_F_higher'])}/{int(r['n_categories'])}"
           for d, sub in (("Variety, 160 cat.", "all_160"), ("Variety, 141 cat.", "eligible_141"))
           for r in vs if r["subset"] == sub], cols="llrrrrr")

    sat = load("saturation_permutation.csv")
    write("tab_saturation.tex",
          "Threshold sweep for the saturation explanation, with the permutation null "
          "that the selection itself induces. Selecting categories by their baseline "
          "and then measuring a change from that same baseline produces a positive "
          "difference even when the two variants are equivalent.",
          "tab:saturation",
          r"Category set & $n$ & Observed & Null from selection & $p$ (permutation)",
          [f"Control $<$ {int(r['threshold'])} & {int(r['n_categories'])} & "
           f"${r['observed']:+.2f}$ & ${r['null_mean']:+.2f} \\pm {r['null_sd']:.2f}$ & "
           f"{r['p_permutation']:.2f}" for r in sat], star_note=False)

    # ---- discussion synthesis ---------------------------------------------
    role = load("discussion_aggregation_role.csv", text=("operating_point", "dataset"))
    write("tab_role.tex",
          "How much mean aggregation adds over the image level, against how much "
          "oracle-mean headroom remains, across eight operating points. Rows are "
          "ordered by aggregation lift.",
          "tab:role",
          r"Operating point & Dataset & I-AUROC & S-AUROC & Aggregation lift & "
          r"Headroom left",
          [f"{NAME[r['operating_point']]} & {r['dataset']} & {r['i_auroc']:.2f} & "
           f"{r['s_auroc']:.2f} & ${r['aggregation_lift']:+.2f}$ & "
           f"${r['oracle_headroom']:+.2f}$"
           for r in sorted(role, key=lambda r: r["aggregation_lift"])],
          star_note=False, cols="llrrrr")

    # ---- appendix ----------------------------------------------------------
    sup = load("supplementary_metrics_summary.csv", text=("comparison", "metric"))
    mlabel = {"s_auroc": "S-AUROC", "s_ap": "S-AP", "s_f1max": "S-F1max"}
    clabel = {"f_budget - f_base": r"$f_{\mathrm{budget}} - f_{\mathrm{base}}$",
              "f_mv - f_budget": r"$f_{\mathrm{mv}} - f_{\mathrm{budget}}$"}
    write("tab_supplementary_metrics.tex",
          "The central comparison recomputed under two further object-level metrics, "
          "from the same stored object scores.",
          "tab:supmetrics",
          r"Comparison & Metric & Left & Right & Difference [95\% CI] & $p$ & Higher in",
          [f"{clabel[r['comparison']]} & {mlabel[r['metric']]} & {r['left']:.2f} & "
           f"{r['right']:.2f} & {ci(r,'difference','ci_low','ci_high')} & "
           f"{r['p_value']:.2g} & {int(r['n_right_higher'])}/30" for r in sup],
          cols="llrrrrr")

    cc = load("coupling_checks.csv", text=("quantity", "note"))
    write("tab_coupling.tex",
          "Permutation nulls for three derived quantities. The null keeps the "
          "algebraic structure of each quantity and destroys only the relationship "
          "under test.",
          "tab:coupling",
          r"Quantity & Observed & Null mean & Null 95\% & Percentile of observed",
          [f"\\texttt{{{r['quantity'].replace('_',chr(92)+'_')}}} & "
           f"${r['observed']:+.2f}$ & ${r['null_mean']:+.2f}$ & "
           f"[${r['null_lo']:+.2f}$, ${r['null_hi']:+.2f}$] & "
           f"{r['percentile_of_observed']:.1f}\\%" for r in cc], star_note=False)

    print(f"\n{len(list(OUT.glob('*.tex')))} tables in {OUT}")

    # ---- extra score-level fusion rules (locked family of 23) --------------
    ex = load("extra_aggregators.csv", text=("group", "detector", "rule", "hyperparameter"))
    A = lambda d, r: next(x for x in ex if x["detector"] == d and x["rule"] == r)
    RULE_LABEL = [("power mean", "Power mean"), ("log-sum-exp", "Log-sum-exp"),
                  ("product", "Product"), ("noisy-OR", "Noisy-OR"),
                  ("per-camera z-score", "Per-camera $z$-score")]
    write("tab_extra_rules.tex",
          "Five further score-level fusion rules against the mean, S-AUROC, 30 "
          "paired categories per cell. The rules, the hyperparameter grids and the "
          "decision threshold were fixed in writing before the runs. Hyperparameters "
          "are chosen on the four training folds only.",
          "tab:extrarules",
          r"Rule & " + " & ".join(NAME[d] for d in ORDER),
          [f"{lab} & " + " & ".join(ci(A(d, key)) for d in ORDER)
           for key, lab in RULE_LABEL],
          note=("Log-sum-exp on VisualAD $f_{\\mathrm{base}}$ is the one cell of the "
                "23 whose nominal interval clears zero; its Bonferroni interval over "
                "the family of 23 is "
                f"[${A('VisualAD-A','log-sum-exp')['bonf_ci_low']:+.2f}$,\\,"
                f"${A('VisualAD-A','log-sum-exp')['bonf_ci_high']:+.2f}$]."))

    # ---- visibility reweighting -------------------------------------------
    km = load("kmix_reweight.csv", text=("detector",))
    K = lambda d: next(x for x in km if x["detector"] == d)
    write("tab_kmix.tex",
          "Oracle headroom on Real-IAD before and after reweighting its anomalous "
          "objects to the Variety visibility mix. Category remains the sampling unit; "
          "weights match the target $k$ distribution inside each category.",
          "tab:kmix",
          r"Detector & Headroom, Real-IAD as observed & Headroom at the Variety $k$ mix",
          [f"{NAME[d]} & {ci(K(d), 'headroom_observed', 'obs_ci_low', 'obs_ci_high')} & "
           f"{ci(K(d), 'headroom_variety_mix', 'mix_ci_low', 'mix_ci_high')}"
           for d in ("VisualAD-A", "VisualAD-Acontinued", "AnomalyCLIP-VisA",
                     "WinCLIP", "Cross-view NN")])

    # ---- identifiability ----------------------------------------------------
    idf = load("identifiability.csv", text=("detector",))
    D = lambda d: next(x for x in idf if x["detector"] == d)
    write("tab_identifiability.tex",
          "Is the visibility information present in the five scalars? Left: how well "
          "a single view score separates views that see the defect from views that do "
          "not, inside anomalous objects. Right: a logistic regression fitted and "
          "evaluated inside the same category by two-fold cross-validation, against "
          "the mean. The right-hand columns are a reference ceiling, not a valid "
          "zero-shot aggregator: they read labels of the category they score.",
          "tab:identifiability",
          r"Detector & Visibility AUROC [95\% CI] & Ceiling, sorted scores & "
          r"Ceiling, camera order",
          [f"{NAME[d]} & "
           f"{D(d)['visibility_auroc']:.1f} [${D(d)['vis_ci_low']:.1f}$,\\,"
           f"${D(d)['vis_ci_high']:.1f}$] & "
           f"{ci(D(d), 'ceiling_sorted_vs_mean', 'sorted_ci_low', 'sorted_ci_high')} & "
           f"{ci(D(d), 'ceiling_camera_vs_mean', 'camera_ci_low', 'camera_ci_high')}"
           for d in ("VisualAD-A", "VisualAD-Acontinued", "VisualAD-F",
                     "AnomalyCLIP-VisA", "WinCLIP", "Cross-view NN")])

    # ---- post-hoc temperature sensitivity of log-sum-exp --------------------
    ls = load("lse_sensitivity.csv", text=("detector", "grid"))
    LS = lambda d, g, tau: next(x for x in ls if x["detector"] == d
                                and x["grid"] == g and abs(x["tau"] - tau) < 1e-9)
    LSNAME = {"f_base": r"VisualAD $f_{\mathrm{base}}$",
              "f_budget": r"VisualAD $f_{\mathrm{budget}}$",
              "f_mv": r"VisualAD $f_{\mathrm{mv}}$",
              "AnomalyCLIP-VisA": "AnomalyCLIP-VisA", "WinCLIP": "WinCLIP",
              "Cross-view NN": "Cross-view NN"}
    TAUS = (0.25, 0.5, 1.0, 2.0, 4.0)
    write("tab_lse_sensitivity.tex",
          "\\emph{Post-hoc.} Log-sum-exp pooling against the mean at a fixed "
          "temperature, S-AUROC over 30 paired categories. The temperature is given "
          "in units of the within-category standard deviation of the view scores, so "
          "that one grid means the same thing for every family. A bullet marks a "
          "cell whose Bonferroni interval over the family of 23 rules excludes zero. "
          "This grid was not part of the locked family; see the "
          "learned-aggregation results of the manuscript.",
          "tab:lsesens",
          r"Detector & " + " & ".join(rf"$\tau={t:g}\sigma$" for t in TAUS),
          [f"{LSNAME[d]} & " + " & ".join(
              "$" + (r"\bullet\," if LS(d, "scaled", t)["beats_mean_bonferroni"] else "")
              + f"{LS(d, 'scaled', t)['delta_vs_mean']:+.2f}$" for t in TAUS)
           for d in LSNAME],
          note="The same grid in raw score units is in the released results file.",
          star_note=False)

    # ---- clustering and multiplicity ---------------------------------------
    CLUSTER_LABEL = {
        "f_mv - f_budget, S-AUROC": r"$f_{\mathrm{mv}} - f_{\mathrm{budget}}$, S-AUROC",
        "f_mv - f_budget, I-AUROC": r"$f_{\mathrm{mv}} - f_{\mathrm{budget}}$, I-AUROC",
        "oracle headroom, f_base": r"Oracle headroom, $f_{\mathrm{base}}$",
    }
    inf = load("inference_checks.csv", text=("check", "quantity"))
    cl = [r for r in inf if r["check"] == "clustering"]
    write("tab_clustering.tex",
          "Sensitivity of the three central comparisons to the fact that six "
          "categories share each fold's checkpoint. ICC is the one-way "
          "intra-cluster correlation with folds as clusters; the adjusted interval "
          "is widened by the square root of the design effect.",
          "tab:clustering",
          r"Comparison & Estimate [95\% CI] & ICC & Design effect & Adjusted interval",
          [f"{CLUSTER_LABEL[r['quantity']]} & {ci(r, 'estimate', 'ci_low', 'ci_high')} & "
           f"${r['icc']:+.3f}$ & ${r['design_effect']:.2f}$ & "
           f"[${r['adj_ci_low']:+.2f}$,\\,${r['adj_ci_high']:+.2f}$]"
           for r in cl],
          star_note=False)

    # ---- inference-time context ablation ---------------------------------
    context = load("context_ablation.csv", text=("level", "quantity"))
    CT = lambda level, quantity: next(
        r for r in context if r["level"] == level and r["quantity"] == quantity
    )
    modes = [("real", "Correct object context"),
             ("swap", "Context from another normal object"),
             ("solo", "No cross-view context ($V=1$)")]
    body = []
    for key, label in modes:
        body.append(
            f"{label} & {CT('i_auroc', 'macro ' + key)['estimate']:.2f} & "
            f"{CT('s_auroc', 'macro ' + key)['estimate']:.2f}"
        )
    for quantity, label in (("delta_identity", r"Correct $-$ swapped context"),
                            ("delta_context", r"Correct $-$ no context")):
        ri, rs = CT("i_auroc", quantity), CT("s_auroc", quantity)
        body.append(
            f"{label} & {ci(ri, 'estimate', 'ci_low', 'ci_high')} & "
            f"{ci(rs, 'estimate', 'ci_low', 'ci_high')}"
        )
    write("tab_context_ablation.tex",
          "Inference-time context ablation for $f_{\\mathrm{mv}}$ on 6,000 "
          "objects from 30 Real-IAD categories. The first three rows are macro "
          "AUROC; the final two are category-paired differences with 95\\% "
          "intervals. Mean aggregation is used for S-AUROC.",
          "tab:context",
          r"Condition or contrast & I-AUROC & S-AUROC", body,
          wide=False, cols="lrr")

    # ---- sensitivity to anomaly-map readout -------------------------------
    readout = load("readout_sensitivity.csv", text=("detector",))
    ratios = [0.0001, 0.001, 0.01, 0.05, 0.1]
    RR = lambda d, q: next(
        r for r in readout if r["detector"] == d and abs(r["ratio"] - q) < 1e-12
    )
    body = []
    for d in ORDER:
        for q in ratios:
            r = RR(d, q)
            body.append(
                f"{NAME[d]} & {100*q:g}\\% & "
                f"{ci(r, 'headroom', 'ci_low', 'ci_high')}"
            )
    write("tab_readout_sensitivity.tex",
          "Oracle-mean headroom under five anomaly-map readouts on the same "
          "6,000-object sample. Each readout averages the indicated fraction of "
          "highest-scoring pixels. The five rows within a detector come from "
          "the same forward pass. The 1\\% reruns reproduce the archived VisualAD "
          "scores but not the archived AnomalyCLIP and Cross-view NN scores; the "
          "table is therefore a within-run sensitivity analysis rather than an "
          "exact replication of every cross-detector value in the main analysis.",
          "tab:readout",
          r"Detector & Readout & Headroom [95\% CI]", body,
          wide=False, cols="lrr")


if __name__ == "__main__":
    main()
