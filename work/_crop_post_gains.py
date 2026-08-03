"""Re-cut the April 2025 post card so the second person is out of frame.

The "Go get gains boyz" photo is a gym mirror shot and the person holding the
phone is in it: a bare arm with a dark watch strap, a dark sleeveless top and
light hair at the top right of the photo. Jimmy is the shirtless figure at
left. Rule 1 is absolute about a second person on screen, and this is on
screen for four seconds.

The card itself stays a real screenshot - the fix is a crop, not a redraw. It
finds the card's bounds against the dark ground, cuts the photo at the point
where the other person begins, and re-centres what is left on the film's
ground so it reads as a cropped screenshot column rather than a broken card.
"""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "work/post_cards/post_gains.png"
OUT = ROOT / "work/post_cards/post_gains_cropped.png"
GROUND = "#0A0A0C"
# Fraction of the CARD's width to keep. The other person occupies the right
# edge of the photo; measured on the composited card, they start at ~0.86.
KEEP = 0.845


def main() -> int:
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(np.int16)
    h, w, _ = a.shape
    # The ground is near-black; the card is not. Find its column extent.
    lum = a.max(axis=2)
    cols = np.where((lum > 40).sum(axis=0) > h * 0.04)[0]
    rows = np.where((lum > 40).sum(axis=1) > w * 0.02)[0]
    x0, x1 = int(cols.min()), int(cols.max())
    y0, y1 = int(rows.min()), int(rows.max())
    print(f"card bounds x {x0}-{x1} ({x1-x0}px)  y {y0}-{y1} ({y1-y0}px)")

    cw = x1 - x0
    keep_w = int(cw * KEEP)
    print(f"keeping {keep_w}px of {cw}px, cutting at x={x0+keep_w}")

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(SRC),
         "-vf",
         f"crop={keep_w}:{y1-y0}:{x0}:{y0},"
         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={GROUND}",
         "-frames:v", "1", str(OUT)], check=True, timeout=300)
    print("[OK]", OUT)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(OUT),
         "-vf", "scale=1100:-2", "-frames:v", "1",
         str(ROOT / "work/qc_v8/pg_fixed.jpg")], check=True, timeout=300)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
