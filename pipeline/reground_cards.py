#!/usr/bin/env python3
"""Bring the six V7 cards onto the same ground as the twelve V8 cards.

The V7 six (`card_weight`, `card_310`, `card_steps`, `card_time`, `card_rest`,
`card_record`) sit at a darkest-pixel luma of 9-10, i.e. essentially the
#0A0A0C that once tripped blackdetect and read as the film having died. The
V8 twelve sit at luma 20-21 and carry a 22px #E3120B bar down the left edge.
Side by side they look like two different films.

Lifting is done with a `lighten` blend against a flat ground rather than a
brightness curve: lighten raises every pixel darker than the ground up to the
ground and leaves the type and artwork untouched, so nothing is washed out.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "work/cards"
BACKUP = CARDS / "v7_original"
GROUND = "#221116"        # #191419 plus the 6% #E3120B wash
ACCENT = "#E3120B"
V7 = ["card_weight", "card_310", "card_steps", "card_time", "card_rest",
      "card_record"]


def luma_floor(p: Path) -> int:
    import numpy as np
    from PIL import Image
    return int(np.asarray(Image.open(p).convert("L")).min())


def main() -> int:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for key in V7:
        src = CARDS / f"{key}.png"
        if not src.exists():
            print(f"[skip] {key} not present")
            continue
        keep = BACKUP / f"{key}.png"
        if not keep.exists():
            shutil.copy2(src, keep)
        before = luma_floor(src)
        tmp = CARDS / f"_{key}_reground.png"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(keep), "-f", "lavfi", "-i",
             f"color=c={GROUND}:s=1920x1080", "-filter_complex",
             "[1:v][0:v]blend=all_mode=lighten:shortest=1,"
             f"drawbox=x=0:y=0:w=22:h=1080:color={ACCENT}:t=fill",
             "-frames:v", "1", str(tmp)], check=True, timeout=300)
        tmp.replace(src)
        print(f"[reground] {key}: darkest luma {before} -> "
              f"{luma_floor(src)}, accent bar added")
    print(f"\noriginals kept in {BACKUP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
