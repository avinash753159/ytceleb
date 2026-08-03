#!/usr/bin/env python3
"""Apply V5 bank changes: boundary fixes + newly recovered material.

BOUNDARY FIXES (operator-reported: clips run past the relevant idea)
  airrack_contract_premise  t1 8.36 -> 5.95
      Removed: "and at the end of it we have to compete in an actual
      bodybuilding competition." The competition is a different idea, it is
      never paid off, and it reframes a health story as a contest.
      Word timing: "days" ends 5.60; the tail begins 6.06.
  airrack_jimmy_continue    t0 1114.42 -> 1115.85
      Removed the host's question so the cut opens on Jimmy at "Oh, of
      course." (word timing: host 1114.36-1115.56, Jimmy from 1115.90).

NEW MATERIAL - recovered from Rogan #1788 at ~87-91 min, which the original
research pass missed entirely while concluding "no verified diet exists".
All timings taken from faster-whisper word timestamps. Profanity-free
windows only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "manifest" / "mrbeast_soundbites.json"

FIXES = {
    "airrack_contract_premise": {
        "t1": 5.95,
        "text": ("I signed a legally binding contract with MrBeast that says "
                 "that we both have to work out every single day for 600 "
                 "days."),
        "edit_note": ("Tail removed at 5.95s: the bodybuilding-competition "
                      "clause is a separate idea, never paid off, and turns "
                      "a health story into a contest."),
    },
    "airrack_jimmy_continue": {
        "t0": 1115.85,
        "t1": 1118.15,
        "text": ("Oh, of course. I mean, mostly because I just don't want "
                 "to die."),
        "edit_note": ("Head moved past the host's question so the cut opens "
                      "on Jimmy."),
    },
}

NEW = [
    {
        "id": "jre_least_energetic",
        "source_id": "cLRLEnPaJLM", "speaker": "subject",
        "t0": 5265.40, "t1": 5267.50,
        "chapter": "illness",
        "topic_tags": ["crohns", "energy", "contradiction"],
        "text": "I'm probably one of the least energetic people you'll ever "
                "meet.",
        "status": "transcript_verified_frame_check_pending",
        "verification_note": "Rogan #1788. The central contradiction of the "
                             "film in his own words.",
    },
    {
        "id": "jre_triggers",
        "source_id": "cLRLEnPaJLM", "speaker": "subject",
        "t0": 5308.80, "t1": 5313.90,
        "chapter": "protocol",
        "topic_tags": ["diet", "triggers", "crohns"],
        "text": "Corn. Anything spicy. Anything like overly, overly "
                "processed.",
        "status": "transcript_verified_frame_check_pending",
        "verification_note": "His actual named trigger foods. Window starts "
                             "after the profanity at 5307.",
    },
    {
        "id": "jre_flare_dead",
        "source_id": "cLRLEnPaJLM", "speaker": "subject",
        "t0": 5353.90, "t1": 5359.60,
        "chapter": "illness",
        "topic_tags": ["crohns", "flare", "despair"],
        "text": "Sometimes I'll flare up and then I'm just like, I'm dead. I "
                "just lay in bed all day, and I can't really do anything.",
        "status": "transcript_verified_frame_check_pending",
        "verification_note": "The emotional floor of the story - what the "
                             "disease actually costs him, unglamorised.",
    },
    {
        "id": "jre_remicade",
        "source_id": "cLRLEnPaJLM", "speaker": "subject",
        "t0": 5363.35, "t1": 5369.20,
        "chapter": "limit",
        "topic_tags": ["treatment", "remicade", "immune"],
        "text": "I'm on what's called Remicade, and so every eight weeks "
                "they just do an IV with a huge bag, which essentially "
                "suppresses my immune system.",
        "status": "transcript_verified_frame_check_pending",
        "verification_note": "Names the actual treatment and its interval. "
                             "Present as his account, not medical advice.",
    },
    {
        "id": "jre_its_just_life",
        "source_id": "cLRLEnPaJLM", "speaker": "subject",
        "t0": 5416.15, "t1": 5419.95,
        "chapter": "resolution",
        "topic_tags": ["acceptance", "crohns", "resolution"],
        "text": "Honestly, I haven't really thought about it. It's just one "
                "of those things - I'm so used to it. It's just life.",
        "status": "transcript_verified_frame_check_pending",
        "verification_note": "Quiet acceptance. Ends before the host "
                             "re-enters at 5420.00.",
    },
]


def main() -> int:
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    by_id = {b["id"]: b for b in bank}

    for bid, patch in FIXES.items():
        if bid not in by_id:
            raise KeyError(f"cannot fix missing bite {bid}")
        before = (by_id[bid]["t0"], by_id[bid]["t1"])
        by_id[bid].update(patch)
        by_id[bid]["duration"] = round(
            by_id[bid]["t1"] - by_id[bid]["t0"], 2)
        print(f"FIX  {bid}: {before[0]:.2f}->{before[1]:.2f}  =>  "
              f"{by_id[bid]['t0']:.2f}->{by_id[bid]['t1']:.2f} "
              f"({by_id[bid]['duration']}s)")

    for n in NEW:
        if n["id"] in by_id:
            print(f"SKIP {n['id']} already present")
            continue
        n["duration"] = round(n["t1"] - n["t0"], 2)
        bank.append(n)
        print(f"ADD  {n['id']}: {n['t0']:.2f}->{n['t1']:.2f} "
              f"({n['duration']}s)")

    BANK.write_text(json.dumps(bank, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print(f"\nbank now holds {len(bank)} bites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
