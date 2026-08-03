#!/usr/bin/env python3
"""Put back the stock dropped under the strict reading of rule 9.

The owner has relaxed it: anonymous people may perform the activity. Rule 9
now means only - never a child cast as young Jimmy, and never another
identifiable creator.

So everything dropped purely for "a hand / forearm / legs are visible" comes
back. What stays dropped is what fails a DIFFERENT rule or is simply bad:
legible third-party branding (rule 3), a stranger's readable private diary,
an almost entirely black frame, and a loaf of bread on a bed.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "manifest/broll_allow.json"
CREDS = [ROOT / "library/broll3/CREDITS.json",
         ROOT / "library/broll4/CREDITS.json"]

# file -> (group, why it is safe to restore)
RESTORE = {
    "eq_barbell_7674510.mp4": ("eq_barbell", "hands and a thigh loading a bar - anonymous, no face"),
    "eq_barbell_4859451.mp4": ("eq_barbell", "hands and forearms loading a plate"),
    "eq_machine_27861371.mp4": ("eq_machine", "legs and shoes on a treadmill; rank last, it is soft"),
    "desk_34268782.mp4": ("desk", "an arm at a monitor and a hand typing - close to the editing-desk look asked for"),
    "walk_5321384.mp4": ("walk", "legs walking a wet plaza"),
    "walk_25956625.mp4": ("walk", "legs and sneakers, POV at own feet"),
    "walk_9150767.mp4": ("walk", "legs on a curb"),
    "walk_5029705.mp4": ("walk", "legs walking away"),
    "walk_2881960.mp4": ("walk", "legs in trainers"),
    "walk_8519682.mp4": ("walk", "legs crossing a court; native 2.44:1, sides get cropped"),
    "clock_7033779.mp4": ("clock", "hands near a clock"),
    "clock_4601287.mp4": ("clock", "hands near a clock"),
    "food_8107804.mp4": ("food", "a hand at a plate"),
    "meds_9902348.mp4": ("meds", "a hand at medication"),
    "meds_6344516.mp4": ("meds", "a hand at medication"),
    "iv_6207662.mp4": ("iv", "an anonymous forearm with a cannula and line - now the RIGHT picture for the Remicade beat"),
    "bed_9057572.mp4": ("bed", "someone lying in bed - now the right picture for 'I just lay in bed all day', so the tail-only window is lifted"),
}

# stays out, and why
STILL_OUT = {
    "eq_barbell_4514293.mp4": "ROGUE embossed across the plate (rule 3)",
    "eq_machine_35585638.mp4": "ROGUE embossing, and ~80% pure black",
    "gym_room_8549741.mp4": "BODYTONE x3, SVENSSON BODY LABS, CarFitness x2 legible (rule 3)",
    "gym_room_37317187.mp4": "SD FITNESS legible on three uprights (rule 3)",
    "calendar_8489506.mp4": "a stranger's readable private week - dental 3pm, visit parents",
    "desk_33656654.mp4": "Windows Start logo, Chrome logo and a Delphi IDE window (rule 3)",
    "bed_7131833.mp4": "a loaf of bread on a board being placed on the bed",
    "iv_7033785.mp4": "effectively a black frame; tripped blackdetect",
}


def main() -> int:
    allow = json.loads(ALLOW.read_text(encoding="utf-8"))
    known: dict[str, dict] = {}
    for cf in CREDS:
        if cf.exists():
            for r in json.loads(cf.read_text(encoding="utf-8")):
                f = r.get("file") or ""
                known[Path(f).name] = r

    present = {Path(it["file"]).name for g in allow for it in allow[g]}
    added = 0
    for name, (group, why) in RESTORE.items():
        if name in present:
            continue
        rec = known.get(name)
        if not rec:
            print(f"[warn] {name} not in any CREDITS.json - skipped")
            continue
        entry = {"file": rec["file"], "duration": float(rec["duration"]),
                 "class": "OBJECT", "crop": None,
                 "note": f"RESTORED after rule 9 was relaxed: {why}"}
        # bed_9057572 previously carried a tail-only window because a sleeper
        # was in frame. A sleeper is now exactly what that beat wants.
        allow.setdefault(group, []).append(entry)
        added += 1
        print(f"[restore] {group:12} {name:34} {why[:64]}")

    ALLOW.write_text(json.dumps(allow, indent=2), encoding="utf-8")
    print(f"\nrestored {added}")
    print("still out:")
    for k, v in STILL_OUT.items():
        print(f"  {k:34} {v}")
    print("\nsupply now: " + ", ".join(
        f"{k} {len(v)}" for k, v in sorted(allow.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
