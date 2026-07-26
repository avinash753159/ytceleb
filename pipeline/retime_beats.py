#!/usr/bin/env python3
"""retime_beats.py - remap existing beats onto a NEW voiceover's word
timestamps (audio-last workflow: same script text, different voice).

Keeps beat IDs/texts; only start/end change. Fuzzy two-pointer walk
absorbs tokenization drift between the two whisper passes.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


beats = json.loads((MAN / "beats.json").read_text())["beats"]
words = json.loads((MAN / "words.json").read_text())["words"]

wi = 0
out = []
for b in beats:
    toks = [norm(t) for t in b["text"].split() if norm(t)]
    if not toks:
        continue
    # find first token near current pointer
    start_i = None
    for look in range(0, 8):
        if wi + look < len(words) and \
                norm(words[wi + look]["w"]) == toks[0]:
            start_i = wi + look
            break
    if start_i is None:
        start_i = wi
    # walk to match last token within a window sized ~len(toks)+slack
    end_i = min(start_i + len(toks) - 1, len(words) - 1)
    best = end_i
    for look in range(-3, 6):
        j = end_i + look
        if 0 <= j < len(words) and norm(words[j]["w"]) == toks[-1] \
                and j >= start_i:
            best = j
            break
    end_i = best
    b["start"] = round(words[start_i]["s"], 3)
    b["end"] = round(words[end_i]["e"], 3)
    wi = end_i + 1
    out.append(b)

# enforce monotonic, gapless tiling
for i in range(1, len(out)):
    if out[i]["start"] < out[i - 1]["end"]:
        out[i]["start"] = out[i - 1]["end"]
    if out[i]["end"] <= out[i]["start"]:
        out[i]["end"] = out[i]["start"] + 1.0
for i in range(len(out) - 1):
    out[i]["end"] = out[i + 1]["start"]        # tile with no gaps
out[-1]["end"] = round(max(out[-1]["end"], words[-1]["e"] + 0.4), 3)

durs = [b["end"] - b["start"] for b in out]
json.dump({"beats": out}, open(MAN / "beats.json", "w"), indent=1)
print(f"[OK] retimed {len(out)} beats onto new VO; "
      f"dur {min(durs):.1f}-{max(durs):.1f}s, total {out[-1]['end']:.1f}s")
