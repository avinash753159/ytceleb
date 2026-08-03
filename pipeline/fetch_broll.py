#!/usr/bin/env python3
"""Fetch b-roll that matches what the narration actually says.

The existing loop library is all explosive gym movements - ball slams, rope
climbs, jiu-jitsu. The storyboard needed an empty gym, someone walking, a
person training steadily and a dark bedroom, none of which existed, so the
same wrong clips were being reused under mismatched labels.
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

# key -> (search query, what beat it serves)
WANT = {
    "gym_empty": ("empty gym interior", "lights going off / the machine wins"),
    "gym_lifting": ("man lifting weights gym", "the routine, steadily"),
    "gym_dumbbell": ("dumbbell workout man", "resistance training"),
    "walking_street": ("man walking city street", "15,000 steps"),
    "walking_treadmill": ("person walking treadmill", "daily movement"),
    "bedroom_dark": ("dark bedroom night", "fix sleep first"),
    "calendar_pages": ("calendar pages", "programmed rest / day count"),
    "gym_barbell": ("barbell squat gym", "the verified protocol"),
    "man_tired": ("tired man sitting", "exhaustion / low energy"),
    "clock_time": ("clock time lapse", "protected time"),
}


# Pexels sits behind Cloudflare, which rejects requests with no
# User-Agent as error 1010 - surfaced as a bare 403 that looks exactly
# like a dead API key. It is not; the header is mandatory.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def api(url):
    req = urllib.request.Request(
        url, headers={"Authorization": KEY, "User-Agent": UA,
                      "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as r:
        dest.write_bytes(r.read())


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    ledger = []
    for key, (query, beat) in WANT.items():
        out = DEST / f"{key}.mp4"
        if out.exists():
            print(f"have  {key}")
            continue
        url = ("https://api.pexels.com/videos/search?"
               + urllib.parse.urlencode(
                   {"query": query, "per_page": 8, "orientation": "landscape",
                    "size": "medium"}))
        try:
            data = api(url)
        except Exception as e:  # noqa: BLE001
            print(f"ERR   {key}: {e}")
            continue
        vids = data.get("videos") or []
        if not vids:
            print(f"MISS  {key}: no results for '{query}'")
            continue
        # prefer ~1080p, 5-20s
        best, best_score = None, -1
        for v in vids:
            dur = v.get("duration", 0)
            if not (4 <= dur <= 25):
                continue
            for f in v.get("video_files", []):
                w = f.get("width") or 0
                if 1200 <= w <= 2000 and f.get("file_type") == "video/mp4":
                    score = w - abs(dur - 10) * 20
                    if score > best_score:
                        best, best_score = (v, f), score
        if not best:
            print(f"MISS  {key}: no suitable file")
            continue
        v, f = best
        download(f["link"], out)
        ledger.append({"key": key, "query": query, "beat": beat,
                       "pexels_id": v["id"], "url": v["url"],
                       "photographer": v.get("user", {}).get("name"),
                       "duration": v.get("duration"),
                       "width": f.get("width")})
        print(f"OK    {key:18} {f.get('width')}px {v.get('duration')}s  "
              f"{v.get('user', {}).get('name')}")

    (DEST / "CREDITS.json").write_text(
        json.dumps(ledger, indent=2), encoding="utf-8")
    print(f"\n{len(ledger)} new clips -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
