#!/usr/bin/env python3
"""
render_section.py - render a contiguous beat range to a preview clip.
Renders each beat's piece, concats, muxes the matching narration slice.

Usage: py -3.12 pipeline/render_section.py b_000 b_022 s01_03_preview
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble  # noqa: E402

WORK = ROOT / "final_video" / "v2_work"
OUT = ROOT / "final_video"


def main():
    a0, a1, name = sys.argv[1], sys.argv[2], sys.argv[3]
    plan = {p["beat_id"]: p for p in
            json.loads((ROOT / "manifest" / "plan.json").read_text())["plan"]}
    assets = json.loads((ROOT / "manifest" / "assets.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((ROOT / "manifest" / "beats.json").read_text())["beats"]}
    n0, n1 = int(a0.split("_")[1]), int(a1.split("_")[1])
    order = [f"b_{i:03d}" for i in range(n0, n1 + 1)]

    pieces = []
    for idx, bid in enumerate(order):
        piece = assemble.build_piece(plan[bid], assets[bid], beats[bid],
                                     idx, assets)
        if plan[bid].get("overlay_stat") and assets[bid]["treatment"] in (
                "still_pushin", "motion_broll", "exercise_demo"):
            dur = round(beats[bid]["end"] - beats[bid]["start"], 3)
            webm = assemble.render_remotion(
                "StatCard", {"value": plan[bid]["overlay_stat"]["value"],
                             "label": plan[bid]["overlay_stat"]["label"],
                             "side": assemble.face_side(piece)},
                WORK / f"ovs_{bid}.webm", min(dur, 3.0), alpha=True)
            piece2 = WORK / f"piece_{idx:03d}_{bid}_s.mp4"
            if not piece2.exists():
                assemble.composite(piece, webm, piece2)
            piece = piece2
        pieces.append(piece)
        print(f"  [{idx+1}/{len(order)}] {bid}", flush=True)

    lst = WORK / f"concat_{name}.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    silent = WORK / f"{name}_silent.mp4"
    assemble.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(lst),
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                  "-pix_fmt", "yuv420p", "-r", str(assemble.FPS),
                  "-y", str(silent)], timeout=1800)

    t0 = beats[order[0]]["start"]
    t1 = beats[order[-1]]["end"]
    cfg = json.loads((ROOT / "config.json").read_text())
    vo = ROOT / f"voiceover_{cfg.get('slug', 'ryan_reynolds')}.mp3"
    final = OUT / f"{name}.mp4"
    assemble.run(["ffmpeg", "-i", str(silent), "-ss", f"{t0:.2f}",
                  "-to", f"{t1:.2f}", "-i", str(vo), "-map", "0:v:0",
                  "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                  "-b:a", "192k", "-shortest", "-y", str(final)], timeout=1800)
    print(f"[OK] {final} ({t1-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
