#!/usr/bin/env python3
"""statham_fix_v5b.py - round-2 fixes after frame-verifying round 1.

cut_piece EXTENDS a window to the beat duration instead of looping it
(end = max(t1, t0 + dur)), so every "loop" beat bled into the next shot.
This renders true loops: extract [t0, t1] with crop, then stream_loop the
segment to the exact beat duration. Also: crop corrections (BB bug on D2,
BBC bug on xrx), b_086 pushup loop -> trampoline (diving-adjacent), b_093
re-windowed onto the real candid (215-221s, video not still).
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "statham"
WORK = ROOT / "final_video" / "v5_work"
TMP = WORK / "looptmp"
TMP.mkdir(exist_ok=True)

A = json.loads((MAN / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}
order = sorted(A)
HF, T7, D2, XR = ("tf_hfTRYwnoPZU", "tf_-7LyChJmWto", "tf_d2V5ZgSDKFE",
                  "xrxH5n93CzM")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{r.stderr[-1500:]}")


def crop_vf(cb):
    if not cb:
        return ""
    l, t, rr, b = cb
    return (f"crop=iw*{1-l-rr:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},")


def loop_piece(bid, src, t0, t1, crop=None):
    """True loop: cut [t0,t1] once, then stream_loop to beat duration."""
    dur = round(beats[bid]["end"] - beats[bid]["start"], 3)
    seg = TMP / f"seg_{bid}.mp4"
    vf = (crop_vf(crop) +
          "scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,fps=30,setsar=1,format=yuv420p")
    run(["ffmpeg", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}",
         "-i", str(DOS / f"{src}.mp4"), "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-y", str(seg)])
    piece = WORK / f"p_{order.index(bid):03d}_{bid}.mp4"
    run(["ffmpeg", "-stream_loop", "-1", "-i", str(seg),
         "-t", f"{dur:.3f}", "-an", "-c:v", "libx264", "-preset",
         "veryfast", "-crf", "19", "-r", "30", "-pix_fmt", "yuv420p",
         "-y", str(piece)])
    e = {"type": "cut", "src": str(DOS / f"{src}.mp4"), "t0": round(t0, 2),
         "t1": round(t1, 2), "vid": f"{src}@{t0}", "verified": True,
         "loop": True, "manual_loop": True}
    if crop:
        e["crop_box"] = crop
    A[bid] = e
    print(f"[loop] {bid} {src} {t0}-{t1} -> {dur}s")


# ---- true-loop renders (were bleeding into the next shot) ---------------
loop_piece("b_001", HF, 38.05, 43.0, crop=[0.0, 0.16, 0.0, 0.13])
loop_piece("b_002", T7, 21.4, 25.5)
loop_piece("b_040", HF, 27.36, 30.15)
loop_piece("b_041", HF, 126.73, 129.6, crop=[0.0, 0.06, 0.06, 0.14])
loop_piece("b_078", HF, 23.86, 27.2)
loop_piece("b_096", T7, 9.47, 12.7)

# ---- window/crop corrections (normal render path handles these) ---------
A["b_043"]["crop_box"] = [0.19, 0.10, 0.14, 0.04]      # BB bug top-right
A["b_088"]["crop_box"] = [0.10, 0.09, 0.0, 0.0]        # BBC bug top-left
A["b_093"] = {"type": "cut", "src": str(DOS / f"{D2}.mp4"),
              "t0": 215.0, "t1": 221.0, "vid": f"{D2}@215",
              "verified": True, "crop_box": [0.0, 0.10, 0.12, 0.0]}
need = beats["b_086"]["end"] - beats["b_086"]["start"]
A["b_086"] = {"type": "cut",
              "src": str(ROOT / "library/exloops/trampoline.mp4"),
              "t0": 0.0, "t1": round(need + 0.2, 2),
              "vid": "exloop:trampoline", "verified": True, "loop": True}

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)
for bid in ["b_043", "b_086", "b_088", "b_093"]:
    p = WORK / f"p_{order.index(bid):03d}_{bid}.mp4"
    if p.exists():
        p.unlink()
print("[OK] round-2 patch applied; re-run the piece runner for 4 beats")
