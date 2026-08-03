#!/usr/bin/env python3
"""Render the storyboard's designed graphics as real stills.

They have been hatched placeholders through three storyboard revisions.
Rendered at ~65% through each card so the animation has resolved.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPHICS = ROOT / "graphics"
OUT = ROOT / "work" / "cards"
ACCENT = "#E3120B"
FPS, DUR = 30, 150

CARDS = {
    "card_weight": ("RangeSplit", {
        "title": "HIS ACCOUNT, AGE 15",
        "left": "190", "leftSub": "POUNDS BEFORE",
        "right": "139", "rightSub": "POUNDS AFTER"}),
    "card_310": ("BigCounter", {
        "title": "THE PACT", "from": 0, "to": 310,
        "suffix": "", "sub": "DAYS FOLLOWED / PROGRAMMED REST ALLOWED"}),
    "card_steps": ("StepsRing", {
        "title": "DAILY MOVEMENT", "display": "12,500"}),
    # ClockRing renders fromH-toH as its readout, so 0/2 printed a
    # meaningless "0-2h ... every night". Sweep to 2 from 2 so the label
    # reads as a single figure: the hours per day the training cost him.
    "card_time": ("ClockRing", {
        "title": "WHAT IT COST HIM DAILY", "fromH": 2, "toH": 2}),
    "card_rest": ("CalendarGrid", {
        "title": "REST WAS PART OF THE PLAN", "activeDays": 5}),
    # Checklist2 draws ticks, which read as "present" - wrong for a list of
    # absences. Phrased so a tick is truthful: these are things the film
    # has verified, not things he did.
    "card_record": ("Checklist2", {
        "title": "WHAT WE ACTUALLY VERIFIED",
        "items": [
            {"text": "No training split was ever published", "atMs": 0},
            {"text": "No sets, reps or calorie target exist", "atMs": 600},
            {"text": "The 41% body-fat figure is Airrack's, not his",
             "atMs": 1200},
        ]}),
}


def render(comp: str, props: dict, dest: Path) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    props = dict(props)
    props.update({"durationInFrames": DUR, "fps": FPS, "accent": ACCENT})
    pf = OUT / f"props_{dest.stem}.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    cmd = ["npx.cmd", "remotion", "still", "src/index.ts", comp, str(dest),
           f"--props={pf}", f"--frame={int(DUR * 0.65)}", "--log=error"]
    r = subprocess.run(cmd, cwd=GRAPHICS, capture_output=True, text=True,
                       timeout=1800)
    if r.returncode or not dest.exists():
        raise RuntimeError(f"{comp} failed:\n"
                           + (r.stderr or r.stdout or "")[-1200:])
    return dest


def main() -> int:
    ok, bad = [], []
    for key, (comp, props) in CARDS.items():
        dest = OUT / f"{key}.png"
        if dest.exists():
            ok.append(key)
            print(f"have  {key}")
            continue
        try:
            render(comp, props, dest)
            ok.append(key)
            print(f"OK    {key:14} <- {comp}")
        except Exception as e:  # noqa: BLE001
            bad.append(key)
            print(f"FAIL  {key:14} {str(e).splitlines()[-1][:110]}")
    print(f"\n{len(ok)} rendered, {len(bad)} failed -> {OUT}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
