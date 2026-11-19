# Release: data and analyses behind the paper

"Investigating the Sources of Multi-View Gain in Zero-Shot Industrial Anomaly Detection" (Pattern Recognition, under review).

The input datasets are public and are not redistributed here:

- Real-IAD (Wang et al., CVPR 2024)
- Real-IAD Variety (Zhu et al., Pattern Recognition 178, 2026)

## Contents

| Path | Contents |
|---|---|
| `predictions/runs/fold_XX/seed_YY/<variant>/eval/predictions_*.npz` | Per-object and per-view scores of the VisualAD operating points on the test fold (Real-IAD) and on the Variety sample. `A` = f_base, `A_continued` = f_budget, `F` = f_mv; other variants are single-fold development runs. |
| `predictions/baselines/<detector>/<fold or variety>/seed_00/.../predictions_*.npz` | The same for WinCLIP, AnomalyCLIP-VisA and Cross-view NN. |
| `protocol/` | Locked protocol, fold assignment (`folds.json`), semantic-overlap analysis, data audits. |
| `results/*.csv` | Every table in the manuscript and the supplementary material, generated from the prediction files. |
| `analysis_scripts/` | Scripts that generate `results/` from `predictions/`, and `verify_claims.py` / `verify_text.py`, which re-check the numbers stated in the manuscript. |

All post-hoc analyses run on CPU from the prediction files. The scripts were written against the original workspace layout; set their `EXP` path to `release/predictions` (and the protocol path to `release/protocol`) to run them here. The training and inference code will be released in this repository upon publication.
