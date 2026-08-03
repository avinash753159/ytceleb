#!/usr/bin/env python3
"""Catch narration that echoes the clip next to it.

Operator feedback, verbatim: "whatever clip just talked about ... the
narration also says oh he walks 10,000 steps. it's not really adding
anything". Narration adjacent to a bite must supply consequence, context or
contradiction - never restate what the viewer just heard.

Two detectors:
  1. NUMBER ECHO   - a figure spoken in the bite reappears in neighbouring
                     narration. This is the hard failure.
  2. PHRASE ECHO   - a distinctive content bigram is shared across the
                     boundary. Softer; reported as a warning.

    py -3.12 pipeline/echo_check.py V4
    py -3.12 pipeline/echo_check.py V3      # known-bad control
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WORDNUM = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "fifteen", "twenty", "thirty", "forty",
    "fifty", "sixty", "ninety", "hundred", "thousand", "million",
}
STOP = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "for", "with", "that", "this", "it", "its", "is", "was", "were", "be",
    "been", "being", "he", "his", "him", "she", "her", "they", "them", "we",
    "you", "i", "not", "no", "so", "as", "by", "from", "into", "about",
    "just", "like", "have", "has", "had", "do", "does", "did", "will",
    "would", "can", "could", "there", "then", "than", "what", "which", "who",
    "when", "how", "all", "any", "more", "most", "one", "out", "up", "down",
    "over", "under", "very", "really", "actually", "thing", "things", "get",
    "got", "going", "know", "think", "because", "my", "me", "your", "our",
}


def toks(s):
    return re.findall(r"[a-z0-9']+", (s or "").lower())


def numbers(s):
    """Digits and spelled-out figures, normalised."""
    out = set()
    for m in re.findall(r"\d[\d,\.]*", s or ""):
        out.add(m.replace(",", "").rstrip("."))
    for w in toks(s):
        if w in WORDNUM:
            out.add(w)
    return out


def bigrams(s):
    t = [w for w in toks(s) if w not in STOP and len(w) > 2]
    return {f"{a} {b}" for a, b in zip(t, t[1:])}


def load(version):
    os.environ["MRBEAST_SCRIPT_VERSION"] = version
    sys.path.insert(0, str(ROOT / "pipeline"))
    for m in ("mrbeast_radio",):
        sys.modules.pop(m, None)
    import mrbeast_radio as radio
    bank = {r["id"]: r for r in json.loads(
        (ROOT / "manifest" / "mrbeast_soundbites.json")
        .read_text(encoding="utf-8"))}
    return radio.parse_script()["segments"], bank


def main() -> int:
    version = (sys.argv[1] if len(sys.argv) > 1 else "V4").upper()
    segs, bank = load(version)

    hard, soft = [], []
    for i, s in enumerate(segs):
        if s["kind"] != "narr":
            continue
        text = s.get("text", "")
        for j in (i - 1, i + 1):
            if not (0 <= j < len(segs)) or segs[j]["kind"] != "bite":
                continue
            bid = segs[j]["id"].split("_", 1)[1]
            btext = bank.get(bid, {}).get("text", "")
            where = "after" if j < i else "before"

            shared_p = bigrams(text) & bigrams(btext)
            shared_n = numbers(text) & numbers(btext)

            # A bare shared number word is noisy - "one problem" vs "no one
            # cared" is not an echo. Count it as a hard failure only when the
            # figure is a digit (310, 139 - always distinctive) or when it
            # carries its noun across the boundary ("three months").
            real_n = {
                v for v in shared_n
                if v.isdigit() or any(v in g for g in shared_p)
            }
            if real_n:
                hard.append((s["id"], bid, where, sorted(real_n), text))
            if shared_p:
                soft.append((s["id"], bid, where, sorted(shared_p)[:4], text))

    print(f"==== ECHO CHECK {version} ====")
    print(f"narration segments adjacent to bites: "
          f"{sum(1 for i, s in enumerate(segs) if s['kind'] == 'narr' and ((i and segs[i-1]['kind'] == 'bite') or (i + 1 < len(segs) and segs[i+1]['kind'] == 'bite')))}")

    print(f"\nNUMBER ECHOES (hard failures): {len(hard)}")
    for sid, bid, where, nums, text in hard:
        print(f"  ! {sid} repeats {nums} from bite `{bid}` ({where} it)")
        print(f"      narration: {text[:150]}")
        print(f"      bite     : {bank.get(bid, {}).get('text', '')[:150]}")

    print(f"\nPHRASE ECHOES (warnings): {len(soft)}")
    for sid, bid, where, ph, _t in soft[:12]:
        print(f"  ~ {sid} shares {ph} with `{bid}` ({where} it)")

    print()
    if hard:
        print(f"FAIL - {len(hard)} narration line(s) restate a figure the "
              f"adjacent clip already delivered.")
        return 1
    print("PASS - no narration restates a figure from its adjacent clip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
