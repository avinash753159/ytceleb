#!/usr/bin/env python3
"""Measure the reference video's opening sound design and cutting rhythm."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VID = ROOT / "work/ref_study/IbWl40xgw0A.mp4"
SCENES = ROOT / "work/ref_study/scenes.txt"
HEAD = 100.0


def pcm(path, t0, dur, sr=8000):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t0}",
         "-t", f"{dur}", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
         "-f", "f32le", "-"], capture_output=True, timeout=900)
    return np.frombuffer(r.stdout, dtype=np.float32), sr


def main():
    print(f"reference: {VID.name}", flush=True)

    # ---------- opening envelope ----------
    x, sr = pcm(VID, 0, HEAD)
    win = 0.25
    n = int(sr * win)
    f = x[:len(x) - len(x) % n].reshape(-1, n)
    env = 20 * np.log10(np.sqrt((f ** 2).mean(axis=1)) + 1e-12)
    floor = float(np.percentile(env, 3))
    aud = np.where(env > floor + 10)[0]
    audio_start = aud[0] * win if len(aud) else None

    # ---------- first narrated word ----------
    from faster_whisper import WhisperModel
    wav = ROOT / "work/ref_study/_h.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-t", str(HEAD), "-i", str(VID), "-vn", "-ac", "1",
                    "-ar", "16000", str(wav)], check=True, timeout=900)
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), vad_filter=False, word_timestamps=True)
    segs = list(segs)
    first = None
    for s in segs:
        if s.words:
            first = s.words[0].start
            break
    wav.unlink(missing_ok=True)

    print("\n--- OPENING SOUND DESIGN ---", flush=True)
    print(f"first audible audio : {audio_start:.2f}s")
    print(f"first narrated word : {first:.2f}s")
    print(f"ATMOSPHERE LEAD-IN  : {first - audio_start:.2f}s of sound "
          f"before a single word", flush=True)

    print("\nloudness per second, first 24s (dBFS):", flush=True)
    per = [float(env[i * 4:(i + 1) * 4].mean()) for i in range(24)]
    for i in range(0, 24, 8):
        print("  {:2d}-{:2d}s ".format(i, i + 7)
              + " ".join(f"{v:6.1f}" for v in per[i:i + 8]))

    print("\nopening narration:", flush=True)
    for s in segs[:9]:
        print(f"  [{s.start:6.2f}] {s.text.strip()[:100]}")

    # ---------- cutting pace ----------
    ts = [float(t) for t in re.findall(r"pts_time:([\d.]+)",
                                       SCENES.read_text(encoding="utf-8"))]
    ts.sort()
    if ts:
        d = np.diff(ts)
        total = 2368.354
        print("\n--- CUTTING PACE ---", flush=True)
        print(f"cuts detected     : {len(ts)}")
        print(f"mean shot length  : {total / max(1, len(ts)):.2f}s")
        print(f"median gap        : {np.median(d):.2f}s")
        print(f"gaps under 2s     : {(d < 2).mean():.0%}")
        print(f"gaps over 8s      : {(d > 8).mean():.0%}")
        starts = np.array(ts[:-1])
        thirds = [d[(starts >= total * i / 3) & (starts < total * (i + 1) / 3)]
                  for i in range(3)]
        for i, t in enumerate(thirds):
            if len(t):
                print(f"  act {i+1} median gap : {np.median(t):.2f}s "
                      f"({len(t)} cuts)")
        opening = d[np.array(ts[:-1]) < 100]
        if len(opening):
            print(f"  first 100s median: {np.median(opening):.2f}s "
                  f"({len(opening)} cuts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
