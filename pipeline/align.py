#!/usr/bin/env python3
"""
align.py - Phase 2 step 1: word-level timestamps for the narration.

Writes manifest/words.json:
  {"audio": "...", "duration": 490.28,
   "words": [{"w": "Ryan", "s": 0.02, "e": 0.31}, ...]}

Uses faster-whisper's word_timestamps (same CTranslate2 alignment WhisperX
wraps; no torch/pyannote needed). Model 'small.en' is accurate enough for
timing and runs on CPU.

Run:  python pipeline/align.py [audio_path]
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"


def main():
    audio = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        ROOT / "voiceover_ryan_reynolds.mp3"
    if not audio.exists():
        raise SystemExit(f"[!] audio not found: {audio}")

    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "small.en"),
                         device="cpu", compute_type="int8")
    segs, info = model.transcribe(str(audio), beam_size=5,
                                  word_timestamps=True, vad_filter=True)
    words = []
    for seg in segs:
        for w in (seg.words or []):
            words.append({"w": w.word.strip(), "s": round(w.start, 3),
                          "e": round(w.end, 3)})
    MANIFEST.mkdir(exist_ok=True)
    out = MANIFEST / "words.json"
    out.write_text(json.dumps(
        {"audio": str(audio), "duration": round(info.duration, 3),
         "words": words}, indent=0), encoding="utf-8")
    print(f"[OK] {out} - {len(words)} words over {info.duration:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
