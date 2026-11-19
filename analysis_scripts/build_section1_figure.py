#!/usr/bin/env python3
"""Teaser figure: the question the paper asks, drawn on one real object.

One anomalous object is passed through the trained detector. The figure shows
the five views, the anomaly map the detector produces for each, the five scalar
scores it reads off them, and the single object score the aggregator returns.
The two intervention points of the study are marked on the same picture.

Run from the repository root with the project virtualenv.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
EP = ROOT / "detector/EP_MVAD"
EXP = ROOT / "research/mv_zsad_experiments"
DATA = ROOT / "research/datasets/Real-IAD/extracted"
FIG_DIR = PAPER / "paper_assets/figures"
sys.path.insert(0, str(EP))

from ep_mvad.common.config import load_config            # noqa: E402
from ep_mvad.data.transforms import build_transforms     # noqa: E402
from ep_mvad.models.detector import EPMVAD               # noqa: E402

CROP, THUMB = 760, 300


def find_object(category: str, k: int):
    with (EXP / "protocol/manifests/realiad.jsonl").open(encoding="utf-8") as fh:
        best = None
        for line in fh:
            o = json.loads(line)
            if o["category"] != category or o["object_label"] != 1:
                continue
            seen = [v for v in o["views"] if v["image_label"] == 1]
            if len(seen) != k:
                continue
            area = min(v["mask_area_frac"] for v in seen)
            if best is None or area > best[0]:
                best = (area, o)
    if best is None:
        raise SystemExit(f"no object with category={category}, k={k}")
    return best[1]


@torch.no_grad()
def run(obj, ckpt: Path, device: str):
    cfg = load_config(str(EP / "configs/F.yaml"))
    cfg.runtime.device = device
    model = EPMVAD(cfg, device)
    model.load_state_dict_ep(torch.load(ckpt, map_location="cpu", weights_only=False), False)
    model.eval().to(device)
    size = int(cfg.model.image_size)
    img_tf, _ = build_transforms(size)
    views = sorted(obj["views"], key=lambda v: v["view_id"])
    batch = torch.stack([img_tf(Image.open(DATA / v["image_path"]).convert("RGB"))
                         for v in views]).unsqueeze(0).to(device)
    valid = torch.ones(1, len(views), dtype=torch.bool, device=device)
    out = model(batch, valid)
    amaps = out["anomaly_maps"][0].mean(1).float().cpu().numpy()   # (V, H, W)
    ratio = float(cfg.eval.topk_ratio)
    scores = [float(np.sort(m.ravel())[::-1][:max(1, int(ratio * m.size))].mean())
              for m in amaps]
    return views, amaps, scores


def crop(path: Path, mask: bool = False):
    img = Image.open(path)
    img = img.convert("L" if mask else "RGB")
    w, h = img.size
    box = ((w - CROP) // 2, (h - CROP) // 2, (w + CROP) // 2, (h + CROP) // 2)
    return img.crop(box).resize((THUMB, THUMB),
                                Image.NEAREST if mask else Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="audiojack")
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()

    obj = find_object(args.category, args.k)
    # The checkpoint must be the one whose TEST fold contains this category,
    # otherwise the figure would show a prediction on a category the model saw.
    folds = json.loads((EXP / "protocol/folds.json").read_text())["folds"]
    held_out = [i for i, f in enumerate(folds) if args.category in f["test"]]
    if len(held_out) != 1:
        raise SystemExit(f"{args.category}: expected exactly one test fold, got {held_out}")
    fold = held_out[0]
    print(f"category held out in fold {fold}; using that checkpoint")
    ckpt = EXP / f"runs/fold_{fold:02d}/seed_00/F/best.pth"
    views, amaps, scores = run(obj, ckpt, args.device)
    print(f"{obj['category']} {obj['sample_id']} defect={obj['defect_class']}")
    print("  visible in views:", [v["view_id"] for v in views if v["image_label"] == 1])
    print("  view scores:", " ".join(f"{s:+.3f}" for s in scores))
    print(f"  mean = {np.mean(scores):+.3f}   max = {np.max(scores):+.3f}")

    plt.rcParams.update({"font.size": 8, "savefig.dpi": 300, "pdf.fonttype": 42})
    fig = plt.figure(figsize=(7.0, 4.4))
    gs = fig.add_gridspec(3, 5, height_ratios=[1, 1, .80], hspace=.06, wspace=.05,
                          top=.87, bottom=.02)

    lo, hi = np.percentile(np.stack(amaps), [40, 99.7])
    for c, (view, amap) in enumerate(zip(views, amaps)):
        rgb = np.asarray(crop(DATA / view["image_path"]))
        mask = None
        if view["mask_path"]:
            m = np.asarray(crop(DATA / view["mask_path"], True)) > 127
            mask = m if m.any() else None

        ax = fig.add_subplot(gs[0, c])
        ax.imshow(rgb)
        if mask is not None:
            ax.contour(mask, levels=[.5], colors="#ff2d1a", linewidths=1.1)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"view {c+1}", fontsize=7.5, pad=3)
        for sp in ax.spines.values():
            sp.set_edgecolor("#c0392b" if view["image_label"] == 1 else "#cccccc")
            sp.set_linewidth(1.6 if view["image_label"] == 1 else .6)

        # The anomaly map is produced at the model resolution, so the centre
        # crop has to be taken as the same fraction of the map, not in source
        # pixels.
        ax = fig.add_subplot(gs[1, c])
        side = amap.shape[0]
        half = int(side * CROP / 1024) // 2
        mid = side // 2
        sub = amap[mid - half:mid + half, mid - half:mid + half]
        sub = np.asarray(Image.fromarray(sub).resize((THUMB, THUMB), Image.BILINEAR))
        ax.imshow(rgb)
        ax.imshow(np.clip((sub - lo) / (hi - lo), 0, 1), cmap="inferno",
                  alpha=.68, vmin=0, vmax=1)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_edgecolor("#cccccc"); sp.set_linewidth(.6)
        if c == 0:
            ax.set_ylabel("anomaly map", fontsize=7.2, labelpad=4)

    ax = fig.add_subplot(gs[2, :]); ax.axis("off")
    ax.set(xlim=(0, 10), ylim=(0, 3))
    for c, sc in enumerate(scores):
        x = 1.02 + c * 1.72
        seen = views[c]["image_label"] == 1
        ax.add_patch(FancyBboxPatch((x - .52, 2.18), 1.04, .60,
                                    boxstyle="round,pad=0.03",
                                    fc="#f6c6b8" if seen else "#eceff1",
                                    ec="#c0392b" if seen else "#9e9e9e",
                                    lw=1.3 if seen else .7))
        ax.text(x, 2.48, f"$s_{{{c+1}}}$ = {sc:+.2f}", ha="center", va="center", fontsize=7.2)
    for c in range(5):
        ax.add_patch(FancyArrowPatch((1.02 + c * 1.72, 2.15), (4.30, 1.32),
                                     arrowstyle="-", lw=.6, color="#b8b8b8"))
    ax.add_patch(FancyBboxPatch((3.42, .58), 1.76, .72, boxstyle="round,pad=0.04",
                                fc="#f2d4c9", ec="#707070", lw=.8))
    ax.text(4.30, .94, "aggregation $g$", ha="center", va="center", fontsize=7.5)
    ax.add_patch(FancyArrowPatch((5.25, .94), (5.78, .94), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.0, color="#555555"))
    ax.add_patch(FancyBboxPatch((5.86, .58), 2.22, .72, boxstyle="round,pad=0.04",
                                fc="#c0392b", ec="#707070", lw=.8))
    ax.text(6.97, .94, f"object score  {np.mean(scores):+.2f}",
            ha="center", va="center", fontsize=7.5, color="white")

    fig.text(.015, .965, "Where does the multi-view gain come from?",
             fontsize=9, fontweight="bold")
    fig.text(.015, .925,
             "intervention 1: change the scorer $f$ that produces the maps and scores   |   "
             "intervention 2: change the aggregator $g$ that combines them",
             fontsize=7, color="#555555")
    plt.savefig(FIG_DIR / "fig1_teaser.pdf", bbox_inches="tight")
    plt.savefig(FIG_DIR / "fig1_teaser.png", bbox_inches="tight")
    plt.close()
    print("wrote fig1_teaser")


if __name__ == "__main__":
    main()
