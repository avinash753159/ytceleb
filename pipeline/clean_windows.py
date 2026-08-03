#!/usr/bin/env python3
"""Reject B-roll windows that contain on-screen text or graphics.

The V6 first cut pulled windows by time offset with no idea what was in the
frame, and shipped third-party burned-in captions ("who's gonna puke
first?"), watermarks (www.Bandicam.com), location cards (BYRON BAY,
AUSTRALIA), workout overlays (30 SECONDS ON) and channel logos.

This samples frames inside a candidate window and OCRs the bands where
burned-in text actually lives - lower third, upper third - and rejects the
window if it finds any. Verdicts are cached to disk because the same windows
get re-tested across rebuilds.

Text belonging to the FILM (our own credit slate) is added after this runs,
so it can never trip the detector.
"""

from __future__ import annotations

import os

# MUST be set before onnxruntime/numpy load. onnxruntime defaults to using
# every core for intra-op parallelism, so N worker processes each spawn ~20
# threads on a 20-core machine - 160 threads thrashing over 20 cores, which
# measured SLOWER than running one window at a time. One thread per worker
# process; the parallelism comes from the process pool.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "ORT_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "work" / "clean_windows_cache.json"

# Minimum OCR confidence to count as real text. Below this it is usually
# texture (gym equipment edges, clothing seams) misread as characters.
MIN_CONF = 0.55
MIN_CHARS = 3

_ocr = None
_cache: dict | None = None


def ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        try:
            _ocr = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
        except TypeError:          # older signature
            _ocr = RapidOCR()
    return _ocr


def cache() -> dict:
    global _cache
    if _cache is None:
        _cache = (json.loads(CACHE.read_text(encoding="utf-8"))
                  if CACHE.exists() else {})
    return _cache


def save_cache():
    if _cache is not None:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(_cache), encoding="utf-8")


def _frames(path: Path, t0: float, dur: float, n=3):
    """Sample n frames spread across the window, as BGR arrays."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(n):
            t = t0 + dur * (i + 0.5) / n
            f = Path(td) / f"{i}.jpg"
            r = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                 "-vf", "scale=1280:-2", str(f)],
                capture_output=True, timeout=180)
            if r.returncode == 0 and f.exists() and f.stat().st_size:
                img = cv2.imread(str(f))
                if img is not None:
                    out.append(img)
    return out


import re

# Studio backdrops and channel branding are unavoidable in interview
# footage and are already handled by crediting the source - rejecting them
# would eliminate essentially every usable frame. What must be rejected is
# text the OTHER production added on top: captions, overlay graphics,
# location cards and screen-recorder watermarks.
WATERMARK = re.compile(r"www\.|\.com|\.net|bandicam|screen ?rec|filmora|"
                       r"capcut|subscribe", re.I)


def _band_text(img: np.ndarray, y0: float, y1: float) -> list[str]:
    h = img.shape[0]
    band = img[int(h * y0):int(h * y1)]
    out = []
    try:
        res, _ = ocr()(band)
    except Exception:
        return out
    for item in (res or []):
        if len(item) < 3:                    # RapidOCR: [box, text, conf]
            continue
        txt, conf = str(item[1]).strip(), float(item[2])
        if conf >= MIN_CONF and len(txt) >= MIN_CHARS and any(
                c.isalnum() for c in txt):
            out.append(txt)
    return out


SPEAKER = re.compile(r"^[a-z][a-z ]{1,12}:", re.I)   # "eric:", "alex:"


def _is_overlay(txt: str) -> bool:
    """Distinguish another production's overlay from incidental branding.

    Measured against real frames from these sources:
      REJECT  "eric: there's his entire resume"   burned-in caption
              "30 SECONDS ON"  "130 CALORIES BURNED"  overlay graphics
              "BYRON BAY, AUSTRALIA"                  location card
              "www.Bandicam.com"                      watermark
      ALLOW   "Beast"                MrBeast's own channel branding
              "MRBEAST" / "MNBEAST"  Feastables labels on the table
              "THE ROGAN"            studio backdrop

    The separator is sentence-likeness: overlays are phrases, incidental
    branding is a single word. Rejecting single words killed every usable
    Colin-and-Samir and archive window in testing.
    """
    if WATERMARK.search(txt):
        return True
    if SPEAKER.match(txt):
        return True
    words = [w for w in re.split(r"\s+", txt.strip()) if len(w) > 1]
    return len(words) >= 2 and len(txt) >= 8


def _text_in(img: np.ndarray) -> list[str]:
    """Return only text indicating ANOTHER production's overlay."""
    found = [t for t in _band_text(img, 0.58, 1.0) if _is_overlay(t)]
    found += [t for t in _band_text(img, 0.0, 0.20)
              if WATERMARK.search(t) or SPEAKER.match(t)]
    return found


