#!/usr/bin/env python3
"""Fetch a deep, varied b-roll pool so no clip ever has to repeat or loop.

Operator notes this answers directly:
  - "the same 5 second loop over and over"  -> enough distinct clips that
    every beat draws a fresh one
  - "you're having an old man lift weights" -> young-subject queries
  - "if he's talking about baseball it should be a kid playing baseball"
  - loops are banned outright, so clips must be long enough on their own
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "library" / "broll"
KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Several clips per concept so beats never reuse one.
WANT = {
    "baseball_kid": ["kid playing baseball", "youth baseball game",
                     "boy baseball bat"],
    "baseball_field": ["empty baseball field", "baseball diamond dusk"],
    "teen_alone": ["teenage boy alone room", "lonely teenager bedroom"],
    "young_gym": ["young man gym workout", "young man weight training",
                  "man exercising gym young"],
    "young_lifting": ["young man barbell bench press",
                      "man doing pull ups gym"],
    "walking_alone": ["man walking alone street", "person walking sidewalk",
                      "walking shoes pavement"],
    "hospital": ["hospital corridor", "iv drip hospital"],
    "bedroom_night": ["person lying awake bed night", "dark bedroom window"],
    "empty_gym2": ["gym at night empty", "weights rack gym empty"],
    "food_plain": ["plain chicken rice meal", "simple meal plate"],
    "editing_desk": ["person editing video computer",
                     "man working late computer"],
    "clock_calendar": ["calendar flipping", "clock ticking close up"],
}
MIN_DUR, MAX_DUR = 8, 30


def api(url):
    req = urllib.request.Request(
        url, headers={"Authorization": KEY, "User-Agent": UA,
                      "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=900) as r:
        dest.write_bytes(r.read())


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    ledger_path = DEST / "CREDITS.json"
    ledger = (json.loads(ledger_path.read_text(encoding="utf-8"))
              if ledger_path.exists() else [])
    have = {e.get("pexels_id") for e in ledger}

    for concept, queries in WANT.items():
        got = 0
        for qi, query in enumerate(queries):
            if got >= 2:
                break
            url = ("https://api.pexels.com/videos/search?"
                   + urllib.parse.urlencode(
                       {"query": query, "per_page": 12,
                        "orientation": "landscape", "size": "medium"}))
            try:
                data = api(url)
            except Exception as e:  # noqa: BLE001
                print(f"ERR   {concept}/{query}: {e}")
                continue
            for v in data.get("videos") or []:
                if got >= 2 or v["id"] in have:
                    continue
                if not (MIN_DUR <= v.get("duration", 0) <= MAX_DUR):
                    continue
                best = None
                for f in v.get("video_files", []):
                    w = f.get("width") or 0
                    if 1200 <= w <= 2100 and f.get("file_type") == "video/mp4":
                        if best is None or w > (best.get("width") or 0):
                            best = f
                if not best:
                    continue
                out = DEST / f"{concept}_{got + 1}.mp4"
                try:
                    download(best["link"], out)
                except Exception as e:  # noqa: BLE001
                    print(f"ERR   download {concept}: {e}")
                    continue
                have.add(v["id"])
                ledger.append({
                    "key": out.stem, "concept": concept, "query": query,
                    "pexels_id": v["id"], "url": v["url"],
                    "photographer": v.get("user", {}).get("name"),
                    "duration": v.get("duration"),
                    "width": best.get("width")})
                got += 1
                print(f"OK    {out.stem:20} {best.get('width')}px "
                      f"{v.get('duration')}s  "
                      f"{v.get('user', {}).get('name')}")
        if got == 0:
            print(f"MISS  {concept}: nothing usable")

    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    clips = sorted(DEST.glob("*.mp4"))
    print(f"\npool now {len(clips)} clips")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
