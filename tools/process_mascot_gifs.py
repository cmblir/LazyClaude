#!/usr/bin/env python3
"""Turn opaque-background mascot GIFs into transparent corner-mascot sprites.

The source GIFs (hand-made elsewhere) come on a pale dithered background
(yellow / lavender / white-ish) at assorted aspect ratios — one is a wide
"run across the screen" canvas. The dashboard mascots, by contrast, are
transparent, roughly square sprites shown ~63px tall in the corner. This tool
bridges the two:

  1. key out the border-connected pale background per frame (4-connectivity
     flood fill — keeps interior white like the checker flag, which is enclosed
     by black and only reachable through the character, not the border);
  2. crop to the character — union bbox when it stays put, or per-frame
     recenter when it translates (the "run" canvas), giving run-in-place;
  3. square-pad with transparency and re-encode as a transparent animated GIF,
     preserving frame timing and subsampling very long animations.

Dev/build-time tool — NOT a runtime dependency. Needs Pillow, numpy, scipy
(same spirit as tools/gen_mascots.py, which needs Pillow). Install into a venv:

    python3 -m venv .venv && .venv/bin/pip install Pillow numpy scipy

Usage:

    python tools/process_mascot_gifs.py --out dist/mascots \\
        run=/path/to/a.gif flag=/path/to/b.gif party=/path/c.gif stand=/path/d.gif

Each positional arg is `<mascot-name>=<source-gif>`; output is
`<out>/<mascot-name>.gif`. Remember to add the name to `_MASCOT_FRIENDS` in
`dist/app.js` so the rotation picks it up.
"""
from __future__ import annotations

import argparse
import math
import os

import numpy as np
from PIL import Image, ImageSequence
from scipy import ndimage

MAX_FRAMES = 28  # subsample longer animations to keep the GIF small


def load_frames(path: str):
    im = Image.open(path)
    frames, durs = [], []
    base = im.info.get("duration", 80)
    for fr in ImageSequence.Iterator(im):
        frames.append(np.array(fr.convert("RGBA")))
        durs.append(fr.info.get("duration", base))
    if len(frames) > MAX_FRAMES:  # keep timing roughly constant
        step = math.ceil(len(frames) / MAX_FRAMES)
        frames, durs = frames[::step], [d * step for d in durs[::step]]
    return frames, durs


def bg_floodfill_mask(arr: np.ndarray) -> np.ndarray:
    """True where a pixel is border-connected pale background.

    Background is a dither of pale colours (every channel high); the character
    is terracotta (low G/B). scipy connected components keeps this O(pixels).
    """
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    pale = (r >= 200) & (g >= 200) & (b >= 160)
    lbl, _ = ndimage.label(pale)  # default structure = 4-connectivity (2D)
    border = np.concatenate([lbl[0, :], lbl[-1, :], lbl[:, 0], lbl[:, -1]])
    return np.isin(lbl, np.setdiff1d(np.unique(border), [0]))


def _bbox(opaque: np.ndarray):
    ys, xs = np.where(opaque)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def process(path: str, out_path: str, pad_frac: float = 0.10, max_side: int = 256,
            target_h_frac: float = 0.56) -> dict:
    frames, durs = load_frames(path)
    keyed = []
    for arr in frames:
        a = arr.copy()
        a[bg_floodfill_mask(a), 3] = 0
        keyed.append(a)
    h, w = keyed[0].shape[:2]

    bbs = [_bbox(a[:, :, 3] > 16) for a in keyed]
    valid = [b for b in bbs if b]
    union = (min(b[0] for b in valid), min(b[1] for b in valid),
             max(b[2] for b in valid), max(b[3] for b in valid))
    bbs = [b if b else union for b in bbs]
    cxs = [(b[0] + b[2]) / 2 for b in bbs]
    cys = [(b[1] + b[3]) / 2 for b in bbs]
    recenter = (max(cxs) - min(cxs) > 0.18 * w) or (max(cys) - min(cys) > 0.18 * h)

    # Representative (median) per-frame character height drives the apparent
    # size; the crop boxes that actually get placed drive the no-clip guard.
    per_h = sorted(b[3] - b[1] + 1 for b in bbs)
    per_w = [b[2] - b[0] + 1 for b in bbs]
    rep_h = per_h[len(per_h) // 2]
    if recenter:
        crops = bbs
        crop_max_h = per_h[-1]
        crop_max_w = max(per_w)
    else:
        crops = [union] * len(keyed)
        crop_max_h = union[3] - union[1] + 1
        crop_max_w = union[2] - union[0] + 1
    # Normalise apparent size: pick the square canvas so the *typical* (median)
    # character height is a fixed fraction of the canvas (target_h_frac). The
    # sprite is shown height-filling a square box, so equal median-char-height /
    # canvas across mascots → equal on-screen size — this is what keeps the new
    # poses consistent with claw'd. Sizing on the median (not the max) keeps a
    # pose whose animation has tall outlier frames (e.g. a squash/stretch) from
    # looking shrunken; the max(...) guards ensure the tallest/widest crop still
    # fits without clipping.
    if target_h_frac:
        side = max(int(round(rep_h / target_h_frac)),
                   crop_max_h,
                   int(round(crop_max_w / 0.86)))
    else:
        side = int(round(max(crop_max_w, crop_max_h) * (1 + 2 * pad_frac)))

    pframes = []
    for arr, (x0, y0, x1, y1) in zip(keyed, crops):
        cw, ch = x1 - x0 + 1, y1 - y0 + 1
        canvas = np.zeros((side, side, 4), np.uint8)
        ox, oy = (side - cw) // 2, (side - ch) // 2
        canvas[oy:oy + ch, ox:ox + cw, :] = arr[y0:y1 + 1, x0:x1 + 1, :]
        img = Image.fromarray(canvas, "RGBA")
        if side > max_side:
            img = img.resize((max_side, max_side), Image.NEAREST)
        alpha = np.array(img)[:, :, 3]
        p = img.convert("RGB").quantize(colors=255, method=Image.MEDIANCUT, dither=Image.NONE)
        p.paste(255, Image.fromarray(((alpha <= 16).astype(np.uint8) * 255)))  # idx 255 = transparent
        pframes.append(p)

    pframes[0].save(out_path, save_all=True, append_images=pframes[1:],
                    duration=durs, loop=0, disposal=2, transparency=255, optimize=True)
    return dict(frames=len(pframes), side=min(side, max_side), recenter=recenter)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output directory (e.g. dist/mascots)")
    ap.add_argument("--max-side", type=int, default=256,
                    help="max output canvas side in px (480 matches the existing claw'd set)")
    ap.add_argument("--target-h-frac", type=float, default=0.56,
                    help="median character height as a fraction of the canvas (size normalisation)")
    ap.add_argument("specs", nargs="+", metavar="name=source.gif",
                    help="one or more <mascot-name>=<source-gif> pairs")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for spec in args.specs:
        name, _, src = spec.partition("=")
        if not src:
            ap.error(f"bad spec {spec!r} — expected name=source.gif")
        out_path = os.path.join(args.out, f"{name}.gif")
        st = process(src, out_path, max_side=args.max_side, target_h_frac=args.target_h_frac)
        print(f"{name:8} {st}  ->  {out_path} ({os.path.getsize(out_path):,} bytes)")


if __name__ == "__main__":
    main()
