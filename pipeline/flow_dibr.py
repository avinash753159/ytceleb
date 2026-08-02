#!/usr/bin/env python3
"""Depth-image-based rendering (DIBR): real parallax on a single still.

This replaces `flow_pushin.py`'s depth-band approach, which the owner
rejected for two specific, correct reasons:

  1. "weirdly shakey" - the old move rounded the scale/crop box to whole
     pixels every frame, so the image juddered at sub-pixel level.
  2. "doesn't really have parallax" - three hard depth bands are three flat
     cards. Boundaries read as cardboard cut-outs, and where the plate behind
     a band was starved of pixels they read as smear. Three planes is not
     depth; it is three zooms.

What this module does instead is what DepthFlow does internally, and what
Business Casual describes when they explain their own technique: put the
picture in 3D space and move a virtual camera through it. Concretely, a
*continuous per-pixel* warp driven by a dense depth map - every pixel is
displaced by an amount proportional to its own disparity and the camera's
motion. There are no bands, so there are no band boundaries to give the
trick away, and near pixels genuinely travel further than far ones.

(`pip install depthflow` is not an option on this machine: moderngl and
glcontext ship no wheels for Python 3.14 and want a C++ toolchain plus a
live OpenGL context. The depth model and the warp are the whole of it, so
the warp is implemented here against the depth model parallax.py already
uses.)

How the geometry works
----------------------
Pinhole projection with the principal point at frame centre. A point at
depth Z projects to u = f*X/Z + cx. Treat the normalised depth map as
disparity D (1 = nearest, 0 = farthest). Dolly the camera forward by dz and
translate it by (dx, dy):

    gain(D)  = zoom / (1 - strength*dz*D)
    u' = cx + (u - cx)*gain(D) - strength*dx*D*W
    v' = cy + (v - cy)*gain(D) - strength*dy*D*H

`gain` is the exact perspective magnification of a dolly, not an
approximation of it: near pixels (large D) blow up fast, the far plane
(D = 0) is untouched by the dolly and only feels the global `zoom`. That
difference IS the parallax.

The relation inverts exactly given the disparity of the point *visible at
the destination pixel*, which is why the render forward-scatters disparity
into the destination frame with a z-buffer first (nearest wins, so near
surfaces correctly occlude far ones), resolves the empty cells, then builds
a float backward map and hands it to `cv2.remap`. Coordinates stay float32
from end to end and the resampler is INTER_CUBIC - nothing is ever rounded
to a whole pixel, which is the defect that made the old move shake.

Empty destination cells come in two kinds that want opposite answers, and
conflating them costs real parallax: ~25% of the grid is left empty by
magnification alone and must take the NEAREST neighbouring surface, while
the ~0.2% that is genuinely revealed background must take the FARTHEST.
See `_close_sampling_gaps`.

Where it fails, honestly
------------------------
DIBR's characteristic failure is *stretching around depth discontinuities*.
Where a near surface pulls away from the background it opens a hole that no
pixel in the source can fill; the fill here is a background-disparity
stretch (see `_fill_disparity_holes`), so the hole is covered with smeared
background rather than black. Small holes are invisible, large ones look
like the background is made of chewing gum. `strength` is what controls hole
size, and 0.05-0.08 is the usable range at 1080p. Push it past ~0.12 and the
smear becomes the thing the eye lands on. Turning `strength` up does not buy
more depth; it buys more artefact.

Depth models also still guess. Hair, glass, reflections and heavy motion
blur produce depth edges that do not sit on picture edges, and the warp will
faithfully render that mistake. `parallax.assess()` remains the screening
gate for whether a still deserves this treatment at all.
"""

from __future__ import annotations

import hashlib
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

# CPU depth estimation is a torch forward pass per image - slow, and a film
# calls dolly_in() ~100 times. Keyed on source bytes, not path, so a renamed
# or copied still still hits the cache.
DEPTH_CACHE = ROOT / "work" / "dibr_depth_cache"

# A constant sliver of over-fill held for the whole move on top of the
# caller's `zoom` ramp. The dolly alone can never expose an edge (it only
# pulls the backward map inward), but this guarantees headroom at t=0 for
# lateral drift and leaves the depth-edge fill somewhere to take pixels from.
OVERFILL = 1.02

