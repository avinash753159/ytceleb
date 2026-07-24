#!/usr/bin/env python3
"""
ingest_ocr.py - Phase 1 gate: zero burned-in text reaches the timeline.

For every scene in shot_index.json:
  * sample 3 keyframes (20% / 50% / 80% through the scene)
  * run RapidOCR on the bottom 30% and top 15% bands of each frame
  * any detection with confidence > 0.5 AND bbox area > 0.4% of the full
    frame -> has_burned_text: true  -> REJECT (default policy)
  * resolution gate: source video below 1280x720 -> REJECT

Outputs (all under library/):
  shots.jsonl       every scene, verdict + evidence   (the clean-pool DB)
  quarantine.jsonl  rejected scenes with the detected text (auditable)
  ingest_report.json  survival stats

Run:  py -3.12 pipeline/ingest_ocr.py            # full backfill
      py -3.12 pipeline/ingest_ocr.py --limit 40 # smoke test
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
INDEX_FILE = ROOT / "shot_index.json"

CONF_MIN = 0.5          # OCR confidence threshold
AREA_MIN = 0.004        # bbox area > 0.4% of full frame
BOTTOM_BAND = 0.30      # bottom 30% of frame
TOP_BAND = 0.15         # top 15% of frame
MIN_SCENE = 1.2         # scenes shorter than this never reach the timeline
MIN_W, MIN_H = 1280, 720


def probe_res(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30)
    try:
        w, h = r.stdout.strip().split("\n")[0].split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


def extract_frame(src, t, out):
    if out.exists():
        return out.exists()
    subprocess.run(
        ["ffmpeg", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
         "-q:v", "3", "-y", str(out)],
        capture_output=True, timeout=60)
    return out.exists()


def scene_list():
    """(source_path, scene_idx, a, b) for every usable scene."""
    cache = json.loads(INDEX_FILE.read_text())
    scenes = []
    for src, meta in cache.items():
        p = Path(src)
        if not p.exists():
            continue
        dur = meta["duration"]
        cuts = [c for c in meta["cuts"] if 0.5 < c < dur - 0.5]
        bounds = [0.0] + cuts + [dur]
        for si in range(len(bounds) - 1):
            a, b = bounds[si], bounds[si + 1]
            if b - a >= MIN_SCENE:
                scenes.append((p, si, a, b))
    return scenes


def ocr_bands(ocr, img_path):
    """OCR the masked bands. Returns list of (text, conf, area_ratio, band)."""
    import cv2
    img = cv2.imread(str(img_path))
    if img is None:
        return []
    H, W = img.shape[:2]
    frame_area = float(H * W)
    hits = []
    bands = [("bottom", img[int(H * (1 - BOTTOM_BAND)):, :]),
             ("top", img[:int(H * TOP_BAND), :])]
    for name, band in bands:
        if band.size == 0:
            continue
        res, _ = ocr(band)
        for box, text, conf in (res or []):
            conf = float(conf)
            if conf <= CONF_MIN:
                continue
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            area = (max(xs) - min(xs)) * (max(ys) - min(ys))
            ratio = area / frame_area
            if ratio > AREA_MIN:
                hits.append({"text": text, "conf": round(conf, 3),
                             "area_pct": round(ratio * 100, 2), "band": name})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="scene cap (smoke)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()

    LIB.mkdir(exist_ok=True)
    scenes = scene_list()
    # incremental: keep existing verdicts, gate only new (source, scene) pairs
    prior = []
    if (LIB / "shots.jsonl").exists():
        prior = [json.loads(l) for l in (LIB / "shots.jsonl")
                 .read_text(encoding="utf-8").splitlines()]
        seen = {(r["source"], r["scene"]) for r in prior}
        scenes = [s for s in scenes if (s[0].stem, s[1]) not in seen]
        print(f"[*] incremental: {len(prior)} already gated")
    if args.limit:
        scenes = scenes[:args.limit]
    print(f"[*] {len(scenes)} scenes to gate")

    # resolution gate per SOURCE (probe once each)
    res_cache = {}
    for p, *_ in scenes:
        if p not in res_cache:
            res_cache[p] = probe_res(p)

    frames_dir = Path(tempfile.mkdtemp(prefix="ocr_frames_"))

    def job(item):
        p, si, a, b = item
        w, h = res_cache[p]
        rec = {"source": p.stem, "src": str(p), "scene": si,
               "start": round(a, 2), "end": round(b, 2),
               "dur": round(b - a, 2), "width": w, "height": h}
        if w < MIN_W or h < MIN_H:
            rec.update(verdict="reject_resolution", has_burned_text=False,
                       detections=[])
            return rec
        hits = []
        ln = b - a
        for k, frac in enumerate((0.2, 0.5, 0.8)):
            f = frames_dir / f"{p.stem}_{si}_{k}.jpg"
            if extract_frame(p, a + ln * frac, f):
                hits += ocr_bands(ocr, f)
                try:
                    f.unlink()          # keep disk flat
                except OSError:
                    pass
        rec["has_burned_text"] = bool(hits)
        rec["detections"] = hits[:8]
        rec["verdict"] = "reject_text" if hits else "clean"
        return rec

    out, done = list(prior), 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for rec in ex.map(job, scenes):
            out.append(rec)
            done += 1
            if done % 50 == 0:
                clean = sum(1 for r in out if r["verdict"] == "clean")
                print(f"    [{done}/{len(scenes)}] clean so far: "
                      f"{clean}/{done} ({clean / done:.0%})", flush=True)

    with open(LIB / "shots.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    with open(LIB / "quarantine.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            if r["verdict"] != "clean":
                f.write(json.dumps(r) + "\n")

    n = len(out)
    clean = [r for r in out if r["verdict"] == "clean"]
    rej_t = sum(1 for r in out if r["verdict"] == "reject_text")
    rej_r = sum(1 for r in out if r["verdict"] == "reject_resolution")
    clean_dur = sum(r["dur"] for r in clean)
    by_src = {}
    for r in out:
        s = by_src.setdefault(r["source"], [0, 0])
        s[1] += 1
        if r["verdict"] == "clean":
            s[0] += 1
    report = {
        "total_scenes": n, "clean": len(clean),
        "reject_text": rej_t, "reject_resolution": rej_r,
        "survival_rate": round(len(clean) / n, 4) if n else 0,
        "clean_duration_s": round(clean_dur, 1),
        "by_source": {k: f"{v[0]}/{v[1]}" for k, v in
                      sorted(by_src.items(), key=lambda x: x[1][0] - x[1][1])},
    }
    (LIB / "ingest_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "by_source"},
                     indent=2))
    print(f"[OK] library/shots.jsonl ({n}), quarantine.jsonl "
          f"({rej_t + rej_r}), ingest_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
