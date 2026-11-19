#!/usr/bin/env python3
"""Illustration of the defect-visibility variable k, from the dataset itself.

One anomalous object per visibility level is drawn as its five views, with the
ground-truth defect outlined. The point of the figure is that k is a property
of the object and the camera geometry, not of any detector: the same physical
defect is present in every row, yet the number of views that can see it changes
the decision problem completely.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EXP = ROOT / "research/mv_zsad_experiments"
DATA = ROOT / "research/datasets/Real-IAD/extracted"
FIG_DIR = PAPER / "paper_assets/figures"

CROP = 660          # centre crop, in source pixels, before resizing
THUMB = 260


def load_manifest():
    objects = []
    with (EXP / "protocol/manifests/realiad.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            objects.append(json.loads(line))
    return objects


def pick(objects):
    """One object per k, preferring a clearly visible defect and varied categories."""
    chosen, used = {}, set()
    for k in range(1, 6):
        best = None
        for o in objects:
            if o["object_label"] != 1 or o["category"] in used:
                continue
            seen = [v for v in o["views"] if v["image_label"] == 1]
            if len(seen) != k:
                continue
            # Prefer the largest defect at this level so the figure is readable
            # in print; the statistics of the paper use every object regardless.
            area = min(v["mask_area_frac"] for v in seen)
            if best is None or area > best[0]:
                best = (area, o)
        if best is None:
            raise SystemExit(f"no object found with k={k}")
        chosen[k] = best[1]
        used.add(best[1]["category"])
    return chosen


def panel(ax, view, show_mask):
    img = Image.open(DATA / view["image_path"]).convert("RGB")
    w, h = img.size
    box = ((w - CROP) // 2, (h - CROP) // 2, (w + CROP) // 2, (h + CROP) // 2)
    crop = img.crop(box).resize((THUMB, THUMB), Image.LANCZOS)
    ax.imshow(np.asarray(crop))
    if show_mask and view["mask_path"]:
        m = Image.open(DATA / view["mask_path"]).convert("L").crop(box)
        m = np.asarray(m.resize((THUMB, THUMB), Image.NEAREST)) > 127
        if m.any():
            ax.contour(m, levels=[.5], colors="#ff2d1a", linewidths=1.2)
            overlay = np.zeros((*m.shape, 4))
            overlay[m] = (1, .18, .10, .28)
            ax.imshow(overlay)
    ax.set_xticks([]); ax.set_yticks([])
    for side in ax.spines.values():
        side.set_edgecolor("#c0392b" if (show_mask and view["image_label"] == 1) else "#cccccc")
        side.set_linewidth(1.6 if (show_mask and view["image_label"] == 1) else .6)


def main():
    chosen = pick(load_manifest())
    plt.rcParams.update({"font.size": 8, "savefig.dpi": 300, "pdf.fonttype": 42})
    fig, axes = plt.subplots(5, 5, figsize=(7.0, 7.4),
                             gridspec_kw={"wspace": .05, "hspace": .05})
    for r, k in enumerate(range(1, 6)):
        obj = chosen[k]
        views = sorted(obj["views"], key=lambda v: v["view_id"])
        for c, view in enumerate(views):
            panel(axes[r, c], view, True)
            if r == 0:
                axes[r, c].set_title(f"view {c+1}", fontsize=7.5, pad=4)
        label = f"$k={k}$\n{obj['category'].replace('_', ' ')}\n{obj['defect_class']}"
        axes[r, 0].set_ylabel(label, fontsize=7.2, labelpad=6)
    plt.savefig(FIG_DIR / "fig3_1_visibility_examples.pdf", bbox_inches="tight")
    plt.savefig(FIG_DIR / "fig3_1_visibility_examples.png", bbox_inches="tight")
    plt.close()
    print("wrote fig3_1_visibility_examples")
    for k, o in chosen.items():
        seen = [v["view_id"] for v in o["views"] if v["image_label"] == 1]
        print(f"  k={k}  {o['category']:18s} {o['sample_id']:14s} defect={o['defect_class']} "
              f"visible in views {seen}")


if __name__ == "__main__":
    main()