# Disparity written into destination cells that no source pixel reached.
# Large and positive so a min-filter (cv2.erode) ignores it and picks the
# farthest real neighbour instead - background-first, which is what should
# be revealed behind a near object that moved.
_SENTINEL = np.float32(1.0e6)

_GRIDS: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}


# ------------------------------------------------------------------ easing
#
# "Eased" here means specifically: zero velocity at BOTH ends. A camera that
# starts or stops at constant speed reads as a cut with a zoom stapled on.

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

    Frame count is contractual in this pipeline - a shot one frame short is
    a build error, not a rounding footnote - so render, tests and CLI all go
    through this one function.
    """
    return round(seconds * FPS)


# ------------------------------------------------------------------- depth

def _depth_cache_key(image: Path) -> str:
    return hashlib.sha1(Path(image).read_bytes()).hexdigest()[:20]


def depth_of(image: Path) -> np.ndarray:
    """Normalised depth for `image`, 0..1 with 1 = nearest, cached to disk.

    Shape is always (OUT_H, OUT_W) because the depth is estimated on the
    same cover-cropped frame the warp renders, so depth and picture are
    pixel-aligned by construction.
    """
    image = Path(image)
    cache = DEPTH_CACHE / f"{_depth_cache_key(image)}_{OUT_W}x{OUT_H}.npy"
    if cache.exists():
        d = np.load(cache)
        if d.shape == (OUT_H, OUT_W):
            return d.astype(np.float32)

    bgr = parallax.load_cover(image, OUT_W, OUT_H)
    # parallax.depth_map already normalises to 0..1 (1 = nearest) and
    # bilateral-filters so depth edges follow surfaces, not model noise.
    d = parallax.depth_map(bgr).astype(np.float32)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, d)
    return d


# ------------------------------------------------------------------- warp

def _grid(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    key = (h, w)
    g = _GRIDS.get(key)
    if g is None:
        yy, xx = np.mgrid[0:h, 0:w]
        g = (xx.astype(np.float32), yy.astype(np.float32))
        _GRIDS[key] = g
    return g


def radial_gain(depth, dz: float, strength: float, zoom: float = 1.0):
    """Per-pixel magnification of a dolly of `dz` at disparity `depth`.

    This is the whole parallax model in one line. It is exact perspective,
    not a linearisation: a point at depth Z seen after the camera advances
    by dz*Z_unit magnifies by 1/(1 - dz*D). Accepts a scalar or an array.

    strength=0 collapses it to `zoom` for every depth - i.e. a flat zoom,
    which is exactly the control the parallax has to beat.
    """
    denom = 1.0 - float(strength) * float(dz) * np.asarray(depth,
                                                           dtype=np.float32)
    # Guard only; callers keep strength*dz well under 1 so this never bites.
    denom = np.maximum(denom, np.float32(0.05))
    return (np.float32(zoom) / denom).astype(np.float32)


def backward_maps(depth_dest: np.ndarray, dz: float, dx: float = 0.0,
                  dy: float = 0.0, strength: float = 0.06,
                  zoom: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """float32 (map_x, map_y) taking each DESTINATION pixel to its source.

    `depth_dest` is the disparity of the point *visible at* each destination
    pixel (see `_scatter_disparity`). Given that, the forward projection in
    the module docstring inverts exactly.

    Both maps are float32 and deliberately non-integral: sub-pixel accuracy
    all the way into the resampler is what removes the judder the owner saw
    in the band-splitting version.
    """
    h, w = depth_dest.shape[:2]
    xx, yy = _grid(h, w)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    gain = radial_gain(depth_dest, dz, strength, zoom)
    s = np.float32(strength)
    mx = cx + (xx - np.float32(cx) + s * np.float32(dx) * depth_dest * w) / gain
    my = cy + (yy - np.float32(cy) + s * np.float32(dy) * depth_dest * h) / gain
    return np.ascontiguousarray(mx, np.float32), \
        np.ascontiguousarray(my, np.float32)


def sort_order(depth: np.ndarray) -> np.ndarray:
    """Flat indices of `depth` sorted far-to-near.

    The z-buffer is implemented as a plain scatter assignment in this order,
    so nearer pixels overwrite farther ones and occlusion comes out right.
    Depth does not change across the frames of a shot, so `dolly_in`
    computes this once instead of 144 times.
    """
    return np.argsort(depth, axis=None, kind="stable")


def _scatter_disparity(depth: np.ndarray, order: np.ndarray, dz: float,
                       dx: float, dy: float, strength: float,
                       zoom: float) -> tuple[np.ndarray, np.ndarray]:
    """Forward-project disparity into the destination frame with a z-buffer.

    Returns (destination disparity, hole mask). Cells no source pixel
    reached are disocclusions - background that was hidden behind something
    nearer and is now being revealed.
    """
    h, w = depth.shape[:2]
    xx, yy = _grid(h, w)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0

    d = depth.reshape(-1)[order]
    u = xx.reshape(-1)[order]
    v = yy.reshape(-1)[order]

    gain = radial_gain(d, dz, strength, zoom)
    s = np.float32(strength)
    up = np.float32(cx) + (u - np.float32(cx)) * gain - s * np.float32(dx) * d * w
    vp = np.float32(cy) + (v - np.float32(cy)) * gain - s * np.float32(dy) * d * h

    iu = np.rint(up).astype(np.int32)
    iv = np.rint(vp).astype(np.int32)
    ok = (iu >= 0) & (iu < w) & (iv >= 0) & (iv < h)

    dst = np.full(h * w, np.float32(-1.0), np.float32)
    flat = iv[ok].astype(np.int64) * w + iu[ok].astype(np.int64)
    # `order` is far-to-near, so on collision the last (nearest) write wins.
    dst[flat] = d[ok]
    dst = dst.reshape(h, w)
    return dst, dst < 0.0


# A hole cell counts as a mere sampling gap - not a disocclusion - when most
# of its 8-neighbourhood landed. Magnification gaps are isolated single cells
# (5-8 valid neighbours); a real disocclusion is a band several pixels wide,
# whose cells have at most 3. Nothing in between occurs in practice.
_GAP_NEIGHBOURS = 5


def _close_sampling_gaps(dst: np.ndarray,
                         holes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fill the lattice of empty cells that magnification alone creates.

    A frame zoomed by 1.12 spreads each source pixel over ~1.25 destination
    cells, so ~25% of the destination grid receives no source pixel even
    where nothing is occluded at all. Those are resampling gaps, not revealed
    background, and treating them as disocclusions is a real defect: filling
    a quarter of the frame with the FARTHEST neighbouring disparity drags the
    whole depth field toward the background and measurably flattens the
    parallax the module exists to produce.

    They are closed with a max-filter instead - nearest surface wins, which
    is the same z-buffer rule the scatter itself used, so a cell straddled by
    a magnified near surface gets that surface rather than what is behind it.

    Returns (disparity, mask of cells that are genuine disocclusions).
    """
    cur = dst
    remaining = holes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    for _ in range(3):
        valid = (~remaining).astype(np.float32)
        # Count of valid cells among the 8 neighbours.
        neighbours = cv2.boxFilter(valid, -1, (3, 3), normalize=False) - valid
        isolated = remaining & (neighbours >= _GAP_NEIGHBOURS)
        if not isolated.any():
            break
        if cur is dst:
            cur = dst.copy()
            remaining = holes.copy()
        dilated = cv2.dilate(cur, kernel)
        cur[isolated] = dilated[isolated]
        remaining &= ~isolated
    return cur, remaining


