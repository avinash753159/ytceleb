#!/usr/bin/env python3
"""
recover_crop.py - V3: un-quarantine watermarked scenes via gentle crop.

A scene whose text detections ALL sit inside the outer margins (corner bugs,
lower-third channel logos) is recoverable: cropping ~10-12% pushes the mark
out of frame while keeping the shot usable. Scenes with centered burns
(subtitles mid-lower-third, full-width cards) stay quarantined.

Reads library/quarantine.jsonl, re-OCRs 3 keyframes per scene at full frame,
and classifies:
  recoverable  -> verdict 'clean_cropped' + crop fraction (0.10-0.12)
  subtle       -> tiny/faint marks (area < 0.7%, conf < 0.75) -> keep as-is
  hard         -> stays rejected

Updates library/shots.jsonl in place. Run before embed --build.
"""
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
LIB = ROOT / "library"

MARGIN = 0.14        # text fully inside outer 14% band = croppable at 12%
CROP = 0.12
SUBTLE_AREA = 0.007
SUBTLE_CONF = 0.75


def extract(src, t, out):
    subprocess.run(["ffmpeg", "-ss", f"{t:.2f}", "-i", str(src),
                    "-frames:v", "1", "-q:v", "3", "-y", str(out)],
                   capture_output=True, timeout=60)
    return out.exists()


def classify(ocr, src, a, b, tmp):
    """Per-SIDE crop: text confined to one edge means we crop only that
    edge (plus 2% safety), so a corner bug costs ~14% of one side instead
    of a heavy symmetric zoom. Returns (verdict, crop_box [l,t,r,b])."""
    import cv2
    ln = b - a
    crop = [0.0, 0.0, 0.0, 0.0]      # left, top, right, bottom fractions
    croppable = True
    subtle = True
    any_text = False
    for k, frac in enumerate((0.2, 0.5, 0.8)):
        f = tmp / f"c{k}.jpg"
        if not extract(src, a + ln * frac, f):
            continue
        img = cv2.imread(str(f))
        if img is None:
            continue
        H, W = img.shape[:2]
        res, _ = ocr(img)
        for box, text, conf in (res or []):
            conf = float(conf)
            if conf <= 0.5:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            area = (max(xs) - min(xs)) * (max(ys) - min(ys)) / (H * W)
            if area < 0.003:
                continue
            any_text = True
            l, t = min(xs) / W, min(ys) / H
            r, btm = max(xs) / W, max(ys) / H
            placed = False
            if btm < MARGIN:                       # top strip
                crop[1] = max(crop[1], btm + 0.02)
                placed = True
            elif t > 1 - MARGIN:                   # bottom strip
                crop[3] = max(crop[3], 1 - t + 0.02)
                placed = True
            elif r < MARGIN:                       # left strip
                crop[0] = max(crop[0], r + 0.02)
                placed = True
            elif l > 1 - MARGIN:                   # right strip
                crop[2] = max(crop[2], 1 - l + 0.02)
                placed = True
            if not placed:
                croppable = False
                if not (area < SUBTLE_AREA and conf < SUBTLE_CONF):
                    subtle = False
        try:
            f.unlink()
        except OSError:
            pass
    if not any_text:
        return "clean", None
    if croppable and max(crop) <= MARGIN + 0.02:
        return "clean_cropped", [round(c, 3) for c in crop]
    if subtle:
        return "clean_subtle", None
    return "hard", None


def main():
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    shots = [json.loads(l) for l in
             (LIB / "shots.jsonl").read_text(encoding="utf-8").splitlines()]
    cand = [s for s in shots if s["verdict"] == "reject_text"]
    print(f"[*] re-examining {len(cand)} quarantined scenes for crop recovery")
    tmp = Path(tempfile.mkdtemp(prefix="crop_"))

    def job(s):
        verdict, crop_box = classify(ocr, s["src"], s["start"], s["end"], tmp)
        return s, verdict, crop_box

    rec = sub = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for s, verdict, crop_box in ex.map(job, cand):
            if verdict in ("clean_cropped", "clean"):
                s["verdict"] = "clean"
                if crop_box:
                    s["crop_box"] = crop_box
                rec += 1
            elif verdict == "clean_subtle":
                s["verdict"] = "clean"
                s["subtle_mark"] = True
                sub += 1
    with open(LIB / "shots.jsonl", "w", encoding="utf-8") as f:
        for s in shots:
            f.write(json.dumps(s) + "\n")
    clean = sum(1 for s in shots if s["verdict"] == "clean")
    print(f"[OK] recovered {rec} via crop, {sub} as subtle; clean pool now "
          f"{clean}/{len(shots)} ({clean / len(shots):.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
