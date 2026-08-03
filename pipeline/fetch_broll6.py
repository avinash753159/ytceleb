#!/usr/bin/env python3
"""Fetch the people-based stock the owner's notes now call for.

Rule 9 has been relaxed: anonymous people may perform the activity. It still
holds that no child is cast as young Jimmy and no other identifiable creator
appears. These are the looks the deck notes asked for by name - "someone
editing on YouTube", "a guy eating and having issues", an athlete - none of
which the object-only library could supply.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "library/broll6"
KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

WANT = {
    "editing": ["editing software timeline screen", "person at editing suite",
                "video editing workspace night", "creator studio camera setup",
                "uploading video progress bar", "youtube on screen"],
    "gut_pain": ["man clutching stomach pain", "person doubled over pain",
                 "man unwell bathroom door", "person holding abdomen ache",
                 "man discomfort sitting"],
    "eating": ["man pushing food around plate", "person eating slowly alone",
               "plain meal being eaten", "man declining food"],
    "athlete": ["young man running outdoors", "athlete sprint training",
                "man throwing ball field", "sports field practice adult",
                "runner morning road"],
    "tired": ["man lying awake bed", "person exhausted couch",
              "man head in hands tired", "person sleeping daytime",
              "tired man morning"],
    "training": ["man lifting barbell gym", "person bench press",
                 "man dumbbell curl gym", "gym workout session man",
                 "man treadmill running"],
    "walk2": ["man walking city pavement", "person walking park path",
              "walking feet street level", "man walking morning"],
    "night_work": ["man working late night desk", "person laptop dark room",
                   "late night computer glow"],
}
MIN_DUR, MAX_DUR, PER = 7, 40, 7


def api(url: str) -> dict:
    r = urllib.request.Request(
        url, headers={"Authorization": KEY, "User-Agent": UA})
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    # Skip anything this project has already downloaded. An audit found 8 of
    # 56 clips in one round were re-downloads of ids already cleared into the
    # allow-list.
    import sys as _s
    _s.path.insert(0, str(ROOT / "pipeline"))
    from fetched_ids import known_ids
    seen = known_ids()
    print(f"[skip] {len(seen)} ids already downloaded project-wide",
          flush=True)
    cred, n = [], 0
    for g, qs in WANT.items():
        got = 0
        for q in qs:
            if got >= PER:
                break
            try:
                d = api("https://api.pexels.com/videos/search?"
                        + urllib.parse.urlencode(
                            {"query": q, "per_page": 14,
                             "orientation": "landscape", "size": "medium"}))
            except Exception as e:                              # noqa: BLE001
                print(f"[warn] {q}: {e}")
                continue
            for v in d.get("videos", []):
                if got >= PER:
                    break
                vid, dur = v.get("id"), v.get("duration") or 0
                if vid in seen or not (MIN_DUR <= dur <= MAX_DUR):
                    continue
                files = [f for f in (v.get("video_files") or [])
                         if (f.get("width") or 0) >= 1280
                         and (f.get("width") or 0) >= (f.get("height") or 1)]
                if not files:
                    continue
                f = sorted(files, key=lambda x: -(x.get("width") or 0))[0]
                dst = DEST / f"{g}_{vid}.mp4"
                try:
                    rq = urllib.request.Request(
                        f["link"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(rq, timeout=300) as r2:
                        dst.write_bytes(r2.read())
                except Exception as e:                          # noqa: BLE001
                    print(f"[warn] download {vid}: {e}")
                    continue
                seen.add(vid)
                got += 1
                n += 1
                cred.append({
                    "file": f"library/broll6/{dst.name}", "group": g,
                    "query": q, "pexels_id": vid, "url": v.get("url"),
                    "photographer": (v.get("user") or {}).get("name"),
                    "duration": dur, "width": f.get("width"),
                    "height": f.get("height"),
                    "license": "Pexels licence - credited in description"})
                print(f"  {dst.name}  {dur}s  {f.get('width')}x"
                      f"{f.get('height')}  [{q}]", flush=True)
        print(f"[{g}] {got}", flush=True)
    (DEST / "CREDITS.json").write_text(
        json.dumps(cred, indent=2), encoding="utf-8")
    print(f"\n[OK] {n} clips -> {DEST}")
    print("     still needs the eyes-on pass before anything is drawn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
