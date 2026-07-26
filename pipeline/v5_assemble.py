#!/usr/bin/env python3
"""v5_assemble.py - render RYAN_REYNOLDS_V5 from assets_v5.json.

  cut     -> ffmpeg exact [t0,t1] cut from the full dossier file (clamped to
             the beat duration, video-start-safe), 1920x1080/30, silent
  v5card  -> full-screen Remotion render (h264, exact beat duration)
  library -> reuse the V4 piece builder (judge-verified assets)

Concat re-encode + narration mux, same proven tail as V2-V4.
Run:  py -3.12 pipeline/v5_assemble.py [--only b_004]
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble  # noqa: E402  (reuses run/render_remotion/clip_piece/etc)

MAN = ROOT / "manifest"
WORK = ROOT / "final_video" / "v5_work"
OUT = ROOT / "final_video"
FPS = 30


def cut_piece(a, dur, dest):
    """Exact cut, resilient: clamp into the file's real video range and pad
    by looping if the planned window is shorter than the beat."""
    src = a["src"]
    vs = assemble._video_start(src)
    t0 = max(float(a["t0"]), vs + 0.05)
    asset = {"src": src, "start": t0, "end": max(float(a["t1"]), t0 + dur),
             "id": f"v5cut_{a['vid']}", "crop_box": a.get("crop_box")}
    return assemble.clip_piece(asset, dur, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    assemble.WORK = WORK          # route V4 helper output into v5_work
    assets5 = json.loads((MAN / "assets_v5.json").read_text())
    v4_plan = {p["beat_id"]: p for p in
               json.loads((MAN / "plan.json").read_text())["plan"]}
    v4_assets = json.loads((MAN / "assets.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((MAN / "beats.json").read_text())["beats"]}
    cfg = json.loads((ROOT / "config.json").read_text())
    voiceover = ROOT / f"voiceover_{cfg.get('slug', 'ryan_reynolds')}.mp3"

    order = sorted(assets5) if not args.only else [args.only]
    pieces = []
    for idx, bid in enumerate(order):
        a5 = assets5[bid]
        b = beats[bid]
        if a5.get("type") == "spanned":
            print(f"  [{idx + 1}/{len(order)}] {bid} spanned", flush=True)
            pieces.append(None)
            continue
        if "span_until" in a5:
            dur = round(beats[a5["span_until"]]["end"] - b["start"], 3)
        else:
            dur = round(b["end"] - b["start"], 3)
        piece = WORK / f"p_{idx:03d}_{bid}.mp4"
        if not piece.exists():
            if a5["type"] == "cut":
                cut_piece(a5, dur, piece)
            elif a5["type"] == "v5card":
                assemble.render_remotion(a5["comp"], dict(a5["props"]),
                                        piece, dur, alpha=False)
            else:  # library - reuse V4 builder
                assemble.build_piece(v4_plan[bid], v4_assets[bid], b, idx,
                                     v4_assets)
                # V4 builder writes piece_{idx:03d}_{bid}.mp4 under WORK
                v4p = WORK / f"piece_{idx:03d}_{bid}.mp4"
                if v4p.exists():
                    v4p.replace(piece)
        pieces.append(piece)
        print(f"  [{idx + 1}/{len(order)}] {bid} {a5['type']}"
              f"{':' + a5.get('comp', '') if a5['type'] == 'v5card' else ''}",
              flush=True)
    if args.only:
        print(f"[OK] {pieces[0]}")
        return 0

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces if p is not None),
                   encoding="utf-8")
    silent = WORK / "v5_silent.mp4"
    assemble.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(lst),
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                  "-pix_fmt", "yuv420p", "-r", str(FPS), "-y", str(silent)],
                 timeout=3600)
    final = OUT / "RYAN_REYNOLDS_V5.mp4"
    assemble.run(["ffmpeg", "-i", str(silent), "-i", str(voiceover),
                  "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                  "-c:a", "aac", "-b:a", "192k", "-y", str(final)],
                 timeout=1800)
    print(f"[OK] {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
