#!/usr/bin/env python3
"""Turn a flat still into depth-separated layers for true 2.5D parallax.

A monocular depth model estimates per-pixel depth, the image is split into
depth bands, and the area hidden behind each nearer band is inpainted so the
layer behind it is complete. Remotion's <ParallaxPhoto> then moves the layers
at different rates under one virtual camera.

Honest limits, because this fails in specific and visible ways:
  - Depth models guess. Hair, glasses, motion blur and busy backgrounds all
    produce ragged edges that look worse than no parallax at all.
  - Inpainting is classical (Telea), not generative. It fills small holes
    convincingly and large ones as smears. Keep `strength` modest.
  - EVERY generated layer set must be eyeballed before use. This module
    writes a QC contact sheet for exactly that reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "graphics" / "public" / "fx"
W, H = 1920, 1080

# Small + fast + good enough at 1080p. Downloaded once to the HF cache.
DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"

_PIPE = None


def _depth_pipe():
    global _PIPE
    if _PIPE is None:
        from transformers import pipeline as hf_pipeline
        _PIPE = hf_pipeline("depth-estimation", model=DEPTH_MODEL)
    return _PIPE


def load_cover(path, w=W, h=H) -> np.ndarray:
    """Load and center-crop-cover to w x h. Returns BGR uint8."""
    img = Image.open(path).convert("RGB")
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = int(round(sw * scale)), int(round(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    img = img.crop((left, top, left + w, top + h))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def depth_map(bgr: np.ndarray) -> np.ndarray:
    """Return float32 depth in 0..1 where 1 = nearest."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    out = _depth_pipe()(Image.fromarray(rgb))
    d = np.array(out["depth"], dtype=np.float32)
    if d.shape[:2] != bgr.shape[:2]:
        d = cv2.resize(d, (bgr.shape[1], bgr.shape[0]),
                       interpolation=cv2.INTER_CUBIC)
    lo, hi = float(d.min()), float(d.max())
    if hi - lo < 1e-6:
        return np.zeros_like(d)
    d = (d - lo) / (hi - lo)
    # Depth-Anything returns larger = closer. Smooth so band edges follow
    # surfaces instead of model noise.
    return cv2.bilateralFilter(d, 9, 0.08, 9)


def build_layers(bgr: np.ndarray, depth: np.ndarray, n_layers=3,
                 feather=9, inpaint_radius=7):
    """Split into n depth bands, back to front.

    Returns a list of RGBA uint8 arrays. Layer 0 is the fully opaque,
    inpainted background; each subsequent layer carries a feathered alpha.
    """
    n_layers = max(2, int(n_layers))
    # Quantile thresholds keep bands populated regardless of the histogram.
    qs = [np.quantile(depth, i / n_layers) for i in range(1, n_layers)]

    masks = []
    for k in range(n_layers):
        lo = -1.0 if k == 0 else qs[k - 1]
        hi = 2.0 if k == n_layers - 1 else qs[k]
        masks.append(((depth > lo) & (depth <= hi)).astype(np.uint8) * 255)

    layers = []
    for k in range(n_layers):
        if k == 0:
            # Background: everything nearer is a hole to be filled, so the
            # plate stays complete when nearer layers slide across it.
            hole = np.zeros(depth.shape, np.uint8)
            for j in range(1, n_layers):
                hole |= masks[j]
            hole = cv2.dilate(hole, np.ones((9, 9), np.uint8), iterations=2)
            filled = cv2.inpaint(bgr, hole, inpaint_radius, cv2.INPAINT_TELEA)
            rgba = cv2.cvtColor(filled, cv2.COLOR_BGR2BGRA)
            rgba[:, :, 3] = 255
        else:
            alpha = masks[k]
            # Close pinholes, then feather so the cut edge is not a stair.
            alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE,
                                     np.ones((7, 7), np.uint8))
            if feather > 0:
                f = feather if feather % 2 else feather + 1
                alpha = cv2.GaussianBlur(alpha, (f, f), 0)
            src = bgr
            if k < n_layers - 1:
                # Mid layers also get holes filled where nearer bands sit.
                hole = np.zeros(depth.shape, np.uint8)
                for j in range(k + 1, n_layers):
                    hole |= masks[j]
                hole = cv2.dilate(hole, np.ones((7, 7), np.uint8), iterations=1)
                src = cv2.inpaint(bgr, hole, inpaint_radius, cv2.INPAINT_TELEA)
            rgba = cv2.cvtColor(src, cv2.COLOR_BGR2BGRA)
            rgba[:, :, 3] = alpha
        layers.append(rgba)
    return layers


