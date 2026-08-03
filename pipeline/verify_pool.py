#!/usr/bin/env python3
"""Record the eyes-on identity verdict for each pooled window.

Rejections were read off the contact sheets in work/jimmy_pool. Indices are
in the same order the sheets were built (sorted filename), so they line up
with the tiles. Anything not verified as Jimmy can never be drawn.

Rejected and why:
  Rogan            title card, two Joe Rogan singles, a second pair of Joe
                   singles, and a wide two-shot of the whole studio
  Diary of a CEO   four Steven Bartlett singles, one on-screen graphic, and
                   a PURE GREEN FRAME that would have been catastrophic
  Colin and Samir  two host two-shots and a wide of the empty room, plus a
                   green frame
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "manifest/jimmy_pool.json"
WORK = ROOT / "work/jimmy_pool"

REJECT = {
    "cLRLEnPaJLM": {0, 4, 5, 12, 13, 14},
    "FjrJ2DJN_pA": {3, 7, 12, 13, 14, 15},
    "9IQ_ldV9z_A": {2, 4, 6},
}


def main() -> int:
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    by_thumb = {e["thumb"]: e for e in pool}

    for sid, bad in REJECT.items():
        thumbs = sorted(p.name for p in WORK.glob(f"{sid}_*.jpg"))
        for i, name in enumerate(thumbs):
            e = by_thumb.get(name)
            if e is None:
                continue
            e["verified_jimmy"] = i not in bad
        kept = sum(1 for n in thumbs
                   if by_thumb.get(n, {}).get("verified_jimmy"))
        print(f"{sid:14} {len(thumbs):3d} scanned -> {kept:3d} verified "
              f"Jimmy, {len(bad)} rejected")

    verified = [e for e in pool if e.get("verified_jimmy")]
    POOL.write_text(json.dumps(pool, indent=2), encoding="utf-8")
    print(f"\npool: {len(verified)} verified windows of Jimmy "
          f"(was 11 used across the whole film)")
    per = {}
    for e in verified:
        per[e["source"]] = per.get(e["source"], 0) + 1
    for k, v in per.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
