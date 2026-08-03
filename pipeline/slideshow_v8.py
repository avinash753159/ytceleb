#!/usr/bin/env python3
"""Render the whole film as a slideshow: one still per shot, locked audio.

A flip-through of the entire picture plan at a size you can actually open -
every shot the film makes, in order, each held for exactly its own length, so
the audio stays in sync and any shot can be found by its timecode.

Frame counts come straight from the shot list, so the slideshow is the same
length as the film to the frame: nothing here re-times anything.

The still is taken from the MIDDLE of each rendered piece rather than its
first frame, because every piece fades in - a first frame would be a slideshow
of fade-ups.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import fx                                                        # noqa: E402

SUFFIX = os.environ.get("BUILD_SUFFIX", "V8")
PIECES = ROOT / f"work/picture_{SUFFIX.lower()}"
SHOTS = ROOT / f"manifest/picture_{SUFFIX.lower()}_shots.json"
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
WORK = ROOT / f"work/slideshow_{SUFFIX.lower()}"
OUT = ROOT / f"final_video/MRBEAST_{SUFFIX}_SLIDESHOW.mp4"

# Stills compress to almost nothing, so quality costs little here. 720p keeps
# the file small enough to send while staying readable on a phone.
HEIGHT = int(os.environ.get("SLIDE_HEIGHT", "720"))
CRF = os.environ.get("SLIDE_CRF", "26")


def still_segment(s: dict) -> Path:
    """One shot's still, held for exactly that shot's frame count."""
    src = PIECES / f"{s['name']}.mp4"
    dest = WORK / f"{s['name']}.mp4"
    if dest.exists():
        return dest
    if not src.exists():
        raise FileNotFoundError(src)
    png = WORK / f"{s['name']}.png"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{s['dur']*0.5:.3f}", "-i", str(src), "-frames:v", "1",
         str(png)], check=True, timeout=300)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-loop", "1", "-i", str(png), "-frames:v", str(s["frames"]),
         "-vf", f"scale=-2:{HEIGHT},fps={fx.FPS},format=yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", CRF,
         "-threads", "2", str(dest)], check=True, timeout=600)
    png.unlink(missing_ok=True)
    return dest


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    print(f"[slideshow] {len(shots)} shots -> one still each", flush=True)

    workers = max(2, min(10, (os.cpu_count() or 8) // 2))
    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(still_segment, s): s for s in shots}
        for f in as_completed(futs):
            f.result()
            done += 1
            if done % 40 == 0:
                print(f"[slideshow] {done}/{len(shots)}", flush=True)
    print(f"[slideshow] stills in {time.time()-t0:.0f}s", flush=True)

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(
        f"file '{(WORK / (s['name'] + '.mp4')).absolute().as_posix()}'"
        for s in shots), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-c", "copy",
            str(silent)], timeout=3600)

    vdur, adur = fx.probe_dur(silent), fx.probe_dur(AUDIO)
    print(f"[slideshow] {vdur:.3f}s vs audio {adur:.3f}s "
          f"({vdur-adur:+.3f}s)", flush=True)
    if abs(vdur - adur) > 0.25:
        raise RuntimeError(f"out of sync by {vdur-adur:+.3f}s")

    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
            str(silent), "-i", str(AUDIO), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
            "-movflags", "+faststart", str(OUT)], timeout=1800)
    mb = OUT.stat().st_size / 1048576
    print(f"[OK] {OUT}  {fx.probe_dur(OUT)/60:.2f} min  {mb:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
