#!/usr/bin/env python3
"""Fetch OBJECT-class b-roll: things, rooms and equipment. No people.

Rule 9 bans stand-in people - "No stock child playing baseball as young
Jimmy. Use equipment, fields, objects. Nothing cast as him." The existing
library was fetched with person-first queries ("kid playing baseball",
"young man gym workout", "teenage boy alone room"), so most of it is exactly
what the rule forbids.

Compounding that: rule 2 bans reusing a clip and rule 6 rejects near-identical
pictures, which together mean ONE shot per stock clip. A 12-minute film needs
far more distinct clips than person-free queries had ever returned.

Every query here is deliberately phrased to return an object, a surface or an
empty room. Anything that comes back with a face in it still has to survive
the eyes-on audit before it can be drawn.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "library" / "broll3"
KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# group -> queries. Grouped by the chapter that needs them.
WANT = {
    # training - equipment and empty rooms only
    "eq_barbell": ["barbell on floor close up", "weight plates rack",
                   "barbell loaded gym floor"],
    "eq_dumbbell": ["dumbbell rack close up", "dumbbells on rack gym"],
    "gym_room": ["empty gym interior", "gym at night no people",
                 "weight room empty", "empty fitness studio"],
    "eq_machine": ["gym machine close up", "cable machine gym detail",
                   "treadmill belt close up"],
    # illness / treatment
    "iv": ["iv drip close up", "intravenous bag hospital",
           "saline drip medical"],
    "meds": ["pill bottle close up", "medication tablets close up",
             "medicine vial syringe"],
    "clinic": ["empty hospital corridor", "hospital room empty bed",
               "waiting room empty chairs"],
    # time / permanence
    "calendar": ["calendar pages turning", "wall calendar close up",
                 "desk calendar flipping"],
    "clock": ["clock ticking close up", "wall clock macro",
              "second hand clock close up"],
    # origin - baseball, equipment and fields, never a child
    "bb_gear": ["baseball glove on grass", "baseball bat leaning fence",
                "baseballs in bucket", "catchers mitt close up"],
    "bb_field": ["empty baseball field", "baseball diamond dirt",
                 "empty stadium seats", "baseball field night lights"],
    # food restriction
    "food": ["plain rice bowl", "boiled chicken plate simple",
             "empty dinner plate table", "bland meal plate overhead"],
    # the machine - desks, screens, night work
    "desk": ["computer monitors dark room", "keyboard close up night",
             "video editing timeline screen", "desk lamp night work"],
    # fall - sleep
    "bed": ["empty bed morning light", "dark bedroom empty",
            "crumpled bedsheets close up", "bedroom window night"],
    # walking / steps
    "walk": ["shoes walking pavement close up", "feet walking sidewalk",
             "footsteps pavement close up"],
}
MIN_DUR, MAX_DUR = 7, 40


def api(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": KEY, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def best_file(files: list[dict]) -> dict | None:
    """Largest landscape HD-or-better progressive file."""
    cands = [f for f in files
             if (f.get("width") or 0) >= 1280
             and (f.get("width") or 0) >= (f.get("height") or 1)]
    if not cands:
        return None
    return sorted(cands, key=lambda f: -(f.get("width") or 0))[0]


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    credits, seen_ids, n = [], set(), 0
    for group, queries in WANT.items():
        got = 0
        for q in queries:
            url = ("https://api.pexels.com/videos/search?"
                   + urllib.parse.urlencode(
                       {"query": q, "per_page": 12, "orientation": "landscape",
                        "size": "medium"}))
            try:
                data = api(url)
            except Exception as e:                      # noqa: BLE001
                print(f"[warn] {q}: {e}")
                continue
            for v in data.get("videos", []):
                vid = v.get("id")
                dur = v.get("duration") or 0
                if vid in seen_ids or not (MIN_DUR <= dur <= MAX_DUR):
                    continue
                f = best_file(v.get("video_files") or [])
                if not f:
                    continue
                dest = DEST / f"{group}_{vid}.mp4"
                if dest.exists():
                    seen_ids.add(vid)
                    continue
                try:
                    req = urllib.request.Request(
                        f["link"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=300) as r, \
                            open(dest, "wb") as out:
                        out.write(r.read())
                except Exception as e:                   # noqa: BLE001
                    print(f"[warn] download {vid}: {e}")
                    dest.unlink(missing_ok=True)
                    continue
                seen_ids.add(vid)
                got += 1
                n += 1
                credits.append({
                    "file": dest.name, "group": group, "query": q,
                    "pexels_id": vid, "url": v.get("url"),
                    "photographer": (v.get("user") or {}).get("name"),
                    "photographer_url": (v.get("user") or {}).get("url"),
                    "duration": dur,
                    "width": f.get("width"), "height": f.get("height"),
                    "license": "Pexels licence - free to use, no on-screen "
                               "credit required (credited in description)"})
                print(f"  {dest.name}  {dur}s  {f.get('width')}x"
                      f"{f.get('height')}  [{q}]", flush=True)
                if got >= 8:
                    break
            if got >= 8:
                break
        print(f"[{group}] {got} clips", flush=True)

    (DEST / "CREDITS.json").write_text(
        json.dumps(credits, indent=2), encoding="utf-8")
    print(f"\n[OK] {n} new clips -> {DEST}")
    print("     every one still has to pass the eyes-on people/text audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
