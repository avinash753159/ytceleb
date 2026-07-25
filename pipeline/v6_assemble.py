#!/usr/bin/env python3
"""v6_assemble.py - RYAN_REYNOLDS_V6: narration beats + interview interludes.

Every segment now CARRIES AUDIO:
  beat pieces  -> video piece muxed with its narration slice (from the VO)
  interludes   -> source video+audio cut, with a <LowerThird> label overlay
Then one concat of all segments (uniform re-encode), loudnorm at the end.

Also runs the global uniqueness pass: perceptual-hash sampling on every beat
piece; if a visual duplicates an earlier beat (non-outro), the beat is
flagged so the operator pass can swap it BEFORE final concat.

Run:  py -3.12 pipeline/v6_assemble.py [--check-only]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble  # noqa: E402
from v4_core import ahash, hamming  # noqa: E402

MAN = ROOT / "manifest"
WORK = ROOT / "final_video" / "v5_work"
V6W = ROOT / "final_video" / "v6_work"
OUT = ROOT / "final_video"
FPS = 30


def run(cmd, timeout=1800):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(" ".join(map(str, cmd))[:160] + "\n"
                           + (r.stderr or "")[-300:])
    return r


def mux_beat(piece, t0, t1, vo, dest):
    """Beat piece + its narration slice -> audio-carrying segment."""
    run(["ffmpeg", "-i", str(piece), "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}",
         "-i", str(vo), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-y", str(dest)])
    return dest


def interlude_seg(it, dest):
    """Cut the interview WITH ITS AUDIO + burn the source lower-third."""
    src = ROOT / "dossier" / "ryan" / f"{it['vid']}.mp4"
    dur = it["t1"] - it["t0"]
    webm = V6W / f"lt_{it['id']}.webm"
    if not webm.exists():
        assemble.WORK = WORK
        assemble.render_remotion(
            "LowerThird", {"title": it["label"], "sub": "INTERVIEW"},
            webm, min(dur, 4.5), alpha=True)
    vs = assemble._video_start(src)
    t0 = max(it["t0"], vs + 0.05)
    run(["ffmpeg", "-ss", f"{t0:.2f}", "-i", str(src),
         "-t", f"{dur:.2f}", "-c:v", "libvpx", "-i", str(webm),
         "-filter_complex",
         "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
         f"crop=1920:1080,fps={FPS}[b];[b][1:v]overlay=0:0:eof_action=pass",
         "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-y", str(dest)])
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    V6W.mkdir(parents=True, exist_ok=True)
    assets5 = json.loads((MAN / "assets_v5.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((MAN / "beats.json").read_text())["beats"]}
    inters = {it["after"]: it for it in
              json.loads((MAN / "interludes.json").read_text())}
    cfg = json.loads((ROOT / "config.json").read_text())
    vo = ROOT / f"voiceover_{cfg.get('slug', 'ryan_reynolds')}.mp3"
    order = sorted(assets5)

    # ---------- uniqueness pass (before assembling) -------------------
    seen = []          # (bid, hash)
    dupes = []
    for idx, bid in enumerate(order):
        piece = WORK / f"p_{idx:03d}_{bid}.mp4"
        if not piece.exists() or bid >= "b_095":     # outro callbacks exempt
            continue
        f = V6W / f"uh_{bid}.jpg"
        subprocess.run(["ffmpeg", "-ss", "1.0", "-i", str(piece),
                        "-frames:v", "1", "-vf", "scale=160:-2",
                        "-y", str(f)], capture_output=True, timeout=60)
        if not f.exists():
            continue
        h = ahash(f)
        for pb, ph in seen:
            if hamming(h, ph) <= 4:
                dupes.append((bid, pb))
                break
        seen.append((bid, h))
    if dupes:
        print("[UNIQUENESS] duplicate visuals found:")
        for a, b in dupes:
            print(f"   {a} duplicates {b}")
        (MAN / "v6_dupes.json").write_text(json.dumps(dupes))
        if args.check_only:
            return 1
    else:
        print("[UNIQUENESS] clean - no visual repeats")
        (MAN / "v6_dupes.json").write_text("[]")
    if args.check_only:
        return 0

    # ---------- build audio-carrying segments -------------------------
    segs = []
    for idx, bid in enumerate(order):
        piece = WORK / f"p_{idx:03d}_{bid}.mp4"
        if not piece.exists():
            raise SystemExit(f"missing piece for {bid}")
        b = beats[bid]
        seg = V6W / f"seg_{idx:03d}_{bid}.mp4"
        if not seg.exists():
            mux_beat(piece, b["start"], b["end"], vo, seg)
        segs.append(seg)
        if bid in inters:
            it = inters[bid]
            iseg = V6W / f"seg_{idx:03d}_zz_{it['id']}.mp4"
            if not iseg.exists():
                interlude_seg(it, iseg)
            segs.append(iseg)
        if (idx + 1) % 20 == 0:
            print(f"  [{idx + 1}/{len(order)}] segments", flush=True)

    lst = V6W / "concat.txt"
    lst.write_text("\n".join(f"file '{s.absolute().as_posix()}'"
                             for s in segs), encoding="utf-8")
    merged = V6W / "v6_merged.mp4"
    run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-y", str(merged)], timeout=5400)
    final = OUT / "RYAN_REYNOLDS_V6.mp4"
    run(["ffmpeg", "-i", str(merged), "-c:v", "copy",
         "-af", "loudnorm=I=-14:TP=-1.0:LRA=11",
         "-c:a", "aac", "-b:a", "192k", "-y", str(final)], timeout=3600)
    print(f"[OK] {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
