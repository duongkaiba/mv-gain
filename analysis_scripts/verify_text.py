#!/usr/bin/env python3
"""Check the manuscript TEXT, not only the generated tables.

verify_claims.py compares CSV files against numbers hard-coded in itself, so a
sentence in the manuscript that drifts away from the data still passes. An
external audit found exactly that failure: several sections kept an older claim
after the evidence had changed. This script reads the .tex sources and checks

  1. numbers written in prose against the CSV they come from,
  2. that retired wordings do not reappear anywhere,
  3. the abstract word count against the journal limit.

Run it together with verify_claims.py; the build is only clean when both pass.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
CSV_DIR = PAPER / "paper_assets/results"
SOURCES = ([PAPER / "main_review.tex", PAPER / "supplementary.tex",
            PAPER / "highlights.tex"]
           + sorted((PAPER / "tex/sections").glob("*.tex"))
           + sorted((PAPER / "tex/tables").glob("*.tex")))
ABSTRACT_LIMIT = 250
FAIL = []


def load(name, text=()):
    rows = []
    for r in csv.DictReader((CSV_DIR / name).open(encoding="utf-8")):
        rows.append({k: (v if k in text or v == "" else float(v)) for k, v in r.items()})
    return rows


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(label)


def body(paths):
    return {p.name: p.read_text(encoding="utf-8") for p in paths}


TEXT = body(SOURCES)
ALL = "\n".join(TEXT.values())


def present(needle, where=None):
    hay = ALL if where is None else TEXT[where]
    return needle in hay


def sources_mentioning(needle):
    return sorted(n for n, t in TEXT.items() if needle in t)


print("Retired wordings must not reappear")
RETIRED = {
    "already close to the best it can do": "headline withdrawn after the temperature sweep",
    "is already optimal within measurement error": "withdrawn, Variety regime is not neutral",
    "the strongest measurement in the study": "withdrawn, Variety carries a k=5-dominated regime",
    "in a first draft": "self-narration removed",
    "all ruled out": "mechanisms were not ruled out, their evidence was withdrawn",
    "22 category-paired": "the family is now 45",
    "three quarters of a point wide": "intervals are within, not narrower than, 0.75",
    "three times too narrow": "measured factor is three to eight",
    "30,210 objects": "30,209 objects are scored",
    "roughly three\ntimes narrower": "measured median factor is 1.4",
}
for phrase, why in RETIRED.items():
    hits = sources_mentioning(phrase)
    check(f"absent: {phrase!r}", not hits, why if not hits else "found in " + ", ".join(hits))

print()
print("Numbers written in prose match the CSV they come from")

ex = load("extra_aggregators.csv", text=("group", "detector", "rule", "hyperparameter"))
nominal = [r for r in ex if r["ci_low"] > 0]
check("prose states 23 new comparisons and the text agrees with the CSV",
      len(ex) == 23 and present("23 new comparisons"))
check("prose states 45 comparisons", present("45 pre-specified") or present("45 category-paired"))
if nominal:
    r = nominal[0]
    check("the one nominal winner is quoted with its own numbers",
          present(f"${r['delta_vs_mean']:+.2f}$ with $[{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]$"),
          f"{r['delta_vs_mean']:+.2f} [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]")
    check("its Bonferroni interval is quoted",
          present(f"$[{r['bonf_ci_low']:+.2f}, {r['bonf_ci_high']:+.2f}]$"))

ls = load("lse_sensitivity.csv", text=("detector", "grid"))
best = max(r["delta_vs_mean"] for r in ls)
worst = min(r["delta_vs_mean"] for r in ls)
check("largest measured gain of any pooling rule is quoted",
      present(f"${best:+.2f}$"), f"{best:+.2f}")
check("largest measured loss is quoted", present(f"${abs(worst):.2f}$"), f"{worst:+.2f}")
lo = min(r["delta_vs_mean"] for r in ls
         if r["grid"] == "scaled" and r["detector"].startswith("f_") and r["tau"] >= 0.5)
hi = max(r["delta_vs_mean"] for r in ls
         if r["grid"] == "scaled" and r["detector"].startswith("f_") and r["tau"] >= 0.5)
check("the VisualAD range of the sweep is quoted",
      present(f"${lo:+.2f}$ to ${hi:+.2f}$"), f"{lo:+.2f}..{hi:+.2f}")

idf = load("identifiability.csv", text=("detector",))
slo = min(r["ceiling_sorted_vs_mean"] for r in idf)
shi = max(r["ceiling_sorted_vs_mean"] for r in idf)
clo = min(r["ceiling_camera_vs_mean"] for r in idf)
chi = max(r["ceiling_camera_vs_mean"] for r in idf)
check("the within-category ceiling range is quoted for sorted scores",
      present(f"${slo:+.2f}$ to $+{shi:.2f}$") or present(f"${slo:+.2f}$ to ${shi:+.2f}$"),
      f"{slo:+.2f}..{shi:+.2f}")
check("the within-category ceiling range is quoted for camera order",
      present(f"${clo:+.2f}$ to\n${chi:+.2f}$") or present(f"${clo:+.2f}$ to ${chi:+.2f}$"),
      f"{clo:+.2f}..{chi:+.2f}")
vlo = min(r["visibility_auroc"] for r in idf)
vhi = max(r["visibility_auroc"] for r in idf)
check("the visibility AUROC range is quoted",
      present(f"${vlo:.1f}$ and ${vhi:.1f}$"), f"{vlo:.1f}..{vhi:.1f}")

km = load("kmix_reweight.csv", text=("detector",))
K = lambda d, f: next(r[f] for r in km if r["detector"] == d)
check("the reweighted headroom pair is quoted",
      present(f"${K('VisualAD-A','headroom_variety_mix'):+.2f}$ and "
              f"${K('VisualAD-Acontinued','headroom_variety_mix'):+.2f}$"))

ctx = load("context_ablation.csv", text=("level", "quantity"))
C = lambda lv, q, f: next(r[f] for r in ctx if r["level"] == lv and r["quantity"] == q)
check("the three context conditions are quoted with their macro I-AUROC",
      all(present(f"${C('i_auroc', q, 'estimate'):.2f}$")
          for q in ("macro real", "macro swap", "macro solo")))
check("the swapped contrast is quoted with its interval",
      present(f"${C('i_auroc','delta_identity','estimate'):+.2f}$ points with\n"
              f"$[{C('i_auroc','delta_identity','ci_low'):+.2f},"
              f"{C('i_auroc','delta_identity','ci_high'):+.2f}]$")
      or present(f"$[{C('i_auroc','delta_identity','ci_low'):+.2f},"
                 f"{C('i_auroc','delta_identity','ci_high'):+.2f}]$"))
check("the object-level contrast is quoted with an interval containing zero",
      present(f"$[{C('s_auroc','delta_identity','ci_low'):+.2f},"
              f"{C('s_auroc','delta_identity','ci_high'):+.2f}]$"))

ro = load("readout_sensitivity.csv", text=("detector",))
cv = [r["headroom"] for r in ro if r["detector"] == "Cross-view NN"]
check("the Cross-view NN readout range is quoted",
      present(f"${max(cv):.2f}$") and present(f"${min(cv):.2f}$"),
      f"{min(cv):.2f}..{max(cv):.2f}")
check("the manuscript says detector-readout pair, not detector alone",
      present("detector--readout pair"))

print()
print("Retired after the context ablation")
for phrase, why in {
    "whether the upstream gain of f_mv is due to cross-view context or to its other components is not tested here":
        "it is tested now",
}.items():
    hits = sources_mentioning(phrase)
    check(f"absent: {phrase[:48]!r}...", not hits, why if not hits else ", ".join(hits))

print()
print("Abstract length")
m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", TEXT["main_review.tex"], re.S)
words = len(re.sub(r"[${}\\]", " ", m.group(1)).split()) if m else -1
check(f"abstract is at most {ABSTRACT_LIMIT} words", 0 < words <= ABSTRACT_LIMIT, f"{words} words")

print()
print(f"{len(FAIL)} failed" if FAIL else "manuscript text verified")
for f in FAIL:
    print("  FAILED:", f)
sys.exit(1 if FAIL else 0)
