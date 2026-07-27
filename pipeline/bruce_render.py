#!/usr/bin/env python3
"""bruce_render.py - render all Bruce Lee pieces.

cuts with loop=True render via the true-loop path (extract [t0,t1] once,
stream_loop to beat duration - ledger F12); everything else uses the
proven cut_piece / render_remotion paths.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble            # noqa: E402
import v5_assemble as v5   # noqa: E402

assemble.WORK = v5.WORK
os.chdir(ROOT / "graphics")          # npx remotion resolves here
TMP = v5.WORK / "looptmp"
TMP.mkdir(parents=True, exist_ok=True)

assets = json.loads((v5.MAN / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((v5.MAN / "beats.json").read_text())["beats"]}
order = sorted(assets)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{r.stderr[-1200:]}")


def crop_vf(cb):
    if not cb:
        return ""
    l, t, rr, b = cb
    return f"crop=iw*{1-l-rr:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},"


def loop_piece(bid, a, dur, piece):
    seg = TMP / f"seg_{bid}.mp4"
    vf = (crop_vf(a.get("crop_box")) +
          "scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,fps=30,setsar=1,format=yuv420p")
    run(["ffmpeg", "-ss", f"{a['t0']:.3f}", "-to", f"{a['t1']:.3f}",
         "-i", a["src"], "-vf", vf, "-an", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "19", "-y", str(seg)])
    run(["ffmpeg", "-stream_loop", "-1", "-i", str(seg), "-t",
         f"{dur:.3f}", "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "19", "-r", "30", "-pix_fmt", "yuv420p", "-y",
         str(piece)])


def main():
    for idx, bid in enumerate(order):
        a = assets[bid]
        if a.get("type") == "spanned":
            continue
        piece = v5.WORK / f"p_{idx:03d}_{bid}.mp4"
        if piece.exists() and piece.stat().st_size > 0:
            continue
        b = beats[bid]
        if "span_until" in a:
            dur = round(beats[a["span_until"]]["end"] - b["start"], 3)
        else:
            dur = round(b["end"] - b["start"], 3)
        print(f"render {bid} {a.get('vid', a.get('comp'))}", flush=True)
        if a["type"] == "cut" and a.get("loop") and \
                "exloop" not in a["vid"]:
            loop_piece(bid, a, dur, piece)
        elif a["type"] == "cut":
            v5.cut_piece(a, dur, piece)
        else:
            assemble.render_remotion(a["comp"], dict(a["props"]), piece,
                                     dur, alpha=False)
        if not piece.exists() or piece.stat().st_size == 0:
            raise SystemExit(f"FAILED {bid}")
    print("[OK] all pieces rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
