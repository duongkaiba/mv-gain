# G series: rules fixed before any G result exists

Written 2026-09-18, before G1 or G2 had produced a single validation number.
The point of writing it now is that none of the choices below can be made
after seeing the test table.

## What changed relative to A-F

Exactly one architectural decision, as required by plan section 11 for the
case "every multi-view variant ties the baseline": the object representation
now has a readout and a loss term of its own.

    image  level (unchanged): cos(anomaly_token, patch) - cos(normal_token, patch)
    object level (new)      : cos(obj_anomaly,  e)      - cos(obj_normal,  e)

Everything else is held fixed: same initialisation from A, same 11000
optimizer updates, same seed, same learning rates, same loss weights on the
four existing terms, same locked pixel subset, same folds.

Plan section 4.4 excluded an object head from the FIRST version, as an
experimental control. That version has now been run and reported. This is the
second version.

## Runs and their controls

| Run | Architecture | Control | Question |
| --- | --- | --- | --- |
| G1 | A + object head | A_continued | Was the missing object-level objective the problem? |
| G2 | F + object head | F | Do the cross-view modules pay off once an object-level objective exists? |
| G1 vs G2 | - | - | Are the cross-view modules useless outright, or only useless without that objective? |

Both controls are already trained and evaluated; neither is re-run.

## Which score becomes the headline number

The evaluator now reports three families on every run:

  * `S-AUROC/mean` etc, the historical mean over view scores
  * `S-AUROC/head`, the object head alone
  * `S-AUROC/map+head@a` for a in {0.5, 1.0, 2.0}, each term standardised
    within its category before summing

**The choice is made on validation and then locked.** Procedure:

1. Read `val_best.json` of the G run. Pick the family with the highest
   `S-AUROC/<rule>` there.
2. Record the choice in this file before opening any test metrics.
3. Report that rule on test. The other families are still printed, as
   secondary numbers, never as the claim.

Checkpoint selection is NOT changed: `J_val` stays
`0.5 * macro(S-AUROC/mean) + 0.5 * macro(P-AP)` for every variant including G,
so the checkpoint-selection criterion cannot differ between G and its control.

## Decision threshold

G1 or G2 counts as a success only if it beats its control with a paired
object-level bootstrap 95 percent interval that does not contain zero, macro
recomputed inside every resample.

Reference values from the same protocol, fold 0 seed 0:

    A -> A_continued          +0.67  [+0.49, +0.86]  significant
    A_continued -> F          -0.29  [-0.75, +0.18]  not significant

If neither G run clears its control, that is the second time the budget
control has won. Plan section 11, last row, then applies: withdraw the
contribution hypothesis rather than add another module.

## What is being watched for a false positive

  * P-AP and AUPRO must not fall. An object BCE that turns the model into an
    image classifier would raise S-AUROC while destroying localisation.
  * The spillover diagnostic must not rise sharply. A head that scores clean
    views of an anomalous object as anomalous is using object-level leakage,
    not detection.
  * A large validation-to-test gap would indicate the head learned a
    category shortcut, which cannot transfer to unseen categories by
    construction.

## Known issue fixed alongside

`by_k` and `by_defect_area` in the evaluator pooled all test categories into a
single AUROC while every other number in the report is a macro over
categories. Since the per-category score baseline spans -0.69 to -0.13 and the
k=1 positives concentrate in the two lowest-baseline categories, the pooled
figure reported 42.7 for a stratum whose macro value is 79.2. Both are now
macro. Earlier tables carrying the pooled numbers are superseded.

---

# Correction, 2026-09-18, after the fold-0 G runs

## The significance tests in the first fold-0 report were wrong

They resampled OBJECTS. The claim of a zero-shot method is about unseen
CATEGORIES, so the category is the sampling unit. The per-category differences
between F and A_continued on fold 0 were

    -0.07  -0.46  +1.02  -3.10  -0.37  +1.22      (sd = 1.55 points)

so with six categories the standard error of the macro difference is 0.63
points. Recomputed with the correct unit:

| comparison | diff | object-level CI (wrong) | category-level CI |
| --- | --- | --- | --- |
| A -> A_continued | +0.67 | [+0.49, +0.86] | [-0.64, +1.98] |
| A_continued -> C | -1.62 | [-2.03, -1.16] | [-3.86, +0.62] |
| A_continued -> D | -1.75 | [-2.35, -1.18] | [-4.90, +1.41] |
| A_continued -> E | -0.76 | [-1.35, -0.20] | [-2.36, +0.83] |
| A_continued -> F | -0.29 | [-0.75, +0.18] | [-1.91, +1.33] |
| A_continued -> E_viewdrop | -0.94 | [-1.44, -0.36] | [-2.86, +0.99] |
| A_continued -> F_no_object | -1.00 | [-1.40, -0.59] | [-4.34, +2.34] |

**No comparison is significant.** Fold 0 did not refute the contribution
hypothesis; it had no power to test it. Detecting a 0.5-point difference at
sd = 1.55 needs of the order of 60 test categories.

`paired_bootstrap` now takes `unit`, defaulting to `"category"`, and
`make_report.py` uses that default.

## What the G runs showed

The object head is not the fix. On validation, against `mean`:

| | G1 | G2 |
| --- | --- | --- |
| S-AUROC/mean | 0.9068 | 0.9226 |
| S-AUROC/head | 0.7324 | 0.7553 |
| S-AUROC/map+head@0.5 | 0.8859 | 0.8829 |
| S-AUROC/map+head@2.0 | 0.8316 | 0.8303 |

Every mixture is worse than `mean` alone and gets worse as the head is given
more weight, so the pre-registered validation rule selects `mean` and the head
contributes nothing. The training object loss fell to 0.005-0.02, i.e. the head
nearly solves the source categories, while transferring at 0.73. That gap is
a category shortcut, the failure mode this document listed in advance.

## Next step

Expand to all five folds for A, A_continued and F only. Each fold contributes
six distinct test categories, so the paired comparison goes from n=6 to n=30
categories and the standard error from 0.63 to about 0.28 points, enough to
resolve a difference of roughly 0.6 points.

C, D and E are not re-run: fold 0 is enough to say they are not promising, and
the open question is only whether F beats the budget control.

Order within a fold is fixed by dependency: A, then A_continued and F, both of
which initialise from that fold's A, with F also using it as frozen teacher.
Twelve runs, about 20 hours per fold, two folds per GPU.
