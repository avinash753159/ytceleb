#!/usr/bin/env python3
"""Turn a depth-layered still into a Business-Casual-style push-in video.

The channel's signature move is not a Ken Burns zoom on a flat postcard: it
reads as a camera physically travelling INTO a scene because near things
cross the frame faster than far things (parallax). `parallax.py` already
splits a still into depth-band layers with the occluded background inpainted
behind each nearer one; this module is only the camera. Every layer gets its
own scale ramp - the nearer the layer, the faster it grows - composited
far-to-near each frame, eased so the move never starts or stops on a hard
edge, with an optional few-pixel lateral drift so the path is not perfectly
axial (a straight-line dolly reads as mechanical; a hair of curve reads as
handheld/cinematic).

This matters on budget: a generated still costs $0.02-0.04, a 6s generated
video clip costs $0.30. A convincing push-in on a still is what makes ~100
shots affordable at all - so the move has to actually sell as camera motion,
not just prove it exists.

Economics of `layer_gain`: it is the only knob that separates "parallax" from
"zoom" (gain 0.0 IS a flat zoom - every layer travels identically). But the
farther a layer travels relative to the plate behind it, the more of its
Telea-inpainted seam gets dragged into view - `parallax.py`'s own warning
about ragged edges on hair/glasses/motion-blur applies harder the more that
layer moves. 0.4-0.6 is the usable range on clean mattes; push higher only
after checking the QC sheet, not before.

`flat_zoom()` is the deliberate fallback for stills `parallax.assess()`
rejects: it skips the depth model entirely (no mush background to expose)
and applies the exact same eased camera to the flat cover image as a single
opaque layer, so callers can pick either function off one suitability check
without special-casing the render step.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

import parallax

ROOT = Path(__file__).resolve().parents[1]

FPS = 24
OUT_W, OUT_H = 1920, 1080

# Depth/layer computation is a CPU torch forward pass per image - slow, and
# this pipeline calls push_in() ~100 times across a film. Keyed on the
# source bytes (not the path) so a renamed/copied file still hits cache.
CACHE_DIR = ROOT / "work" / "pushin_cache"


# ------------------------------------------------------------------ easing
#
# "Eased" specifically means: zero velocity at both ends. A push that starts
# or stops at constant speed reads as a cut, not a camera - that is the
# whole reason this exists instead of a linear scale ramp.

def ease_smoothstep(t: float) -> float:
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


def ease_cosine(t: float) -> float:
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return (1.0 - math.cos(math.pi * t)) / 2.0


EASES = {"smoothstep": ease_smoothstep, "cosine": ease_cosine}


# -------------------------------------------------------------- frame math

def frame_count(seconds: float) -> int:
    """Contractual frame count for a shot of this many seconds at FPS.

    Frame count is contractual elsewhere in this pipeline - a shot one frame
    short is a build error, not a rounding footnote - so every caller
    (render, tests, the CLI) goes through this one function.
    """
    return round(seconds * FPS)


def layer_travel(depth: float, start_scale: float, end_scale: float,
                  layer_gain: float) -> float:
    """Total scale a layer at this depth travels over the full shot.

    depth: 0.0 = farthest layer, 1.0 = nearest. The farthest layer always
    travels exactly (end_scale - start_scale); layer_gain scales how much
    MORE the nearer layers travel on top of that. gain=0 -> every layer
    travels identically, i.e. a flat zoom by construction.
    """
    base = end_scale - start_scale
    return base * (1.0 + layer_gain * depth)


def layer_scale(depth: float, t: float, start_scale: float, end_scale: float,
                 layer_gain: float, ease_fn) -> float:
    """Scale of a layer at eased progress t in [0, 1]."""
    travel = layer_travel(depth, start_scale, end_scale, layer_gain)
    return start_scale + travel * ease_fn(t)


# ---------------------------------------------------------------- caching

def _cache_key(image: Path, n_layers: int) -> str:
    digest = hashlib.sha1(Path(image).read_bytes()).hexdigest()[:20]
    return f"{digest}_n{n_layers}"


def _get_layers(image: Path, n_layers: int):
    """Depth-band layers for `image`, computed once and cached to disk.

    Returns (layers, meta) where layers is a list of BGRA uint8 arrays,
    far-to-near, and meta carries parallax.assess()'s verdict so callers can
    see (and this module can warn on) shots that never should have reached
    push_in() in the first place.
    """
    key = _cache_key(image, n_layers)
    cdir = CACHE_DIR / key
    meta_path = cdir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        layers = [cv2.imread(str(cdir / f"L{k}.png"), cv2.IMREAD_UNCHANGED)
                  for k in range(meta["n_layers"])]
        if all(layer is not None for layer in layers):
            return layers, meta
        # Partial/corrupt cache entry - fall through and rebuild.

    cdir.mkdir(parents=True, exist_ok=True)
    bgr = parallax.load_cover(image, OUT_W, OUT_H)
    depth = parallax.depth_map(bgr)
    verdict = parallax.assess(bgr, depth)
    layers = parallax.build_layers(bgr, depth, n_layers=n_layers)
    for k, rgba in enumerate(layers):
        cv2.imwrite(str(cdir / f"L{k}.png"), rgba)
    meta = {"n_layers": len(layers), "assessment": verdict}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return layers, meta


# ------------------------------------------------------------- compositing

def _place(rgba: np.ndarray, scale: float, dx: float, dy: float) -> np.ndarray:
    """Scale a layer and crop its centre (offset by dx, dy) to OUT_W x OUT_H.

    scale must be >= 1.0 for every caller in this module (start_scale is
    validated > 1.0 and travel only adds to it), so the crop is always
    fully inside the resized image - no edge is ever exposed.
    """
    h, w = rgba.shape[:2]
    nw = max(OUT_W, int(round(w * scale)))
    nh = max(OUT_H, int(round(h * scale)))
    resized = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_LINEAR)
    left = int(round((nw - OUT_W) / 2 + dx))
    top = int(round((nh - OUT_H) / 2 + dy))
    left = max(0, min(left, nw - OUT_W))
    top = max(0, min(top, nh - OUT_H))
    return resized[top:top + OUT_H, left:left + OUT_W]


def _composite_frame(layers, depths, t, start_scale, end_scale, drift,
                      layer_gain, ease_fn) -> np.ndarray:
    """One BGR frame: every layer placed at its own eased scale/drift,
    alpha-composited far to near. Layer 0's alpha is 255 everywhere (it is
    the fully-inpainted background), so this also correctly seeds the
    canvas without a special case."""
    canvas = np.zeros((OUT_H, OUT_W, 3), np.float32)
    for layer, depth in zip(layers, depths):
        scale = layer_scale(depth, t, start_scale, end_scale, layer_gain,
                             ease_fn)
        e = ease_fn(t)
        dx = drift[0] * (1.0 + layer_gain * depth) * e
        dy = drift[1] * (1.0 + layer_gain * depth) * e
        crop = _place(layer, scale, dx, dy)
        a = crop[:, :, 3:4].astype(np.float32) / 255.0
        canvas = crop[:, :, :3].astype(np.float32) * a + canvas * (1.0 - a)
    return canvas.astype(np.uint8)


# ------------------------------------------------------------- encoding

def _assert_frames_complete(framedir: Path, n_frames: int) -> None:
    """Fail loudly on any gap. ffmpeg's image2 demuxer stops dead at the
    first missing index in a %06d sequence, which would otherwise silently
    hand back a short video instead of an error."""
    for i in range(n_frames):
        p = framedir / f"{i:06d}.png"
        if not p.exists():
            raise FileNotFoundError(
                f"frame {i}/{n_frames} missing ({p}) - refusing to encode "
                f"a video the image2 demuxer would silently truncate")


def _encode(framedir: Path, n_frames: int, dest: Path) -> Path:
    _assert_frames_complete(framedir, n_frames)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-i", str(framedir / "%06d.png"),
        "-frames:v", str(n_frames),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        # This box has 20 cores; ffmpeg defaults to grabbing all of them,
        # which starves anything else running concurrently (e.g. the ~100
        # other shots this module renders across a film).
        "-threads", "2",
        str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed:\n" + " ".join(cmd[:20]) + "\n"
            + (r.stderr or "")[-2000:])
    return dest


def _render(layers, depths, dest, seconds, start_scale, end_scale, drift,
            layer_gain, ease) -> Path:
    if start_scale <= 1.0:
        raise ValueError(
            f"start_scale={start_scale} must be > 1.0 - anything else "
            f"exposes an edge on frame 0")
    if ease not in EASES:
        raise ValueError(f"unknown ease {ease!r}, want one of {list(EASES)}")
    ease_fn = EASES[ease]

    n_frames = frame_count(seconds)
    with tempfile.TemporaryDirectory(prefix="pushin_") as raw_tmp:
        tmp = Path(raw_tmp)
        for i in range(n_frames):
            t = i / (n_frames - 1) if n_frames > 1 else 1.0
            frame = _composite_frame(layers, depths, t, start_scale,
                                      end_scale, drift, layer_gain, ease_fn)
            cv2.imwrite(str(tmp / f"{i:06d}.png"), frame)
        return _encode(tmp, n_frames, Path(dest))


# ---------------------------------------------------------------- public

def push_in(image: Path, dest: Path, seconds: float, *,
            n_layers: int = 3, start_scale: float = 1.06,
            end_scale: float = 1.22, drift: tuple[float, float] = (0.0, 0.0),
            layer_gain: float = 0.55, ease: str = "smoothstep") -> Path:
    """Depth-layered push-in: true parallax, Business Casual style.

    Nearest layer travels fastest (see layer_gain docstring at module top
    for the seam-visibility trade-off), farthest slowest, composited
    far-to-near every frame with a shared ease so the whole move reads as
    one continuous camera push rather than N independent zooms.
    """
    layers, meta = _get_layers(Path(image), n_layers)
    n = len(layers)
    depths = [k / (n - 1) for k in range(n)] if n > 1 else [0.0]

    verdict = meta["assessment"]
    if not verdict["suitable"]:
        print(
            f"[flow_pushin] WARNING: {image} failed parallax.assess() "
            f"({'; '.join(verdict['reasons'])}) - layers were generated "
            f"anyway but this shot should probably use flat_zoom() instead",
            file=sys.stderr)

    return _render(layers, depths, dest, seconds, start_scale, end_scale,
                   drift, layer_gain, ease)


def flat_zoom(image: Path, dest: Path, seconds: float, *,
              n_layers: int = 3, start_scale: float = 1.06,
              end_scale: float = 1.22, drift: tuple[float, float] = (0.0, 0.0),
              layer_gain: float = 0.55, ease: str = "smoothstep") -> Path:
    """Single-plane eased push - the fallback for stills parallax.assess()
    rejects. Same signature shape as push_in() so a caller can swap between
    them off one suitability check with no special-casing; n_layers and
    layer_gain are accepted but ignored (there is only one plane, so no
    depth model runs and no inpainting seam can ever show)."""
    del n_layers, layer_gain  # accepted for call-site symmetry only
    bgr = parallax.load_cover(image, OUT_W, OUT_H)
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = 255
    return _render([rgba], [0.0], dest, seconds, start_scale, end_scale,
                   drift, 0.0, ease)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("dest")
    ap.add_argument("seconds", type=float)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--start-scale", type=float, default=1.06)
    ap.add_argument("--end-scale", type=float, default=1.22)
    ap.add_argument("--layer-gain", type=float, default=0.55)
    ap.add_argument("--drift", nargs=2, type=float, default=(0.0, 0.0))
    ap.add_argument("--ease", default="smoothstep", choices=list(EASES))
    ap.add_argument("--flat", action="store_true",
                    help="use flat_zoom() instead of the layered push")
    a = ap.parse_args()
    fn = flat_zoom if a.flat else push_in
    out = fn(a.image, a.dest, a.seconds, n_layers=a.layers,
             start_scale=a.start_scale, end_scale=a.end_scale,
             drift=tuple(a.drift), layer_gain=a.layer_gain, ease=a.ease)
    print(f"[flow_pushin] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
