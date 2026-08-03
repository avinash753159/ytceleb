#!/usr/bin/env python3
"""Build a WIDE pool of cut-bounded windows of Jimmy, across every source.

Why this replaces jimmy_pool.py
-------------------------------
1. `verify_pool.py` recorded the eyes-on verdicts as *sheet indices*. Adding a
   source re-sorts the thumbnails, every index shifts, and the two pure green
   frames and nine host singles that were rejected quietly come back. Verdicts
   here are keyed by `sid@t0`, which never moves.
2. Three sources were scanned. There are ten on disk, including the 115-minute
   Colin & Samir that had never been touched.
3. MIN_RUN was 7.0s, so only runs long enough for a 6s shot survived. No shot
   in this film is over 6s and most are 4-5s, so 3.2s runs are usable and
   there are far more of them.
4. A frame that is nearly all one colour - the green decode artefacts - passed
   dHash dedupe because they were the only two of their kind. They are now
   rejected arithmetically before a human ever sees them, and the eyes-on pass
   is a second net rather than the only one.

Coarse/fine split: cut detection here is downscaled and fast, and is only
good enough to *propose* windows. Every window that actually gets rendered is
re-checked at full resolution over its exact span by mrbeast_picture_v8.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"
WORK = ROOT / "work/jimmy_pool2"
OLD = ROOT / "work/jimmy_pool"
POOL = ROOT / "manifest/jimmy_pool2.json"
FONT = "graphics/public/fonts/Anton-Regular.ttf"

# sid -> (dir, credit_main, credit_sub, candidates_wanted)
#
# EXCLUDED BY CONSTRUCTION, not by filtering:
#   7r3ORKgNUjw  Airrack        - 12 windows checked, no Jimmy-only window
#   WwVs1qVaOb4  Chris Hemsworth- his gym, his crew, his burned-in graphics
#   2XVcLrB7B3Y  Minecraft trap - no Jimmy on screen at all
#   8TFq_vvO_Wg  first video    - screen recording, no Jimmy on screen
SOURCES = {
    "cLRLEnPaJLM": (SRC, "POWERFULJRE", "JOE ROGAN EXPERIENCE #1788", 200),
    "FjrJ2DJN_pA": (SRC, "THE DIARY OF A CEO", "YOUTUBE", 200),
    "9IQ_ldV9z_A": (SRC, "COLIN AND SAMIR", "YOUTUBE / JUNE 2023", 200),
    "c8VcUnz3nVc": (SRC, "COLIN AND SAMIR",
                    "THE FULL STORY OF MRBEAST", 200),
    "NdjcGrpNSF4": (SRC, "JON YOUSHAEI",
                    "INSIDE MRBEAST'S YOUTUBE MACHINE", 40),
    "cWEUE8X7p-k": (SRC, "MRBEAST", "BEAST GAMES / BEHIND THE SCENES", 40),
    "AKJfakEsgy0": (ARC, "MRBEAST", "HI ME IN 5 YEARS / 2013 ARCHIVE", 22),
    "F0OkwXKcPSE": (ARC, "MRBEAST", "HI ME IN 10 YEARS / ARCHIVE", 22),
}

MIN_RUN = 3.2        # shortest run we can place a shot inside
MAX_SHOT = 6.0
SCENE = 0.30

# Candidate-stage dedupe only has to throw out windows that are literally the
# same picture. At 14 it threw out 125 of 140 windows per interview - inside
# one interview almost every frame is the same set, so a strict bar here
# starves a film that needs ~150 distinct shots. Visible repetition is the
# ALLOCATOR's job (mrbeast_picture_v8 refuses near-matches that land close
# together in the programme); this is just an artefact filter.
HAMMING = 9

# Calibrated on the 41 already-labelled thumbnails in work/jimmy_pool, NOT
# guessed. First guess was std<14 / max-channel>0.42, which rejected every
# usable frame in the film: the Rogan studio is a red curtain, so a genuine
# Jimmy single measures max-channel 0.505-0.532, and a dark single measures
# luma std 13.7. Real frames occupy std 13.7-62 and max-channel 0.34-0.53.
# A pure green decode artefact is std 0.0 / G 0.99 and a black slate is
# std 0.0, so the thresholds belong far outside the real range, not beside it.
FLAT_STD = 6.0       # luma std-dev below this = flat frame
CHROMA_MAX = 0.72    # single-channel dominance above this = decode artefact


def probe_dur(p: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True,
        timeout=300).stdout.strip() or 0.0)


def scan_cuts(sid: str, src: Path) -> list[float]:
    """Camera-cut times across the whole file. Downscaled: this only has to
    be good enough to propose windows."""
    cache = WORK / f"{sid}_cuts.json"
    if cache.exists():
        return json.loads(cache.read_text())
    legacy = OLD / f"{sid}_cuts.json"          # 3 sources already cost hours
    if legacy.exists():
        cuts = json.loads(legacy.read_text())
        cache.write_text(json.dumps(cuts))
        print(f"[scan] {sid}: {len(cuts)} cuts (reused cache)", flush=True)
        return cuts
    print(f"[scan] {sid}: detecting cuts over {probe_dur(src)/60:.0f} min...",
          flush=True)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-threads", "2", "-i", str(src),
         "-an", "-vf", f"scale=320:-2,select='gt(scene,{SCENE})',"
         "metadata=print", "-f", "null", "NUL"],
        capture_output=True, text=True, timeout=14400)
    cuts = sorted(float(m) for m in
                  re.findall(r"pts_time:([\d.]+)", r.stderr or ""))
    cache.write_text(json.dumps(cuts))
    print(f"[scan] {sid}: {len(cuts)} cuts", flush=True)
    return cuts


def runs_for(sid: str, src: Path) -> list[tuple[float, float]]:
    total = probe_dur(src)
    edges = [0.0] + [c for c in scan_cuts(sid, src) if c < total] + [total]
    return [(a, b) for a, b in zip(edges, edges[1:]) if (b - a) >= MIN_RUN]


def spread(runs: list[tuple[float, float]], want: int, total: float):
    """Pick `want` runs spread evenly over the DURATION of the file.

    Striding the run *list* clusters picks wherever the edit is busiest - the
    old scanner sampled a fast-cut first hour and skipped the long takes.
    """
    if len(runs) <= want:
        return runs
    picked, used = [], set()
    for k in range(want):
        target = total * (k + 0.5) / want
        best, bi = None, None
        for i, (a, b) in enumerate(runs):
            if i in used:
                continue
            d = abs((a + b) / 2 - target)
            if best is None or d < best:
                best, bi = d, i
        if bi is not None:
            used.add(bi)
            picked.append(runs[bi])
    return sorted(picked)


def dhash(a: np.ndarray) -> np.ndarray:
    im = Image.fromarray(a).convert("L").resize((9, 8), Image.LANCZOS)
    g = np.asarray(im, dtype=np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def degenerate(a: np.ndarray) -> str | None:
    """Reject flat frames before a human is asked to look at them."""
    g = np.asarray(Image.fromarray(a).convert("L"), dtype=np.float32)
    if float(g.std()) < FLAT_STD:
        return f"flat frame (luma std {g.std():.1f})"
    f = a.astype(np.float32) + 1.0
    share = f.sum(axis=(0, 1)) / f.sum()
    if float(share.max()) > CHROMA_MAX:
        ch = "RGB"[int(share.argmax())]
        return f"single-channel frame ({ch} {share.max()*100:.0f}%)"
    return None


def thumb(src: Path, t: float, dest: Path) -> np.ndarray | None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-threads", "1",
         "-vf", "scale=320:180", str(dest)], check=False, timeout=300)
    if not dest.exists() or dest.stat().st_size == 0:
        return None
    return np.asarray(Image.open(dest).convert("RGB"))


def sample_source(sid: str) -> list[dict]:
    d, main, sub, want = SOURCES[sid]
    src = d / f"{sid}.mp4"
    if not src.exists():
        print(f"[skip] {sid} not on disk")
        return []
    total = probe_dur(src)
    runs = runs_for(sid, src)
    picks = spread(runs, want * 2, total)
    print(f"[{sid}] {len(runs)} runs >= {MIN_RUN}s, probing {len(picks)}",
          flush=True)

    got, hashes, dropped = [], [], {"flat": 0, "dupe": 0, "fail": 0}
    for a, b in picks:
        if len(got) >= want:
            break
        t0 = a + 0.35
        span = min(b - 0.25, t0 + MAX_SHOT) - t0
        if span < MIN_RUN - 0.5:
            continue
        key = f"{sid}@{t0:.2f}"
        tp = WORK / f"{sid}_{t0:.0f}.jpg"
        arr = thumb(src, t0 + span / 2, tp)
        if arr is None:
            dropped["fail"] += 1
            continue
        why = degenerate(arr)
        if why:
            dropped["flat"] += 1
            tp.unlink(missing_ok=True)
            continue
        h = dhash(arr)
        if any(int(np.count_nonzero(h != g)) < HAMMING for g in hashes):
            dropped["dupe"] += 1
            tp.unlink(missing_ok=True)
            continue
        hashes.append(h)
        got.append({"key": key, "source": sid, "dir": d.name,
                    "t0": round(t0, 2), "run_end": round(b - 0.25, 2),
                    "run_len": round(b - a, 2),
                    "credit_main": main, "credit_sub": sub,
                    "thumb": tp.name, "verified_jimmy": None})
    print(f"[{sid}] kept {len(got)}  (flat {dropped['flat']}, "
          f"near-dupe {dropped['dupe']}, unreadable {dropped['fail']})",
          flush=True)
    return got


def sheets(entries: list[dict]) -> None:
    """Contact sheets with the KEY burned onto every tile.

    The old sheets were unlabelled, so a verdict could only be expressed as
    'tile 7' - which is exactly how the index drift got in.
    """
    by_src: dict[str, list[dict]] = {}
    for e in entries:
        by_src.setdefault(e["source"], []).append(e)
    for sid, es in by_src.items():
        es = sorted(es, key=lambda e: e["t0"])
        for page in range(0, len(es), 20):
            grp = es[page:page + 20]
            ins, sc = [], []
            for i, e in enumerate(grp):
                ins += ["-i", str(WORK / e["thumb"])]
                lab = f"{i+1}  {e['t0']:.0f}s"
                sc.append(
                    f"[{i}:v]scale=320:180,drawbox=x=0:y=156:w=320:h=24"
                    f":color=black@0.75:t=fill,"
                    f"drawtext=fontfile='{FONT}':text='{lab}'"
                    f":fontcolor=#FFE04D:fontsize=19:x=6:y=158[a{i}]")
            cols = 5
            lay = "|".join(f"{(i % cols)*320}_{(i//cols)*180}"
                           for i in range(len(grp)))
            lb = "".join(f"[a{i}]" for i in range(len(grp)))
            out = WORK / f"sheet_{sid}_{page//20}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
                 "-filter_complex",
                 f"{';'.join(sc)};{lb}xstack=inputs={len(grp)}:layout={lay}",
                 "-frames:v", "1", "-q:v", "3", str(out)],
                check=False, timeout=900)
            idx = out.with_suffix(".json")
            idx.write_text(json.dumps(
                [{"tile": i + 1, "key": e["key"], "t0": e["t0"],
                  "thumb": e["thumb"]} for i, e in enumerate(grp)], indent=2),
                encoding="utf-8")
            print(f"[sheet] {out.name}  {len(grp)} tiles", flush=True)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or list(SOURCES)

    # Cut detection is the long pole and is pure decode: run the files in
    # parallel, each pinned to 2 threads (14 workers x 20 threads once
    # starved this machine so badly PowerShell could not start a thread).
    todo = [s for s in only
            if not (WORK / f"{s}_cuts.json").exists()
            and not (OLD / f"{s}_cuts.json").exists()]
    if todo:
        with ThreadPoolExecutor(max_workers=min(5, len(todo))) as ex:
            futs = {ex.submit(scan_cuts, s, SOURCES[s][0] / f"{s}.mp4"): s
                    for s in todo}
            for f in as_completed(futs):
                f.result()

    entries: list[dict] = []
    for sid in only:
        entries += sample_source(sid)

    # Carry forward verdicts already given by eye, matched on the key.
    prior: dict[str, bool] = {}
    if POOL.exists():
        for e in json.loads(POOL.read_text(encoding="utf-8")):
            if e.get("verified_jimmy") is not None:
                prior[e["key"]] = e["verified_jimmy"]
    for e in entries:
        if e["key"] in prior:
            e["verified_jimmy"] = prior[e["key"]]

    POOL.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    sheets([e for e in entries if e["verified_jimmy"] is None])
    n_open = sum(1 for e in entries if e["verified_jimmy"] is None)
    print(f"\n[OK] {len(entries)} candidates -> {POOL}")
    print(f"     {n_open} awaiting the eyes-on identity pass")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    raise SystemExit(main())
