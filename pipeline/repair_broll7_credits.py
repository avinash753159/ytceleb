#!/usr/bin/env python3
"""Rebuild library/broll7/CREDITS.json for EVERY clip, not just the last batch.

fetch_broll7.py wrote CREDITS.json with `write_text` at the end of each run,
so every top-up round overwrote the attribution for the clips fetched before
it. By the end, 189 clips were in the cut and only 4 had a photographer on
record. Pexels asks for attribution in return for the licence, so this is a
licence problem, not a tidiness one.

The Pexels id survives in every filename (s19_33637800.mp4 -> 33637800), so
the record can be refetched from the API and merged rather than replaced.
"""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "library/broll7"
KEY = os.environ.get("PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

def one(p: Path):
    vid = p.stem.rsplit("_", 1)[-1]
    if not vid.isdigit():
        return None
    try:
        r = urllib.request.Request(
            f"https://api.pexels.com/videos/videos/{vid}",
            headers={"Authorization": KEY, "User-Agent": UA})
        with urllib.request.urlopen(r, timeout=45) as resp:
            d = json.loads(resp.read().decode("utf-8"))
    except Exception as e:                                       # noqa: BLE001
        return {"file": f"library/broll7/{p.name}", "pexels_id": int(vid),
                "photographer": None, "url": None,
                "error": type(e).__name__}
    return {"file": f"library/broll7/{p.name}", "pexels_id": int(vid),
            "photographer": (d.get("user") or {}).get("name"),
            "photographer_url": (d.get("user") or {}).get("url"),
            "url": d.get("url"), "duration": d.get("duration"),
            "license": "Pexels licence - credited in the description"}

def main() -> int:
    clips = sorted(DEST.glob("*.mp4"))
    print(f"[repair] {len(clips)} clips", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        recs = [r for r in ex.map(one, clips) if r]
    named = sum(1 for r in recs if r.get("photographer"))
    (DEST / "CREDITS.json").write_text(json.dumps(recs, indent=2),
                                       encoding="utf-8")
    print(f"[OK] {named}/{len(recs)} clips now carry a photographer")
    bad = [r for r in recs if not r.get("photographer")]
    if bad:
        print(f"[warn] {len(bad)} unresolved: {[r['pexels_id'] for r in bad][:6]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
