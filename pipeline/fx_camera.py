#!/usr/bin/env python3
"""Named camera moves on a single still, driven by its depth map.

Higgsfield sells these as generation presets, charging per second. They are
not generation: they are camera paths through a depth-warped image, so we
build them once and they cost nothing per shot forever. Their real
contribution is the VOCABULARY - a named move is one a shot manifest can ask
for, and "dolly_zoom_in" carries meaning that "zoom=1.2, dz=-0.4" does not.

Everything here is a different path through flow_dibr.warp(). That module
already solved the hard parts: subpixel-accurate remapping (integer rounding
of a crop box reads as judder - measured 1.008px before the fix, 0.031px
after), disocclusion filling, and a headroom check that refuses to render
rather than expose a frame edge.

The one move that is NOT here is `through_object` - a continuous flight from
macro to micro. That needs nested source images, not a camera path, so it
lives with the zoom_through work.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import flow_dibr as dibr

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "graphics/public/fonts/Anton-Regular.ttf"
FPS = dibr.FPS
OUT_W, OUT_H = dibr.OUT_W, dibr.OUT_H
THREADS = "2"


def _ease(t: float) -> float:
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3.0 - 2.0 * t)


def _shake(i: int, seed: int, amp: float) -> tuple[float, float]:
    """Deterministic handheld wobble.

    Summed sines rather than random noise, so a re-render is identical - the
    generation side has no seed and cannot be reproduced, but everything on
    this side must be.
    """
    a = math.sin(i * 0.41 + seed) + 0.5 * math.sin(i * 0.97 + seed * 1.7)
    b = math.cos(i * 0.37 + seed * 2.3) + 0.5 * math.cos(i * 1.13 + seed)
    return a * amp, b * amp


# --------------------------------------------------------------------------
# the move table: each returns (dz, dx, dy, zoom, roll) for a normalised t
# --------------------------------------------------------------------------

def _path(kind: str, t: float, amt: float) -> tuple[float, float, float, float, float]:
    e = _ease(t)
    if kind == "dolly_in":
        return -amt * e, 0.0, 0.0, 1.0 + 0.10 * e, 0.0
    if kind == "dolly_out":
        return amt * e, 0.0, 0.0, 1.10 - 0.10 * e, 0.0
    if kind == "dolly_zoom_in":
        # Vertigo: push the depth field in while the frame scales OUT to
        # cancel the subject's size. The subject holds; the world warps.
        return -amt * 1.6 * e, 0.0, 0.0, 1.14 - 0.12 * e, 0.0
    if kind == "dolly_zoom_out":
        return amt * 1.6 * e, 0.0, 0.0, 1.02 + 0.12 * e, 0.0
    if kind == "crash_zoom_in":
        # Violent: most of the travel in the first third, then it settles.
        k = _ease(min(1.0, t * 2.6))
        return -amt * 0.7 * k, 0.0, 0.0, 1.0 + 0.30 * k, 0.0
    if kind == "crane_up":
        return -amt * 0.3 * e, 0.0, -amt * 2.2 * e, 1.08, 0.0
    if kind == "aerial_pullback":
        return amt * 1.4 * e, 0.0, -amt * 0.8 * e, 1.16 - 0.14 * e, 0.0
    if kind == "arc_left":
        return -amt * 0.5 * e, -amt * 2.4 * e, 0.0, 1.12, 0.0
    if kind == "orbit_360":
        # A pass of a full circle, as far as a single viewpoint allows.
        a = 2.0 * math.pi * e
        return -amt * 0.4, amt * 2.2 * math.sin(a), amt * 0.5 * (1 - math.cos(a)), 1.14, 0.0
    if kind == "dutch_angle":
        return -amt * 0.4 * e, 0.0, 0.0, 1.14, 6.0 * e
    if kind == "handheld":
        return -amt * 0.25 * e, 0.0, 0.0, 1.10, 0.0
    if kind == "static":
        return 0.0, 0.0, 0.0, 1.02, 0.0
    raise ValueError(f"unknown move: {kind}")


MOVES = ("dolly_in", "dolly_out", "dolly_zoom_in", "dolly_zoom_out",
         "crash_zoom_in", "crane_up", "aerial_pullback", "arc_left",
         "orbit_360", "dutch_angle", "handheld", "focus_change",
         "low_shutter", "head_tracking", "static")


def _roll(img: np.ndarray, deg: float) -> np.ndarray:
    if abs(deg) < 1e-6:
        return img
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _face_centre(rgb: np.ndarray) -> tuple[float, float] | None:
    """Centre of the largest face, in fractions of frame. None if no face."""
    try:
        import mediapipe as mp
        with mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.4) as fd:
            res = fd.process(cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR))
        if not res.detections:
            return None
        best = max(res.detections,
                   key=lambda d: d.location_data.relative_bounding_box.width)
        b = best.location_data.relative_bounding_box
        return b.xmin + b.width / 2, b.ymin + b.height / 2
    except Exception:
        return None


def camera_move(image: Path, dest: Path, frames: int, kind: str = "dolly_in",
                *, amount: float = 0.06, label: str | None = None) -> Path:
    """Render one named move. Returns a piece of exactly `frames` frames."""
    if kind not in MOVES:
        raise ValueError(f"unknown move {kind!r}; known: {', '.join(MOVES)}")

    rgb = np.asarray(Image.open(image).convert("RGB").resize(
        (OUT_W, OUT_H), Image.LANCZOS), dtype=np.float32)
    depth = dibr.depth_of(image)
    if depth.shape[:2] != (OUT_H, OUT_W):
        depth = cv2.resize(depth, (OUT_W, OUT_H), interpolation=cv2.INTER_CUBIC)
    order = dibr.sort_order(depth)

    anchor = _face_centre(rgb) if kind == "head_tracking" else None
    work = Path(tempfile.mkdtemp(prefix=f"cam_{kind}_"))
    try:
        fdir = work / "f"
        fdir.mkdir(parents=True, exist_ok=True)
        prev: list[np.ndarray] = []

        for i in range(frames):
            t = i / max(1, frames - 1)

            if kind == "focus_change":
                # Rack focus: the sharp depth plane travels from far to near.
                out = rgb.copy()
                plane = 0.15 + 0.7 * _ease(t)
                soft = cv2.GaussianBlur(rgb, (0, 0), 9)
                m = np.clip(1.0 - np.abs(depth - plane) / 0.22, 0.0, 1.0)
                out = rgb * m[..., None] + soft * (1.0 - m[..., None])
                out = dibr.warp(out, depth, -amount * 0.25 * _ease(t),
                                0.0, 0.0, strength=amount, zoom=1.06,
                                order=order)
            elif kind == "head_tracking":
                # The world moves; his face stays put.
                dz, dx, _, zoom, _ = _path("arc_left", t, amount)
                out = dibr.warp(rgb, depth, dz, dx, 0.0,
                                strength=amount, zoom=zoom, order=order)
                if anchor:
                    ax = (anchor[0] - 0.5) * OUT_W * dx * 2.0
                    M = np.float32([[1, 0, -ax], [0, 1, 0]])
                    out = cv2.warpAffine(out, M, (OUT_W, OUT_H),
                                         flags=cv2.INTER_CUBIC,
                                         borderMode=cv2.BORDER_REPLICATE)
            else:
                dz, dx, dy, zoom, roll = _path(
                    "dolly_in" if kind == "low_shutter" else kind, t, amount)
                if kind == "handheld":
                    sx, sy = _shake(i, 7, amount * 0.35)
                    dx, dy = dx + sx, dy + sy
                out = dibr.warp(rgb, depth, dz, dx, dy,
                                strength=amount, zoom=zoom, order=order)
                if roll:
                    out = _roll(out, roll)

            if kind == "low_shutter":
                # Long exposure: accumulate the trailing frames.
                prev.append(out.copy())
                prev = prev[-5:]
                out = np.mean(prev, axis=0)

            frame = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
            if label:
                _stamp(frame, label)
            frame.save(fdir / f"f{i:05d}.png")

        missing = [i for i in range(frames)
                   if not (fdir / f"f{i:05d}.png").exists()]
        if missing:
            raise RuntimeError(f"{len(missing)} frames missing, first {missing[0]}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
             "-i", str(fdir / "f%05d.png"), "-frames:v", str(frames),
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-threads", THREADS, str(dest)], check=True)
        return dest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _stamp(img: Image.Image, text: str) -> None:
    """Burn the move name in, for the demo reel only."""
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(str(FONT), 46)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.rectangle([54, OUT_H - 130, 54 + w + 44, OUT_H - 130 + h + 40],
                fill=(0, 0, 0, 170))
    d.text((76, OUT_H - 122), text, font=f, fill=(227, 18, 11))
