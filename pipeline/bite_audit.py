#!/usr/bin/env python3
"""Audit every soundbite's in/out points against the actual audio.

Operator complaint: clips end mid-conversation, or run past the relevant
sentence into material that has nothing to do with the story ("...and then
not only do we have to work out together but we have to challenge each
other" - the competition tail belongs to a different idea).

For each bite this transcribes a padded window with word timestamps and
reports:
  - START MID-SENTENCE : the cut begins after a sentence has already started
  - END MID-SENTENCE   : the cut stops before the sentence finishes
  - TAIL DRIFT         : the last sentence inside the cut introduces a new
                         subject not present earlier in the cut
plus the exact word times of every sentence boundary near the edges, so a
corrected t0/t1 can be chosen instead of guessed.

    py -3.12 pipeline/bite_audit.py            # all bites
    py -3.12 pipeline/bite_audit.py colin_     # only ids containing 'colin_'
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "manifest" / "mrbeast_soundbites.json"
SOURCES = ROOT / "dossier" / "mrbeast" / "sources"
WORK = ROOT / "work" / "bite_audit"
PAD_BEFORE = 5.0
PAD_AFTER = 10.0

STOP = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "for", "with", "that", "this", "it", "its", "is", "was", "were", "be",
    "been", "he", "his", "him", "they", "them", "we", "you", "i", "not",
    "no", "so", "as", "by", "from", "just", "like", "have", "has", "had",
    "do", "does", "did", "will", "would", "can", "could", "there", "then",
    "what", "which", "when", "how", "all", "any", "more", "out", "up",
    "very", "really", "actually", "thing", "things", "get", "got", "going",
    "know", "think", "because", "my", "me", "your", "our", "am", "are",
    "were", "one", "two", "day", "days", "yeah", "okay", "right", "well",
}
_M = None


def model():
    global _M
    if _M is None:
        from faster_whisper import WhisperModel
        _M = WhisperModel("small", device="cpu", compute_type="int8")
    return _M


def words_for(src: Path, t0: float, dur: float):
    WORK.mkdir(parents=True, exist_ok=True)
    wav = WORK / "_w.wav"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
         "-vn", "-ac", "1", "-ar", "16000", str(wav)],
        check=True, timeout=1800)
    segs, _ = model().transcribe(str(wav), vad_filter=False,
                                 word_timestamps=True)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append((w.word.strip(), t0 + w.start, t0 + w.end))
    wav.unlink(missing_ok=True)
    return out


def sentences(words):
    """Group words into sentences on terminal punctuation."""
    sents, cur = [], []
    for w, a, b in words:
        cur.append((w, a, b))
        if re.search(r"[.!?]$", w):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    return [{"text": " ".join(x[0] for x in s),
             "t0": s[0][1], "t1": s[-1][2]} for s in sents if s]


def content(text):
    return {w for w in re.findall(r"[a-z']+", text.lower())
            if w not in STOP and len(w) > 2}


def audit(bite, words):
    t0, t1 = bite["t0"], bite["t1"]
    sents = sentences(words)
    inside = [s for s in sents if s["t1"] > t0 + 0.15 and s["t0"] < t1 - 0.15]

    issues = []
    if inside:
        first, last = inside[0], inside[-1]
        if first["t0"] < t0 - 0.35:
            issues.append(("START MID-SENTENCE",
                           f"sentence begins {t0 - first['t0']:.2f}s before "
                           f"the cut: \"{first['text'][:80]}\""))
        if last["t1"] > t1 + 0.35:
            issues.append(("END MID-SENTENCE",
                           f"sentence continues {last['t1'] - t1:.2f}s past "
                           f"the cut: \"{last['text'][:80]}\""))
        # Tail drift: does the final sentence introduce a new subject?
        if len(inside) >= 2:
            body = set()
            for s in inside[:-1]:
                body |= content(s["text"])
            tail = content(inside[-1]["text"])
            novel = tail - body
            if tail and len(novel) / max(1, len(tail)) > 0.75:
                issues.append(("TAIL DRIFT",
                               f"final sentence is {len(novel)}/{len(tail)} "
                               f"new subject matter: "
                               f"\"{inside[-1]['text'][:90]}\""))
    else:
        issues.append(("NO SPEECH", "no complete sentence inside the window"))
    return sents, inside, issues


def main() -> int:
    filt = sys.argv[1] if len(sys.argv) > 1 else ""
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    flagged = 0

    for b in bank:
        if filt and filt not in b["id"]:
            continue
        if b.get("status", "").startswith("rejected"):
            continue
        src = SOURCES / f"{b['source_id']}.mp4"
        if not src.exists():
            print(f"-- {b['id']}: MISSING SOURCE {src.name}")
            continue

        t0, t1 = b["t0"], b["t1"]
        words = words_for(src, max(0, t0 - PAD_BEFORE),
                          (t1 - t0) + PAD_BEFORE + PAD_AFTER)
        sents, inside, issues = audit(b, words)

        print("=" * 78, flush=True)
        print(f"{b['id']}   [{t0:.2f} -> {t1:.2f}]  ({t1 - t0:.2f}s)",
              flush=True)
        for s in sents:
            mark = "  "
            if s["t1"] <= t0 + 0.15:
                mark = "< "          # before the cut
            elif s["t0"] >= t1 - 0.15:
                mark = "> "          # after the cut
            else:
                mark = "* "          # inside the cut
            print(f"  {mark}[{s['t0']:8.2f}-{s['t1']:8.2f}] {s['text'][:110]}",
                  flush=True)
        if issues:
            flagged += 1
            for kind, detail in issues:
                print(f"  !! {kind}: {detail}", flush=True)
        else:
            print("  OK - clean sentence boundaries, no tail drift",
                  flush=True)

    print(f"\n{flagged} bite(s) flagged.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
