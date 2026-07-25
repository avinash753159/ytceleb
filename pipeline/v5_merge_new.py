#!/usr/bin/env python3
"""v5_merge_new.py - after downloads land, upgrade 'library' beats to 'cut'
where the planned source file NOW exists. NEVER touches beats already
verified, operator-locked, or verify-failed (those swaps were deliberate)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOSS = ROOT / "dossier" / "ryan"

a5 = json.loads((MAN / "assets_v5.json").read_text())
plan = json.loads((MAN / "v5_plan.json").read_text())


def parse_range(ts):
    m = re.match(r"(\d+):(\d+)\s+to\s+(\d+):(\d+)", ts)
    if not m:
        return None
    return (int(m.group(1)) * 60 + int(m.group(2)),
            int(m.group(3)) * 60 + int(m.group(4)))


up = 0
for bid, a in a5.items():
    if a["type"] != "library" or "verify-fail" in str(a.get("note", "")):
        continue
    for c in plan.get(bid, []):
        m = re.search(r"watch\?v=([\w-]{11})", c["url"])
        rng = parse_range(c["ts"])
        if m and rng:
            f = DOSS / f"{m.group(1)}.mp4"
            if f.exists() and f.stat().st_size > 300_000:
                a5[bid] = {"type": "cut", "src": str(f), "t0": rng[0],
                           "t1": rng[1], "vid": m.group(1),
                           "title": c["title"][:60]}
                up += 1
                break
json.dump(a5, open(MAN / "assets_v5.json", "w"), indent=1)
from collections import Counter
print("upgraded to cut:", up, "|",
      dict(Counter(v["type"] for v in a5.values())))
