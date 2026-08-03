#!/usr/bin/env python3
"""Find where the narration repeats ITSELF across the film.

echo_check.py catches narration restating the adjacent clip. This catches a
different defect the operator flagged - "it needs to be a complete story, not
just repeat Crohn's disease etc": the same idea, phrase or fact returning in
several narration blocks so the film circles instead of advancing.

Reports:
  CONCEPT FREQUENCY - key story concepts and how often narration says them
  REPEATED PHRASES  - content trigrams appearing in 2+ narration blocks
  RESTATED FACTS    - the same figure appearing in 2+ narration blocks

    py -3.12 pipeline/repetition_check.py V5
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONCEPTS = {
    "crohn's/disease": r"\bcrohn|\bdisease\b|\billness\b",
    "immune system": r"\bimmune\b",
    "age fifteen": r"\bfifteen\b|\b15\b",
    "baseball": r"\bbaseball\b",
    "the machine/system": r"\bmachine\b|\bsystem\b",
    "body/physique": r"\bbody\b|\bphysique\b",
    "time/hours": r"\bhours?\b|\btime\b",
    "energy/tired": r"\benerg|\btired\b|\bexhaust|\bfatigue",
    "habit/repetition": r"\bhabit\b|\brepetition\b|\bconsistent",
    "recovery/rest": r"\brecovery\b|\brest\b|\bsleep\b",
    "not a cure": r"\bcure\b|\btreatment\b|\bremission\b",
}

STOP = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "for", "with", "that", "this", "it", "its", "is", "was", "were", "be",
    "been", "he", "his", "him", "they", "them", "we", "you", "i", "not",
    "no", "so", "as", "by", "from", "just", "like", "have", "has", "had",
    "do", "does", "did", "will", "would", "can", "could", "there", "then",
    "what", "which", "when", "how", "all", "any", "more", "out", "up",
    "very", "into", "than", "who", "one", "his", "her", "their", "about",
}


def toks(s):
    return [w for w in re.findall(r"[a-z']+", s.lower())
            if w not in STOP and len(w) > 2]


def main() -> int:
    version = (sys.argv[1] if len(sys.argv) > 1 else "V5").upper()
    os.environ["MRBEAST_SCRIPT_VERSION"] = version
    sys.path.insert(0, str(ROOT / "pipeline"))
    for m in [k for k in sys.modules if k.startswith("mrbeast_radio")]:
        del sys.modules[m]
    import mrbeast_radio as radio

    segs = radio.parse_script()["segments"]
    narr = [(s["id"], s["chapter"], s.get("text", ""))
            for s in segs if s["kind"] == "narr"]
    print(f"==== REPETITION CHECK {version} ====")
    print(f"{len(narr)} narration blocks, "
          f"{sum(len(t.split()) for _, _, t in narr)} words\n")

    print("--- CONCEPT FREQUENCY (how often narration returns to an idea) ---")
    for name, pat in CONCEPTS.items():
        hits = [(i, c) for i, (_, c, t) in enumerate(narr)
                if re.search(pat, t, re.I)]
        acts = sorted({c for _, c in hits})
        flag = "  <-- circling" if len(hits) >= 6 else ""
        print(f"  {name:20} {len(hits):2d} blocks  across {len(acts)} acts"
              f"{flag}")
        if len(hits) >= 6:
            print(f"      acts: {', '.join(acts)}")

    print("\n--- REPEATED PHRASES (trigram in 2+ blocks) ---")
    seen = defaultdict(list)
    for sid, ch, t in narr:
        tk = toks(t)
        for g in {" ".join(tk[i:i + 3]) for i in range(len(tk) - 2)}:
            seen[g].append(sid)
    rep = {g: ids for g, ids in seen.items() if len(ids) > 1}
    for g, ids in sorted(rep.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  \"{g}\"  in {', '.join(ids)}")
    if not rep:
        print("  none")

    print("\n--- RESTATED FIGURES ---")
    nums = defaultdict(list)
    for sid, ch, t in narr:
        for n in re.findall(r"\b(\d[\d,]*|fifteen|fifty|ten|three hundred"
                            r"|six hundred|hundred)\b", t.lower()):
            nums[n].append(sid)
    for n, ids in sorted(nums.items(), key=lambda x: -len(x[1])):
        if len(ids) > 1:
            print(f"  \"{n}\" in {len(ids)} blocks: {', '.join(ids)}")

    print("\n--- ACT WORD BUDGET (is any act carrying too much talk?) ---")
    per = Counter()
    for _, ch, t in narr:
        per[ch] += len(t.split())
    total = sum(per.values())
    for ch, w in per.items():
        bar = "#" * round(w / max(1, total) * 60)
        print(f"  {ch:11} {w:4d}w {w / total:5.1%} {bar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
