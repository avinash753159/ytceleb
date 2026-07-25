#!/usr/bin/env python3
"""v5_download.py - download every clip-plan source IN FULL to dossier/ryan/.
Full downloads kill the --download-sections PTS corruption for good.
Skips existing files; caps at 720-1080p mp4."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dossier" / "ryan"
OUT.mkdir(parents=True, exist_ok=True)

srcs = json.loads((ROOT / "manifest" / "v5_sources.json").read_text())
ok = fail = skip = 0
for vid, title in srcs.items():
    dest = OUT / f"{vid}.mp4"
    if dest.exists() and dest.stat().st_size > 500_000:
        skip += 1
        continue
    print(f"[*] {vid} {title[:46]}", flush=True)
    r = subprocess.run(
        ["yt-dlp", "-f", "bv*[height<=1080][height>=480]+ba/b[height<=1080]",
         "--merge-output-format", "mp4", "--no-playlist",
         "-o", str(dest), f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=1200)
    if dest.exists() and dest.stat().st_size > 500_000:
        ok += 1
        print(f"    OK {dest.stat().st_size/1e6:.0f} MB")
    else:
        fail += 1
        print(f"    FAIL {(r.stderr or '')[-120:]}")
print(f"[DONE] ok={ok} skip={skip} fail={fail} of {len(srcs)}")
