#!/usr/bin/env python3
"""Promote screened broll7 clips into the allow-list the builder reads.

Nothing reaches the film except through manifest/broll_allow.json. This script
is the only door, and it will not open it for a clip that has no verdict:
an unscreened clip is not "probably fine", it is unscreened, and that is how
five Joe Rogan singles and two pure green frames once got through a machine
pass.

Groups are named `s<segment>` so the builder's group and the sentence being
spoken are the same thing. The V8 groups in the file are left untouched - the
bite overflow slots still fall back to them.

Usage:  py -3.12 pipeline/allow_broll7.py          (writes)
        py -3.12 pipeline/allow_broll7.py --dry    (reports only)
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "library/broll7"
ALLOW = ROOT / "manifest/broll_allow.json"
VERDICTS = ROOT / "manifest/broll7_verdicts.json"
MIN_LUMA = 12.0   # below this a clip reads as a blank screen


def group_of(stem: str) -> str:
    if stem.startswith("sm1_"):
        return "s-1"
    if stem.startswith("s6_5_"):
        return "s6.5"
    return stem.split("_")[0]


def duration(p: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(p)],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return round(float(out), 2)
    except Exception:                                            # noqa: BLE001
        return 0.0


def main() -> int:
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
    clips = sorted(SRC.glob("*.mp4"))
    unscreened = [c.stem for c in clips if c.stem not in verdicts]
    if unscreened:
        print(f"[STOP] {len(unscreened)} clips have no verdict; screen them "
              f"first:\n   {unscreened[:8]}")
        return 1

    keep = [c for c in clips if verdicts[c.stem].get("ok")]
    print(f"[allow] {len(keep)} of {len(clips)} clips passed screening",
          flush=True)

    # BRIGHTNESS GATE. A clip can be correct in subject and still be a blank
    # screen: segment 19 shipped with 11.4 SECONDS of near-black (mean
    # luminance 2.5/255) under "there is no cure", because both surviving
    # clips were starfields. ffmpeg's blackdetect found it; the contact sheet
    # did not, because a dark frame in a grid just looks like a dark shot.
    # Measured from the screening frames already on disk - no re-decode.
    import numpy as np
    from PIL import Image
    too_dark = []
    for c in list(keep):
        fdir = ROOT / "work/broll7_frames" / c.stem
        vals = []
        for f in sorted(fdir.glob("*.jpg")):
            try:
                vals.append(float(np.asarray(
                    Image.open(f).convert("L"), dtype=float).mean()))
            except Exception:                                    # noqa: BLE001
                pass
        if vals and sum(vals) / len(vals) < MIN_LUMA:
            too_dark.append((c.stem, sum(vals) / len(vals)))
            keep.remove(c)
    if too_dark:
        print(f"[dark] {len(too_dark)} clip(s) below {MIN_LUMA}/255 mean "
              f"luminance, held back:")
        for stem, m in too_dark:
            print(f"        {stem}  {m:.1f}")

    with ThreadPoolExecutor(max_workers=8) as ex:
        durs = list(ex.map(duration, keep))

    groups: dict[str, list] = {}
    for c, d in zip(keep, durs):
        if d <= 0:
            print(f"  [skip] {c.stem}: unreadable duration")
            continue
        v = verdicts[c.stem]
        note = v.get("note") or "screened: no logo, no text, subject matches"
        groups.setdefault(group_of(c.stem), []).append({
            "file": f"library/broll7/{c.name}",
            "duration": d,
            "class": "OBJECT",
            "crop": None,
            "note": f"broll7 eyes-on pass - {note}",
        })

    for g in groups:
        groups[g].sort(key=lambda it: -it["duration"])

    allow = json.loads(ALLOW.read_text(encoding="utf-8")) if ALLOW.exists() \
        else {}
    before = sum(len(v) for v in allow.values())
    allow.update(groups)          # replace, so a re-run is idempotent
    after = sum(len(v) for v in allow.values())

    print(f"[groups] {len(groups)} segment groups, "
          f"{sum(len(v) for v in groups.values())} clips")
    thin = sorted((g for g in groups if len(groups[g]) < 2),
                  key=lambda g: float(g[1:]))
    if thin:
        print(f"[thin] one clip only: {thin}")

    if "--dry" in sys.argv:
        print("[dry] nothing written")
        return 0

    ALLOW.write_text(json.dumps(allow, indent=1), encoding="utf-8")
    print(f"[OK] {ALLOW}  {before} -> {after} clips, "
          f"{len(allow)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
