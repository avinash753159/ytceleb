#!/usr/bin/env python3
"""soundbank.py - build and query the archival soundbite bank.

The V11 format needs real voices carrying >=40% of runtime, which means
the script is written TO the material rather than the material hunted to
match the script. This module indexes every utterance in every source so
the bank exists before the script does.

Sources are transcribed with faster-whisper (punctuated + word
timestamps). YouTube auto-caption VTTs carry no punctuation and are
useless for sentence boundaries - established in v7_interludes.

Output: manifest/soundbites.json
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"

MAX_BITE_S = 30.0
SENT_END = re.compile(r"[.!?]['\"]?$")


def merge_words(words, max_gap=0.6, max_dur=MAX_BITE_S):
    """Group (t0, t1, word) tuples into sentence-bounded utterances.

    Splits on: sentence-final punctuation, a silence gap > max_gap, or
    an utterance running past max_dur.
    """
    out, cur = [], []

    def flush():
        if cur:
            out.append({"t0": round(cur[0][0], 2),
                        "t1": round(cur[-1][1], 2),
                        "text": " ".join(x[2] for x in cur)})
            cur.clear()

    for i, (t0, t1, word) in enumerate(words):
        if cur:
            if t0 - cur[-1][1] > max_gap:
                flush()
            elif t1 - cur[0][0] > max_dur:
                flush()
        cur.append((t0, t1, word))
        if SENT_END.search(word):
            flush()
    flush()
    return out


def _transcribe(src, model):
    """Whisper a whole source; return [(t0, t1, word), ...]."""
    wav = Path(tempfile.gettempdir()) / f"sb_{Path(src).stem}.wav"
    subprocess.run(["ffmpeg", "-i", str(src), "-vn", "-ac", "1",
                    "-ar", "16000", "-y", str(wav)],
                   capture_output=True, check=True)
    segs, _ = model.transcribe(str(wav), word_timestamps=True, language="en")
    words = []
    for s in segs:
        for x in s.words or []:
            words.append((x.start, x.end, x.word.strip()))
    wav.unlink(missing_ok=True)
    return words


def index_source(src_path, source_id, speaker, model):
    """Transcribe one source into full utterance records."""
    return [{"source_id": source_id,
             "t0": u["t0"],
             "t1": u["t1"],
             "speaker": speaker,
             "text": u["text"],
             "topic_tags": [],
             "emotion": "",
             "on_camera": True,
             "audio_clean": True}
            for u in merge_words(_transcribe(src_path, model))]


def main():
    """Index every source listed in manifest/bank_sources.json.

    bank_sources.json: [{"id": "<yt id>", "path": "dossier/x/<id>.mp4",
                         "speaker": "subject"}, ...]
    """
    from faster_whisper import WhisperModel
    model = WhisperModel("base.en", compute_type="int8")
    srcs = json.loads((MAN / "bank_sources.json").read_text(encoding="utf-8"))
    bank = []
    for s in srcs:
        p = ROOT / s["path"]
        if not p.exists():
            print(f"{s['id']}: MISSING {p} - skipped")
            continue
        recs = index_source(p, s["id"], s.get("speaker", "unknown"), model)
        bank.extend(recs)
        print(f"{s['id']}: {len(recs)} utterances", flush=True)
    (MAN / "soundbites.json").write_text(
        json.dumps(bank, indent=1), encoding="utf-8")
    print(f"[OK] {len(bank)} utterances -> manifest/soundbites.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
