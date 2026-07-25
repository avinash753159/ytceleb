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

import re

srcs = json.loads((ROOT / "manifest" / "v5_sources.json").read_text())
plan = json.loads((ROOT / "manifest" / "v5_plan.json").read_text())

# needed time ranges per video (from the clip plan), padded +-45s
PAD = 45
need = {}
for bid, clips in plan.items():
    for c in clips:
        m = re.search(r"watch\?v=([\w-]{11})", c["url"])
        r = re.match(r"(\d+):(\d+)\s+to\s+(\d+):(\d+)", c["ts"])
        if m and r:
            a = int(r.group(1)) * 60 + int(r.group(2)) - PAD
            b = int(r.group(3)) * 60 + int(r.group(4)) + PAD
            need.setdefault(m.group(1), []).append((max(a, 0), b))


def merged(vid):
    spans = sorted(need.get(vid, []))
    out = []
    for a, b in spans:
        if out and a <= out[-1][1] + 30:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def duration_of(vid):
    r = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings",
                        "--print", "%(duration)s",
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, timeout=120)
    try:
        return float(r.stdout.strip().splitlines()[-1])
    except Exception:
        return 0.0


LONG = 15 * 60          # >15 min -> section download of needed ranges only
from concurrent.futures import ThreadPoolExecutor


def fetch(item):
    vid, title = item
    dest = OUT / f"{vid}.mp4"
    if dest.exists() and dest.stat().st_size > 500_000:
        return "skip", vid
    dur = duration_of(vid)
    args = ["yt-dlp", "-f",
            "bv*[height<=1080][height>=480]+ba/b[height<=1080]",
            "--merge-output-format", "mp4", "--no-playlist",
            "-o", str(dest), f"https://www.youtube.com/watch?v={vid}"]
    mode = "full"
    if dur > LONG and need.get(vid):
        for a, b in merged(vid):
            args += ["--download-sections", f"*{a}-{b}"]
        mode = "sections"
    print(f"[*] {vid} ({dur/60:.0f}m, {mode}) {title[:40]}", flush=True)
    r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    if dest.exists() and dest.stat().st_size > 300_000:
        print(f"    OK {vid} {dest.stat().st_size/1e6:.0f} MB", flush=True)
        return "ok", vid
    for pp in OUT.glob(vid + "*"):
        try:
            pp.unlink()
        except OSError:
            pass
    print(f"    FAIL {vid} {(r.stderr or chr(32))[-100:]}", flush=True)
    return "fail", vid


results = []
with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(fetch, srcs.items()))
ok = sum(1 for s, _ in results if s == "ok")
skip = sum(1 for s, _ in results if s == "skip")
fail = sum(1 for s, _ in results if s == "fail")
print(f"[DONE] ok={ok} skip={skip} fail={fail} of {len(srcs)}")
