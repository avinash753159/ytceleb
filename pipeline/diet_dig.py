#!/usr/bin/env python3
"""Recover the diet/workout material the first research pass missed.

The V1-V4 research concluded there was "no verified diet in the public
record". That was wrong: the Rogan interview contains a first-person diet
discussion at ~87-91 min, and the Airrack documentary films the training
itself. This transcribes both properly so real windows can be cut.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "diet_dig"
JRE = ROOT / "dossier/mrbeast/sources/cLRLEnPaJLM.mp4"
AIRRACK = ROOT / "dossier/mrbeast/sources/7r3ORKgNUjw.mp4"

PROGRAM_RE = re.compile(
    r"\b(bench|squat|deadlift|press|curl|row|pull ?up|push ?up|lunge|"
    r"set|sets|rep|reps|split|push day|pull day|leg day|upper|lower|"
    r"trainer|coach|program|routine|lift|lifting|cardio|incline|dumbbell|"
    r"barbell|protein|calorie|macro|bulk|cut|body fat|percent)\b", re.I)


def clip(src, t0, dur, dest):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.2f}", "-t", f"{dur:.2f}", "-i", str(src),
         "-vn", "-ac", "1", "-ar", "16000", str(dest)],
        check=True, timeout=1800)
    return dest


def model():
    from faster_whisper import WhisperModel
    return WhisperModel("small", device="cpu", compute_type="int8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = model()

    print("=" * 74, flush=True)
    print("JRE #1788 - DIET / CROHN'S MANAGEMENT  (offset 5230s)", flush=True)
    print("=" * 74, flush=True)
    t0 = 5230.0
    w = clip(JRE, t0, 250, OUT / "jre_diet.wav")
    segs, _ = m.transcribe(str(w), vad_filter=False)
    for s in segs:
        print(f"  [{t0 + s.start:8.2f} - {t0 + s.end:8.2f}] {s.text.strip()}",
              flush=True)

    print("\n" + "=" * 74, flush=True)
    print("AIRRACK 600-DAY DOC - FULL PASS, PROGRAM MENTIONS", flush=True)
    print("=" * 74, flush=True)
    w2 = clip(AIRRACK, 0, 100000, OUT / "airrack_full.wav")
    segs2, _ = m.transcribe(str(w2), vad_filter=False)
    hits = 0
    for s in segs2:
        txt = s.text.strip()
        if PROGRAM_RE.search(txt):
            hits += 1
            print(f"  [{s.start:8.2f} - {s.end:8.2f}] {txt}", flush=True)
    print(f"\n  {hits} program-related lines found", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