def _fill_disparity_holes(dst: np.ndarray,
                          holes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Resolve every empty destination cell. Returns (disparity, residual).

    Two stages, because the two kinds of empty cell want opposite answers:
    resampling gaps want the NEAREST neighbouring surface (see
    `_close_sampling_gaps`), true disocclusions want the FARTHEST.

    Assigning a disocclusion the background's disparity makes the backward
    map sample the background plate just behind the gap - i.e. a stretch of
    background across the gap. That is the classic DIBR fill: cheap, never
    black, and invisible while the gap is thin. It is also exactly where the
    smear artefact comes from when the gap is wide, which is the honest cost
    of turning `strength` up.

    A min-filter (cv2.erode) over a widening rectangular window does the
    background propagation in a handful of vectorised passes rather than
    dozens of single-pixel dilations.
    """
    if not holes.any():
        return dst, np.zeros(dst.shape, np.uint8)

    filled, remaining = _close_sampling_gaps(dst, holes)
    if not remaining.any():
        return filled, np.zeros(dst.shape, np.uint8)

    filled = filled.copy()
    filled[remaining] = _SENTINEL
    for k in (7, 21, 61, 181):
        er = cv2.erode(filled,
                       cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
        got = remaining & (er < _SENTINEL * 0.5)
        filled[got] = er[got]
        remaining &= ~got
        if not remaining.any():
            break

    if remaining.any():
        # Nothing valid within 90px in any direction. Cannot happen for the
        # strengths this module ships, but a defined disparity everywhere is
        # what guarantees every destination pixel has a real source, so fall
        # back to the frame's mean depth and let warp() inpaint the pixels.
        valid = dst[~holes]
        filled[remaining] = np.float32(valid.mean()) if valid.size else \
            np.float32(0.0)

    return filled, (remaining.astype(np.uint8) * 255)


def _smooth_disparity(d: np.ndarray) -> np.ndarray:
    """Kill scatter speckle, then soften.

    The scatter leaves single-cell noise wherever two source pixels contend
    for one destination cell; a 3x3 median removes it without rounding the
    depth edges off. The small Gaussian that follows turns each remaining
    depth cliff into a 2-3px ramp, which is what stops the warp cutting a
    hard silhouette - the cardboard-cut-out look the band version had.
    """
    d = cv2.medianBlur(d, 3)
    return cv2.GaussianBlur(d, (0, 0), 1.0)


def warp(rgb: np.ndarray, depth: np.ndarray, dz: float, dx: float = 0.0,
         dy: float = 0.0, strength: float = 0.06, zoom: float = 1.0,
         order: np.ndarray | None = None) -> np.ndarray:
    """One DIBR view of `rgb` from a camera dollied `dz` and shifted (dx, dy).

    `depth` is 0..1 with 1 = nearest and must match `rgb`'s shape.
    `dz`, `dx`, `dy` are normalised camera motion (the render drives dz from
    0 to 1 across a shot); `strength` scales the whole displacement field and
    is the only knob that trades depth against smear - see the module
    docstring. `zoom` is an optional global magnification applied in the same
    resample, so combining the parallax with a push-in costs no extra
    resampling pass and therefore no extra softening.

    strength=0 with zoom=1 is the identity.

    `order` is an optional precomputed `sort_order(depth)`; passing it lets a
    render skip a 2M-element argsort on every frame.
    """
    if rgb.shape[:2] != depth.shape[:2]:
        raise ValueError(f"rgb {rgb.shape[:2]} and depth {depth.shape[:2]} "
                         f"must be the same size")
    depth = depth.astype(np.float32, copy=False)
    if order is None:
        order = sort_order(depth)

    dst, holes = _scatter_disparity(depth, order, dz, dx, dy, strength, zoom)
    dst, residual = _fill_disparity_holes(dst, holes)
    dst = _smooth_disparity(dst)

    mx, my = backward_maps(dst, dz, dx, dy, strength, zoom)
    out = cv2.remap(rgb, mx, my, interpolation=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE)
    if residual.any():
        # Backstop only. A hole must never reach the screen as black.
        out = cv2.inpaint(out, residual, 3, cv2.INPAINT_TELEA)
    return out


# ----------------------------------------------------------------- encoding

def _assert_frames_complete(framedir: Path, n_frames: int) -> None:
    """Fail loudly on any gap. ffmpeg's image2 demuxer stops dead at the
    first missing index in a %06d sequence, which would otherwise hand back
    a short video instead of an error."""
    for i in range(n_frames):
        p = Path(framedir) / f"{i:06d}.png"
        if not p.exists():
            raise FileNotFoundError(
                f"frame {i}/{n_frames} missing ({p}) - refusing to encode a "
                f"video the image2 demuxer would silently truncate")


def _encode(framedir: Path, n_frames: int, dest: Path) -> Path:
    _assert_frames_complete(framedir, n_frames)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-i", str(Path(framedir) / "%06d.png"),
        "-frames:v", str(n_frames),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        # 20 cores on this box and ffmpeg takes all of them by default,
        # starving the ~100 other shots a film renders alongside this one.
        "-threads", "2",
        str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + " ".join(cmd[:20]) + "\n"
                           + (r.stderr or "")[-2000:])
    return dest


# ------------------------------------------------------------------- render

def check_drift_fits(zoom: float, drift: tuple[float, float],
                     strength: float, ease_fn) -> None:
    """Raise if lateral drift could pull an edge into frame mid-move.

    The dolly can never expose an edge (it only pulls the backward map
    toward centre) but a lateral shift can, and it grows on the same ease as
    the zoom margin that has to contain it. Checked on a dense sample of the
    ease rather than at the endpoints, because either one alone can pass
    while a middle frame fails.
    """
    if not drift[0] and not drift[1]:
        return
    for i in range(101):
        e = ease_fn(i / 100)
        z = OVERFILL * (1.0 + (zoom - 1.0) * e)
        margin = (1.0 - 1.0 / z) / 2.0
        need = strength * max(abs(drift[0]), abs(drift[1])) * e
        if need > margin:
            raise ValueError(
                f"drift={drift} with strength={strength} needs {need:.4f} of "
                f"the frame at ease={e:.2f} but zoom={zoom} only leaves "
                f"{margin:.4f} - raise zoom or lower drift, an exposed edge "
                f"is a black bar on screen")


def dolly_in(image: Path, dest: Path, seconds: float, *,
             strength: float = 0.06, zoom: float = 1.10,
             drift: tuple[float, float] = (0.0, 0.0),
             ease: str = "smoothstep") -> Path:
    """Render a `seconds`-long DIBR push-in from a still. Returns `dest`.

    The virtual camera advances from dz=0 to dz=1 on the chosen ease while a
    global zoom ramps 1.0 -> `zoom` (times a constant OVERFILL sliver), both
    resolved in a single float remap per frame. Near pixels travel further
    than far pixels for the whole move; that is the parallax. Exactly
    round(seconds*FPS) frames are written and every one is verified on disk
    before ffmpeg is allowed near them.

    strength=0.0 renders the control: an eased zoom with no parallax at all.
    """
    if ease not in EASES:
        raise ValueError(f"unknown ease {ease!r}, want one of {list(EASES)}")
    if zoom < 1.0:
        raise ValueError(f"zoom={zoom} < 1.0 would shrink the plate and "
                         f"expose an edge")
    if strength < 0.0:
        raise ValueError(f"strength={strength} must be >= 0")
    ease_fn = EASES[ease]
    check_drift_fits(zoom, drift, strength, ease_fn)

    image = Path(image)
    rgb = parallax.load_cover(image, OUT_W, OUT_H)
    depth = depth_of(image)
    order = sort_order(depth)

    n_frames = frame_count(seconds)
    if n_frames < 1:
        raise ValueError(f"seconds={seconds} rounds to {n_frames} frames")

    with tempfile.TemporaryDirectory(prefix="dibr_") as raw_tmp:
        tmp = Path(raw_tmp)
        for i in range(n_frames):
            t = i / (n_frames - 1) if n_frames > 1 else 1.0
            e = ease_fn(t)
            frame = warp(rgb, depth, dz=e, dx=drift[0] * e, dy=drift[1] * e,
                         strength=strength,
                         zoom=OVERFILL * (1.0 + (zoom - 1.0) * e),
                         order=order)
            cv2.imwrite(str(tmp / f"{i:06d}.png"), frame,
                        [cv2.IMWRITE_PNG_COMPRESSION, 1])
        return _encode(tmp, n_frames, Path(dest))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="DIBR push-in on a still")
    ap.add_argument("image")
    ap.add_argument("dest")
    ap.add_argument("seconds", type=float)
    ap.add_argument("--strength", type=float, default=0.06)
    ap.add_argument("--zoom", type=float, default=1.10)
    ap.add_argument("--drift", nargs=2, type=float, default=(0.0, 0.0))
    ap.add_argument("--ease", default="smoothstep", choices=list(EASES))
    a = ap.parse_args()
    try:
        out = dolly_in(a.image, a.dest, a.seconds, strength=a.strength,
                       zoom=a.zoom, drift=tuple(a.drift), ease=a.ease)
    except Exception as e:  # noqa: BLE001
        print(f"[flow_dibr] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"[flow_dibr] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
