#!/usr/bin/env python3
"""
beats.py - Phase 2 step 2: segment the word-aligned narration into BEATS.

A beat is the unit that receives exactly one visual treatment: 2-7s,
cut at clause boundaries (sentence enders first, then commas/conjunctions),
never mid-word. Beats tile the narration with no gaps.

In:  manifest/words.json   Out: manifest/beats.json
Run: python pipeline/beats.py
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"

MIN_BEAT = 2.0
MAX_BEAT = 7.0
TARGET = 4.5
CONJ = {"and", "but", "so", "because", "while", "then", "which", "that"}


def main():
    data = json.loads((MANIFEST / "words.json").read_text(encoding="utf-8"))
    words = data["words"]
    n = len(words)

    # boundary strength after word i: 2 = sentence end, 1 = clause-ish
    strength = [0] * n
    for i, w in enumerate(words):
        t = w["w"]
        if re.search(r"[.!?]['\"]?$", t):
            strength[i] = 2
        elif t.endswith(",") or t.endswith(";") or t.endswith(":"):
            strength[i] = 1
        elif i + 1 < n and words[i + 1]["w"].lower().strip(",.") in CONJ:
            strength[i] = 1

    beats, start_i = [], 0
    while start_i < n:
        s_time = words[start_i]["s"]
        # candidate cut: strongest boundary in the window closest to TARGET
        best, best_score = None, -1.0
        for j in range(start_i, n):
            dur = words[j]["e"] - s_time
            if dur < MIN_BEAT:
                continue
            if dur > MAX_BEAT and best is not None:
                break
            sc = strength[j] * 10 - abs(dur - TARGET)
            if dur > MAX_BEAT:          # forced cut, no boundary found
                sc = 0 if best is None else -99
            if sc > best_score:
                best, best_score = j, sc
            if j == n - 1:
                break
        j = best if best is not None else min(start_i + 12, n - 1)
        beats.append({
            "beat_id": f"b_{len(beats):03d}",
            "text": " ".join(w["w"] for w in words[start_i:j + 1]),
            "start": round(s_time, 2),
            "end": round(words[j]["e"], 2),
            "word_start": start_i, "word_end": j,
        })
        start_i = j + 1

    # tile exactly: each beat ends where the next begins
    for k in range(len(beats) - 1):
        beats[k]["end"] = beats[k + 1]["start"]
    # audio tail (outro music after the last word) becomes its OWN beat so a
    # spoken beat is never stretched past MAX_BEAT
    last_e = beats[-1]["end"]
    tail = round(data["duration"], 2) - last_e
    if tail > 3.0:
        beats.append({"beat_id": f"b_{len(beats):03d}", "text": "",
                      "start": last_e, "end": round(data["duration"], 2),
                      "word_start": -1, "word_end": -1, "tail": True})
    else:
        beats[-1]["end"] = round(data["duration"], 2)

    out = MANIFEST / "beats.json"
    out.write_text(json.dumps({"duration": data["duration"], "beats": beats},
                              indent=1), encoding="utf-8")
    durs = [b["end"] - b["start"] for b in beats]
    print(f"[OK] {out} - {len(beats)} beats, "
          f"{min(durs):.1f}-{max(durs):.1f}s (median "
          f"{sorted(durs)[len(durs)//2]:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
