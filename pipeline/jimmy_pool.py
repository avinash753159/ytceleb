#!/usr/bin/env python3
"""Build a large pool of distinct, cut-bounded windows of Jimmy on camera.

There are 8.3 hours of him across three interviews and the film had been
drawing from about eleven windows. This scans the whole of each source,
finds runs with no camera cut in them, samples a frame per run, discards
perceptual near-duplicates, and writes a pool the picture build can draw
from without ever repeating a shot.

Speaker identity is confirmed by eye on the contact sheets this writes -
the pool is candidates, not verified Jimmy, until that pass is done.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources"
WORK = ROOT / "work/jimmy_pool"
POOL = ROOT / "manifest/jimmy_pool.json"

SOURCES = {
    "cLRLEnPaJLM": ("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"),
    "FjrJ2DJN_pA": ("THE DIARY OF A CEO", "YOUTUBE"),
    "9IQ_ldV9z_A": ("COLIN AND SAMIR", "YOUTUBE / JUNE 2023"),
}
SHOT = 6.0          # window length we want to be able to cut
MIN_RUN = 7.0       # a run must comfortably contain it
PER_SOURCE = 45     # candidates to keep per interview
HAMMING = 13        # below this, two windows look the same


def scan_cuts(src: Path) -> list[float]:
    cache = WORK / f"{src.stem}_cuts.json"
    if cache.exists():
        return json.loads(cache.read_text())
    print(f"[scan] {src.stem} - detecting cuts across the whole file...",
          flush=True)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vf",
         "select='gt(scene,0.32)',metadata=print", "-an", "-f", "null",
         "NUL"], capture_output=True, text=True, timeout=7200)
    cuts = sorted(float(m) for m in
                  re.findall(r"pts_time:([\d.]+)", r.stderr or ""))
    cache.write_text(json.dumps(cuts))
    print(f"[scan] {src.stem}: {len(cuts)} cuts", flush=True)
    return cuts


def dhash(p: Path) -> np.ndarray:
    a = np.asarray(Image.open(p).convert("L").resize((9, 8), Image.LANCZOS),
                   dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    pool = []
    for sid, (main, sub) in SOURCES.items():
        src = SRC / f"{sid}.mp4"
        if not src.exists():
            continue
        total = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(src)], capture_output=True,
            text=True).stdout.strip())
        cuts = scan_cuts(src)
        edges = [0.0] + cuts + [total]
        runs = [(a, b) for a, b in zip(edges, edges[1:])
                if (b - a) >= MIN_RUN]
        # spread candidates across the whole interview, not the first hour
        step = max(1, len(runs) // (PER_SOURCE * 2))
        picks = runs[::step][:PER_SOURCE * 2]
        print(f"[{sid}] {len(runs)} usable runs, sampling {len(picks)}",
              flush=True)

        hashes: list[np.ndarray] = []
        kept = 0
        for a, b in picks:
            if kept >= PER_SOURCE:
                break
            t0 = a + 0.4
            mid = t0 + SHOT / 2
            thumb = WORK / f"{sid}_{int(t0)}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{mid:.2f}", "-i", str(src), "-frames:v", "1",
                 "-vf", "scale=240:135", str(thumb)],
                check=False, timeout=300)
            if not thumb.exists() or thumb.stat().st_size == 0:
                continue
            h = dhash(thumb)
            if any(int(np.count_nonzero(h != g)) < HAMMING for g in hashes):
                thumb.unlink(missing_ok=True)
                continue
            hashes.append(h)
            kept += 1
            pool.append({"source": sid, "t0": round(t0, 2),
                         "run_len": round(b - a, 2),
                         "credit_main": main, "credit_sub": sub,
                         "thumb": thumb.name, "verified_jimmy": None})
        print(f"[{sid}] kept {kept} visually distinct windows", flush=True)

    POOL.parent.mkdir(parents=True, exist_ok=True)
    POOL.write_text(json.dumps(pool, indent=2), encoding="utf-8")

    # contact sheets, one per source, for the identity pass
    for sid in SOURCES:
        tiles = sorted(WORK.glob(f"{sid}_*.jpg"))
        if not tiles:
            continue
        for page in range(0, len(tiles), 24):
            grp = tiles[page:page + 24]
            ins = []
            for t in grp:
                ins += ["-i", str(t)]
            n = len(grp)
            cols = 6
            lay = "|".join(f"{(i % cols)*240}_{(i//cols)*135}"
                           for i in range(n))
            sc = ";".join(f"[{i}:v]scale=240:135[a{i}]" for i in range(n))
            lb = "".join(f"[a{i}]" for i in range(n))
            out = WORK / f"sheet_{sid}_{page//24}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
                 "-filter_complex", f"{sc};{lb}xstack=inputs={n}:layout={lay}",
                 "-frames:v", "1", str(out)], check=False, timeout=600)
            print(f"[sheet] {out.name}  ({n} windows)", flush=True)

    print(f"\n[OK] {len(pool)} candidate windows -> {POOL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
