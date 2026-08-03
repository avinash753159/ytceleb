#!/usr/bin/env python3
"""Refetch the seven b-roll groups that came back under supply.

The object-first queries in fetch_broll3 worked for equipment and walking and
failed for rooms and objects that stock libraries only shoot with a person in
them. The audit of those 120 clips kept 59 and left seven groups below what
the plan draws:

    calendar 1   bed 2   desk 2   clinic 2   iv 3   bb_gear 3   bb_field 3
    eq_machine 4   gym_room 4   food 4

Two specific lessons are baked into the queries below:

  * "calendar" returned BOOKS - six of eight were novels, paperbacks or blank
    notepads being flipped. The words planner / journal / notebook / diary all
    return books. Ask for the furniture instead: a month grid, a tear-off, a
    date circled.
  * every "bed", "clinic", "desk" and "editing" query returns a person, so ask
    for the absence explicitly - empty, no people, unmade, nobody.

Aerials and stadiums are avoided outright for baseball: aerials return live
games full of players, and stadiums return trademarked turf.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "library" / "broll4"
KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

WANT = {
    "calendar": ["blank wall calendar grid", "desk calendar page turning",
                 "month grid calendar close up", "tear off calendar",
                 "date circled on calendar", "calendar squares macro"],
    "bed": ["empty unmade bed morning light", "rumpled duvet no people",
            "empty bedroom slow pan", "dark bedroom curtains drawn",
            "pillow and sheets close up", "empty bedroom window light"],
    "desk": ["empty desk monitors glowing night",
             "video editing timeline screen close up",
             "keyboard lit night no person", "empty studio chair monitors on",
             "computer screen glow dark room", "monitor close up dark office"],
    "clinic": ["empty hospital corridor no people", "empty infusion chair",
               "iv pole empty room", "hospital waiting room chairs empty",
               "treatment room empty", "empty clinic hallway"],
    "iv": ["iv drip close up no people", "saline bag hanging window light",
           "infusion pump display", "drip chamber macro",
           "iv line close up macro"],
    "eq_machine": ["weight stack close up", "cable machine empty gym",
                   "selector pin weight plate numbers",
                   "gym machine handle close up", "weight plates stacked"],
    "gym_room": ["empty weight room no people", "industrial gym empty rigs",
                 "empty gym floor barbells", "power rack empty gym"],
    "bb_gear": ["baseball glove on bench", "bat leaning fence",
                "baseball on dirt close up", "catchers mitt on grass",
                "baseball helmet on bench"],
    "bb_field": ["empty little league field dusk", "chain link backstop empty",
                 "pitchers mound close up", "infield dirt empty",
                 "empty bleachers small field"],
    "food": ["plain rice bowl overhead", "boiled chicken breast plate",
             "empty white plate table", "measured food portion plate",
             "bland food close up"],
}
MIN_DUR, MAX_DUR = 7, 40
PER_GROUP = 10

# Words that, seen in a Pexels title or the query result, mean the clip is
# almost certainly what we do NOT want.
BAD_WORDS = ("child", "kid", "boy", "girl", "baby", "toddler", "patient",
             "doctor", "nurse", "blood", "transfusion", "wedding",
             "notebook", "journal", "diary", "book", "novel", "planner",
             "basketball", "stadium", "crowd", "team", "player")


def api(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": KEY, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def best_file(files: list[dict]) -> dict | None:
    cands = [f for f in files
             if (f.get("width") or 0) >= 1280
             and (f.get("width") or 0) >= (f.get("height") or 1)]
    return sorted(cands, key=lambda f: -(f.get("width") or 0))[0] \
        if cands else None


def existing_ids() -> set[int]:
    """Do not re-download anything fetch_broll3 already has."""
    ids: set[int] = set()
    for d in (ROOT / "library/broll3", DEST):
        cf = d / "CREDITS.json"
        if cf.exists():
            try:
                for r in json.loads(cf.read_text(encoding="utf-8")):
                    if r.get("pexels_id"):
                        ids.add(int(r["pexels_id"]))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
    return ids


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    seen = existing_ids()
    print(f"[skip] {len(seen)} clip ids already fetched", flush=True)
    credits, n = [], 0
    for group, queries in WANT.items():
        got = 0
        for q in queries:
            if got >= PER_GROUP:
                break
            url = ("https://api.pexels.com/videos/search?"
                   + urllib.parse.urlencode(
                       {"query": q, "per_page": 14,
                        "orientation": "landscape", "size": "medium"}))
            try:
                data = api(url)
            except Exception as e:                              # noqa: BLE001
                print(f"[warn] {q}: {e}")
                continue
            for v in data.get("videos", []):
                if got >= PER_GROUP:
                    break
                vid = v.get("id")
                dur = v.get("duration") or 0
                if vid in seen or not (MIN_DUR <= dur <= MAX_DUR):
                    continue
                blurb = ((v.get("url") or "") + " "
                         + ((v.get("user") or {}).get("name") or "")).lower()
                if any(w in blurb for w in BAD_WORDS):
                    continue
                f = best_file(v.get("video_files") or [])
                if not f:
                    continue
                dest = DEST / f"{group}_{vid}.mp4"
                try:
                    req = urllib.request.Request(
                        f["link"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=300) as r, \
                            open(dest, "wb") as out:
                        out.write(r.read())
                except Exception as e:                          # noqa: BLE001
                    print(f"[warn] download {vid}: {e}")
                    dest.unlink(missing_ok=True)
                    continue
                seen.add(vid)
                got += 1
                n += 1
                credits.append({
                    "file": f"library/broll4/{dest.name}", "group": group,
                    "query": q, "pexels_id": vid, "url": v.get("url"),
                    "photographer": (v.get("user") or {}).get("name"),
                    "photographer_url": (v.get("user") or {}).get("url"),
                    "duration": dur, "width": f.get("width"),
                    "height": f.get("height"),
                    "license": "Pexels licence - credited in description, "
                               "never on screen"})
                print(f"  {dest.name}  {dur}s  {f.get('width')}x"
                      f"{f.get('height')}  [{q}]", flush=True)
        print(f"[{group}] +{got}", flush=True)

    (DEST / "CREDITS.json").write_text(
        json.dumps(credits, indent=2), encoding="utf-8")
    print(f"\n[OK] {n} new clips -> {DEST}")
    print("     none of these may be drawn until the eyes-on people/text "
          "audit clears them into manifest/broll_allow.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