def qc_sheet(bgr, depth, layers, dest):
    """Contact sheet: source, depth, and each layer over magenta so alpha
    problems are impossible to miss."""
    tiles = [cv2.resize(bgr, (480, 270))]
    dvis = cv2.applyColorMap((depth * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    tiles.append(cv2.resize(dvis, (480, 270)))
    for rgba in layers:
        small = cv2.resize(rgba, (480, 270))
        a = small[:, :, 3:4].astype(np.float32) / 255.0
        bg = np.zeros((270, 480, 3), np.uint8)
        bg[:, :] = (255, 0, 255)
        comp = (small[:, :, :3].astype(np.float32) * a
                + bg.astype(np.float32) * (1 - a)).astype(np.uint8)
        tiles.append(comp)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.zeros((rows * 270, cols * 480, 3), np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * 270:(r + 1) * 270, c * 480:(c + 1) * 480] = t
    cv2.imwrite(str(dest), sheet)
    return dest


def assess(bgr: np.ndarray, depth: np.ndarray) -> dict:
    """Score whether a still is a good parallax candidate.

    Locked-off shots with a clear subject (interviews, the teen webcam
    archive) separate cleanly. Handheld motion-blurred footage produces a
    mush depth map and a background plate that is pure inpaint smear; that
    case must never ship, and it is also pointless - moving footage already
    has real parallax.

    Measured on three real frames (Laplacian variance / depth std /
    edge-alignment):

        colin interview  14.5 / 0.201 / 4.80   -> clean matte
        teen archive      3.3 / 0.326 / 2.43   -> clean matte
        airrack gym walk  3.2 / 0.328 / 1.81   -> mush, must not ship

    Sharpness and depth-spread do NOT discriminate: the teen archive and the
    unusable gym walk score identically on both. Only edge-alignment - do the
    depth discontinuities land on actual picture edges - tracks the visual
    verdict, so that is what the gate uses.

    Calibrated on three samples, so treat ACCEPT as "worth reviewing", not
    as proof. The QC sheet remains the real gate.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Kept for the record even though they are weak discriminators on
    # compressed video frames - useful for spotting a totally flat input.
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    spread = float(depth.std())

    # The signal that works: a trustworthy matte has its depth gradient
    # sitting on top of an image gradient.
    dg = np.abs(cv2.Laplacian(depth, cv2.CV_32F))
    dg = dg / (dg.max() + 1e-6)
    ig = np.abs(cv2.Laplacian(gray.astype(np.float32) / 255.0, cv2.CV_32F))
    ig = ig / (ig.max() + 1e-6)
    strong = dg > np.quantile(dg, 0.98)
    alignment = float(ig[strong].mean() / (ig.mean() + 1e-6)) if strong.any() \
        else 0.0

    # Absolute depth threshold, NOT a quantile - a quantile makes this
    # constant by construction and therefore meaningless.
    near_frac = float((depth > 0.62).mean())

    ALIGN_MIN, ALIGN_CONFIDENT = 2.1, 3.5
    reasons = []
    if alignment < ALIGN_MIN:
        reasons.append(
            f"depth edges do not follow picture edges ({alignment:.2f} < "
            f"{ALIGN_MIN}) - typical of handheld/motion-blurred footage, "
            f"which already has real parallax and does not need fake depth")
    if spread < 0.05:
        reasons.append(f"frame is effectively one plane (std {spread:.3f})")
    if near_frac > 0.80:
        reasons.append(f"foreground covers {near_frac:.0%} of frame - the "
                       f"background plate would be almost entirely inpaint")

    ok = not reasons
    return {
        "suitable": ok,
        "confidence": ("high" if alignment >= ALIGN_CONFIDENT else
                       "review-required" if ok else "rejected"),
        "sharpness": round(sharpness, 1),
        "depth_spread": round(spread, 4),
        "edge_alignment": round(alignment, 3),
        "near_fraction": round(near_frac, 4),
        "reasons": reasons,
        "recommendation": "ParallaxPhoto" if ok else
                          "KenBurns2 (eased push) - do not fake depth here",
    }


def make(src_image, name, n_layers=3, outdir=None, force=False):
    """Generate layer PNGs + QC sheet. Returns the props dict for Remotion."""
    outdir = Path(outdir) if outdir else PUBLIC
    outdir.mkdir(parents=True, exist_ok=True)
    bgr = load_cover(src_image)
    depth = depth_map(bgr)

    verdict = assess(bgr, depth)
    if not verdict["suitable"] and not force:
        qc_sheet(bgr, depth, build_layers(bgr, depth, n_layers=2),
                 outdir / f"{name}_REJECTED_QC.jpg")
        raise ValueError(
            f"{name}: unsuitable for depth parallax - "
            + "; ".join(verdict["reasons"])
            + f". Use {verdict['recommendation']}. "
            + f"Rejected QC sheet: {outdir / f'{name}_REJECTED_QC.jpg'}"
        )

    layers = build_layers(bgr, depth, n_layers=n_layers)

    entries = []
    for k, rgba in enumerate(layers):
        p = outdir / f"{name}_L{k}.png"
        cv2.imwrite(str(p), rgba)
        # depth 0 = far (moves least) .. 1 = near (moves most)
        entries.append({
            "src": f"fx/{p.name}",
            "depth": round(k / max(1, len(layers) - 1), 4),
        })
    sheet = qc_sheet(bgr, depth, layers, outdir / f"{name}_QC.jpg")
    return {"layers": entries, "qc_sheet": str(sheet), "assessment": verdict}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("name")
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--force", action="store_true",
                    help="generate layers even if the suitability check fails")
    a = ap.parse_args()
    try:
        props = make(a.image, a.name, n_layers=a.layers, outdir=a.outdir,
                     force=a.force)
    except Exception as e:  # noqa: BLE001
        print(f"[parallax] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(json.dumps(props, indent=2))
    print(f"[parallax] REVIEW {props['qc_sheet']} before using these layers.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
