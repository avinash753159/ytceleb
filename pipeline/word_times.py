#!/usr/bin/env python3
"""Print word-level timestamps for a source window, for exact bite cutting.

    py -3.12 pipeline/word_times.py cLRLEnPaJLM 5255 175
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "dossier" / "mrbeast" / "sources"


def main():
    sid, t0, dur = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    src = SOURCES / f"{sid}.mp4"
    wav = ROOT / "work" / "_wt.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{t0}", "-t", f"{dur}", "-i", str(src),
                    "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                   check=True, timeout=1800)
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), vad_filter=False, word_timestamps=True)
    for s in segs:
        line = " ".join(f"{w.word.strip()}@{t0 + w.start:.2f}"
                        for w in (s.words or []))
        print(f"[{t0 + s.start:8.2f}] {line}", flush=True)
    wav.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
