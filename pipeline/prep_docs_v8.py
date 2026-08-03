#!/usr/bin/env python3
"""Capture the three documents the plan needs that were not yet on disk.

All three are real captures. Nothing here draws a document - a hand-lettered
card standing in for evidence is the thing this rebuild exists to remove.

  dash_2015     his own 2015 YouTube dashboard, read off a screen recording
                inside "Hi Me In 5 Years": 8,726 subscribers, 1,830,631 views.
                It is the only hard figure we have for where he started, and
                it is his own upload, not a press estimate.
  his2015card   his own title card, "Today Is October 4th, 2015 ... setting
                this video to go public in 5 years". It dates the archive in
                his handwriting rather than ours, and it carries the 4-second
                music-only title break.
  ccf_page      the Crohn's & Colitis Foundation page. The narration names
                this organisation out loud, so the film should show the actual
                source rather than the NIDDK page a second time.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/docs_v8"
ARC = ROOT / "dossier/mrbeast/archive"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

GRABS = [
    # (dest, source video, timestamp) - timestamps confirmed by eye on the
    # contact sheets in work/jimmy_pool2.
    ("dash_2015.png", ARC / "AKJfakEsgy0.mp4", 12.0),
    ("his2015card.png", ARC / "AKJfakEsgy0.mp4", 1.6),
]


def grab(dest: Path, src: Path, t: float) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
         "-vf", "scale=1920:-2:flags=lanczos", str(dest)],
        check=True, timeout=300)
    print(f"[grab] {dest.name}  from {src.name} @ {t:.2f}s")


def shot(url: str, dest: Path, w=1600, h=1400) -> None:
    """Headless Chrome. A browser User-Agent is not optional on any of these
    hosts; without one the request comes back as a Cloudflare error page that
    looks exactly like a dead endpoint."""
    if not CHROME.exists():
        raise FileNotFoundError(CHROME)
    tmp = dest.with_suffix(".raw.png")
    subprocess.run(
        [str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--user-agent={UA}", f"--window-size={w},{h}",
         "--force-device-scale-factor=2", "--virtual-time-budget=9000",
         f"--screenshot={tmp}", url],
        check=False, timeout=180, capture_output=True)
    if not tmp.exists() or tmp.stat().st_size < 20000:
        raise RuntimeError(f"capture failed or near-empty: {url}")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
         "-vf", "scale=1920:-2:flags=lanczos", str(dest)],
        check=True, timeout=300)
    tmp.unlink(missing_ok=True)
    print(f"[shot] {dest.name}  {url}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, src, t in GRABS:
        grab(OUT / name, src, t)
    try:
        shot("https://www.crohnscolitisfoundation.org/what-is-crohns-disease",
             OUT / "ccf_page.png")
    except Exception as e:                                    # noqa: BLE001
        print(f"[warn] Crohn's & Colitis Foundation capture failed: {e}")
        print("       the plan's seg17 slot needs this - fix before building")
        return 1
    for p in sorted(OUT.glob("*.png")):
        print(f"  {p.name:20} {p.stat().st_size/1024:7.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