def is_clean(path: Path, t0: float, dur: float, frames=3) -> tuple[bool, str]:
    """True when no burned-in text was detected anywhere in the window."""
    key = f"{path.name}|{t0:.2f}|{dur:.2f}"
    c = cache()
    if key in c:
        return bool(c[key][0]), c[key][1]

    hits: list[str] = []
    for img in _frames(path, t0, dur, frames):
        hits += _text_in(img)
    ok = not hits
    reason = "" if ok else "text: " + " / ".join(sorted(set(hits))[:4])
    c[key] = [ok, reason]
    return ok, reason


def _check_one(args):
    """Top-level so it can be sent to a worker PROCESS (must be picklable)."""
    path, t0, dur = args
    ok, why = is_clean(Path(path), t0, dur, frames=2)
    return t0, ok, why


def candidates(path: Path, dur: float, count: int) -> list[float]:
    """Evenly spread candidate window starts inside a file."""
    total = _duration(path)
    lo, hi = 2.0, total - dur - 1.0
    if hi <= lo:
        return []
    n = min(int(count * 1.8) + 6, 90)
    return [lo + (hi - lo) * i / max(1, n - 1) for i in range(n)]


def scan_many(jobs: list[tuple[Path, float, float]], workers: int = 8):
    """OCR many windows across many files using ONE process pool.

    Worker startup plus loading the OCR model costs a few seconds per
    process. Creating a pool per source paid that seven times over and left
    the measured speedup at 1.6x; paying it once amortises it across the
    whole scan.
    """
    from concurrent.futures import ProcessPoolExecutor

    c = cache()
    todo = [(str(p), t, d) for p, t, d in jobs
            if f"{p.name}|{t:.2f}|{d:.2f}" not in c]
    if not todo:
        return
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for (ps, t, d), (t0, ok, why) in zip(
                todo, ex.map(_check_one, todo, chunksize=4)):
            c[f"{Path(ps).name}|{t0:.2f}|{d:.2f}"] = [ok, why]


def verdicts(path: Path, cands: list[float], dur: float) -> list[float]:
    c = cache()
    return [t for t in cands
            if c.get(f"{path.name}|{t:.2f}|{dur:.2f}", [False])[0]]


def clean_pool(path: Path, dur: float, count: int, workers: int = 8,
               span: tuple[float, float] | None = None) -> list[float]:
    """Return start times of windows in `path` with no overlay text.

    Uses PROCESSES, not threads. RapidOCR/onnxruntime does not release the
    GIL, so a thread pool serialised the work and added overhead - measured
    at ~8s per window versus 4.6s sequential. Processes give real
    concurrency at the cost of loading the model once per worker.
    """
    from concurrent.futures import ProcessPoolExecutor

    total = _duration(path)
    lo, hi = span or (2.0, max(3.0, total - dur - 2.0))
    hi = min(hi, total - dur - 1.0)
    if hi <= lo:
        return []

    # Only as many candidates as needed plus headroom for rejections.
    n = min(int(count * 1.8) + 6, 90)
    cands = [lo + (hi - lo) * i / max(1, n - 1) for i in range(n)]

    # Anything already decided is free; only scan the rest.
    c = cache()
    todo = [t for t in cands
            if f"{path.name}|{t:.2f}|{dur:.2f}" not in c]
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for t0, ok, why in ex.map(
                    _check_one, [(str(path), t, dur) for t in todo],
                    chunksize=2):
                c[f"{path.name}|{t0:.2f}|{dur:.2f}"] = [ok, why]

    return [t for t in cands
            if c.get(f"{path.name}|{t:.2f}|{dur:.2f}", [False])[0]]


def _duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=120)
    return float(r.stdout.strip())


if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1])
    t0, dur = float(sys.argv[2]), float(sys.argv[3])
    ok, why = is_clean(p, t0, dur)
    save_cache()
    print(f"{'CLEAN' if ok else 'REJECT'}  {p.name} {t0}+{dur}  {why}")
