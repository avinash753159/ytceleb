#!/usr/bin/env python3
"""
fetch_pexels_hd.py - expand the clean pool with 1080p stock exercise clips.

Pexels stock is watermark-free, so nearly all of it survives the OCR gate;
this directly lifts library survival and gives exercise_demo real coverage.
Downloads the best 1920x1080 file per result into pexels_videos/hd_*.mp4.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
OUT = ROOT / "pexels_videos"
KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")

QUERIES = [
    ("man barbell squat gym", 3), ("man deadlift barbell gym", 3),
    ("man pull ups gym", 3), ("man bench press chest gym", 3),
    ("man dumbbell curl biceps", 3), ("man overhead press shoulders", 3),
    ("man kettlebell swing workout", 3), ("man battle ropes training", 3),
    ("man jump rope boxing", 3), ("man sprinting track running", 3),
    ("man boxing training pads", 3), ("man foam rolling stretching", 3),
    ("healthy meal prep chicken rice", 3), ("protein shake gym", 2),
    ("man walking lunges gym", 2), ("man rowing machine cardio", 2),
]


def main():
    OUT.mkdir(exist_ok=True)
    got = 0
    for q, n in QUERIES:
        url = ("https://api.pexels.com/v1/videos/search?" +
               urllib.parse.urlencode({"query": q, "per_page": n + 2,
                                       "orientation": "landscape",
                                       "size": "medium"}))
        req = urllib.request.Request(url, headers={"Authorization": KEY})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"[!] search failed '{q}': {e}")
            continue
        taken = 0
        for v in data.get("videos", []):
            if taken >= n:
                break
            files = [f for f in v.get("video_files", [])
                     if f.get("width") == 1920 and f.get("height") == 1080]
            if not files:
                continue
            slug = q.replace(" ", "_")[:28]
            dest = OUT / f"hd_{slug}_{v['id']}.mp4"
            if dest.exists():
                taken += 1
                continue
            try:
                urllib.request.urlretrieve(files[0]["link"], dest)
                if dest.stat().st_size > 300_000:
                    taken += 1
                    got += 1
                    print(f"  [OK] {dest.name} "
                          f"({dest.stat().st_size / 1e6:.0f} MB)")
                else:
                    dest.unlink()
            except Exception as e:
                print(f"  [!] dl failed: {e}")
        time.sleep(0.5)
    print(f"[OK] {got} new HD stock clips")


if __name__ == "__main__":
    main()
