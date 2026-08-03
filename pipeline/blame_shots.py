#!/usr/bin/env python3
"""Which clip file produced a given shot in the finished cut?

The review flags shot numbers; the allow-list holds file names; nothing
connects them, because the choice happens inside the builder's registry at
render time and the render box has been destroyed.

So match on pixels. Every candidate clip already has four sampled frames on
disk from the screening pass (work/broll7_frames/<stem>/*.jpg). Take the same
frame out of the rendered MP4, dHash both, and the clip whose frames are
closest is the one that was used. Grade and push shift the hash a little, so
this reports the distance and lets a human see whether the match is credible
rather than asserting it.

Usage:  py -3.12 pipeline/blame_shots.py 6 7 8 45 80 81
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

MP4 = ROOT / "final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V9.mp4"
FRAMES = ROOT / "work/broll7_frames"
TMP = ROOT / "work/blame"


def dhash(path: Path, size: int = 16) -> np.ndarray | None:
    try:
        im = Image.open(path).convert("L").resize((size + 1, size),
                                                  Image.LANCZOS)
    except Exception:                                            # noqa: BLE001
        return None
    a = np.asarray(im, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def shot_frame(t: float, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(MP4),
         "-frames:v", "1", "-vf", "scale=440:-2", "-y", str(dst)],
        capture_output=True, timeout=120)
    return dst


def main() -> int:
    import mrbeast_picture_v9 as M
    wanted = [int(a) for a in sys.argv[1:]]
    if not wanted:
        print(__doc__)
        return 1
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(encoding="utf-8"))
    shots = M.allocate(edl, M.fx.probe_dur(M.AUDIO))
    allow = json.loads((ROOT / "manifest/broll_allow.json")
                       .read_text(encoding="utf-8"))

    # every candidate frame, hashed once
    cand: dict[str, list] = {}
    for group, items in allow.items():
        for it in items:
            stem = Path(it["file"]).stem
            d = FRAMES / stem
            if not d.exists():
                continue
            hs = [h for h in (dhash(p) for p in sorted(d.glob("*.jpg")))
                  if h is not None]
            if hs:
                cand[it["file"]] = hs

    for n in wanted:
        if n >= len(shots):
            print(f"#{n}: out of range")
            continue
        s = shots[n]
        t = s["prog_start"] + s["dur"] / 2
        f = shot_frame(t, TMP / f"{n:03d}.jpg")
        h = dhash(f)
        if h is None:
            print(f"#{n}: could not read frame")
            continue
        best = sorted(
            ((int((h != c).sum()), fn) for fn, hs in cand.items()
             for c in hs), key=lambda x: x[0])[:3]
        spec = s["spec"]
        print(f"#{n:>3} {t:7.2f}s span {str(s['span']):>4} "
              f"{spec[0]}:{spec[1] if len(spec) > 1 else ''}")
        for dist, fn in best:
            mark = "  <-- likely" if dist <= 40 else ""
            print(f"      d={dist:>3}  {fn}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
