#!/usr/bin/env python3
"""OCR-screen every candidate window for burned-in third-party text.

Why six frames, not one
-----------------------
The eyes-on identity pass looks at ONE frame per window - its midpoint - and
that is not enough. Rogan pulled the Crohn's & Colitis Foundation website up
on a studio monitor that sits in the lower right of frame, and it comes and
goes mid-window: the midpoint frame of the "it's just life" window is clean
and the panel arrives 2.3 seconds later. A one-frame verdict ships it.

Why this does not use clean_windows.scan_many
---------------------------------------------
`scan_many`'s worker hardcodes `frames=2`, and the shared cache key is
`file|t0|dur` with no frame count in it. A 2-frame verdict therefore gets
handed back later to a caller that asked for 6, which is precisely the failure
this screen exists to prevent. Own cache, own key, frame count included.

Why processes
-------------
RapidOCR/onnxruntime does not release the GIL, so a thread pool serialises the
work and adds overhead - a previous session measured 8s per window threaded
against 4.6s sequential. Each worker process is pinned to one thread, and the
parallelism comes from the pool. Sequentially this scan was running at 26s per
window, or nearly two hours for the pool.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "ORT_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"
POOL = ROOT / "manifest/jimmy_pool2.json"
BITES = ROOT / "manifest/bite_windows.json"
CACHE = ROOT / "work/screen_text_cache.json"
FRAMES = 6


def src_for(sid: str) -> Path:
    p = SRC / f"{sid}.mp4"
    return p if p.exists() else ARC / f"{sid}.mp4"


def _worker(job):
    """Top-level so it is picklable. Loads the OCR model once per process."""
    import clean_windows as cw
    key, path, t0, dur = job
    hits: list[str] = []
    for img in cw._frames(Path(path), t0, dur, FRAMES):
        hits += cw._text_in(img)
    ok = not hits
    return key, ok, ("" if ok else
                     "text: " + " / ".join(sorted(set(hits))[:4])[:280])


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def run(jobs: list[tuple], workers: int) -> dict:
    cache = load_cache()
    todo = [j for j in jobs if j[0] not in cache]
    print(f"  {len(jobs)} windows, {len(jobs)-len(todo)} cached, "
          f"{len(todo)} to scan on {workers} processes", flush=True)
    done = 0
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for key, ok, why in ex.map(_worker, todo, chunksize=2):
                cache[key] = [ok, why]
                done += 1
                if not ok:
                    # OCR returns whatever glyphs it saw, including CJK and
                    # fullwidth punctuation. Windows stdout is cp1252 and
                    # raises on those, which killed a run at 60/248 with the
                    # cache half written. The verdict is what matters; the
                    # console rendering of it is not.
                    safe = why[:100].encode("ascii", "replace").decode()
                    print(f"  [text] {key.split('|')[0]}  {safe}", flush=True)
                if done % 20 == 0:
                    print(f"  ...{done}/{len(todo)}", flush=True)
                    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return cache


def main() -> int:
    workers = max(2, min(10, (os.cpu_count() or 8) - 4))

    pool = json.loads(POOL.read_text(encoding="utf-8"))
    jobs = []
    for e in pool:
        dur = min(6.0, max(2.5, e["run_end"] - e["t0"]))
        jobs.append((f"{e['key']}|{dur:.2f}|{FRAMES}",
                     str(src_for(e["source"])), e["t0"], dur))
    print("[pool] screening candidate windows", flush=True)
    cache = run(jobs, workers)
    n_bad = 0
    for e, j in zip(pool, jobs):
        ok, why = cache.get(j[0], (True, ""))
        e["has_text"] = not ok
        e["text_reason"] = why
        n_bad += 0 if ok else 1
    POOL.write_text(json.dumps(pool, indent=2), encoding="utf-8")
    print(f"[pool] {n_bad}/{len(pool)} carry burned-in text\n", flush=True)

    bites = json.loads(BITES.read_text(encoding="utf-8"))
    bjobs, refs = [], []
    for r in bites:
        for w in r["runs"]:
            d = max(2.0, w["usable"])
            bjobs.append((f"{w['key']}|{d:.2f}|{FRAMES}",
                          str(src_for(r["source"])), w["t0"], d))
            refs.append(w)
    print("[bites] screening sync windows", flush=True)
    cache = run(bjobs, workers)
    nb = 0
    for w, j in zip(refs, bjobs):
        ok, why = cache.get(j[0], (True, ""))
        w["has_text"] = not ok
        w["text_reason"] = why
        nb += 0 if ok else 1
    BITES.write_text(json.dumps(bites, indent=2), encoding="utf-8")
    print(f"[bites] {nb}/{len(bjobs)} carry burned-in text", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
