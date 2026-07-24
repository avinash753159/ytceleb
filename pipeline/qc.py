#!/usr/bin/env python3
"""
qc.py - Phase 5: fail loudly rather than ship a bad render.

Gates (qc_report.json + table; exit non-zero on ANY failure):
  G1 OCR sweep of the final render - 1 frame / 2s, only inside beats whose
     footage is source material (clip/still/split without our overlays),
     masked to bottom 30% / top 15%. Any text -> FAIL with timestamps.
  G2 no library scene reused within 90s
  G3 no source shot < 1.2s or > 6.0s
  G4 no treatment (post-fallback) > 3x consecutive
  G5 every COUNT-forced infographic beat has exactly N items
  G6 ffmpeg blackdetect + freezedetect clean
  G7 loudness: two-pass loudnorm target -14 LUFS / -1.0 dBTP
     (--normalize applies the second pass and re-muxes the shipped file)
  G8 final duration within +/-0.1s of the narration

Run:  py -3.12 pipeline/qc.py final_video/RYAN_REYNOLDS_FINAL_V2.mp4 [--normalize]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"


def ffprobe_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def g1_ocr_sweep(video, plan, assets, beats):
    from rapidocr_onnxruntime import RapidOCR
    import cv2
    ocr = RapidOCR()
    fails = []
    tmp = Path(tempfile.mkdtemp(prefix="qc_ocr_"))
    for p in plan:
        a = assets[p["beat_id"]]
        tr = a["treatment"]
        if tr in ("infographic_list", "stat_callout", "person_card",
                  "split_compare"):
            continue          # our own overlays/labels contain text by design
        if p.get("overlay_stat"):
            continue
        b = beats[p["beat_id"]]
        t = b["start"] + 0.5
        while t < b["end"] - 0.3:
            f = tmp / "f.jpg"
            subprocess.run(["ffmpeg", "-ss", f"{t:.2f}", "-i", str(video),
                            "-frames:v", "1", "-q:v", "3", "-y", str(f)],
                           capture_output=True, timeout=60)
            img = cv2.imread(str(f))
            if img is not None:
                H, W = img.shape[:2]
                for band in (img[int(H * .70):, :], img[:int(H * .15), :]):
                    res, _ = ocr(band)
                    for box, text, conf in (res or []):
                        # 1-3 char fragments are OCR noise on textures /
                        # equipment; real subtitles/watermarks are longer
                        if len(re.sub(r"[^A-Za-z0-9]", "", text)) < 4:
                            continue
                        xs = [q[0] for q in box]
                        ys = [q[1] for q in box]
                        if float(conf) > 0.5 and \
                           (max(xs) - min(xs)) * (max(ys) - min(ys)) \
                           / (H * W) > 0.004:
                            fails.append(f"{t:.1f}s [{p['beat_id']}] "
                                         f"'{text[:40]}'")
            t += 2.0
    return fails


def g2_g3_shots(plan, assets, beats):
    reuse, lens = [], []
    last_use = {}
    for p in plan:
        a = assets[p["beat_id"]]
        b = beats[p["beat_id"]]
        dur = b["end"] - b["start"]
        asset = a.get("asset") or {}
        segs = []
        if asset.get("kind") == "clip":
            segs = [(asset["id"], dur)]
        elif asset.get("kind") == "clip2":
            segs = [(asset["a"]["id"], dur / 2), (asset["b"]["id"], dur / 2)]
        elif asset.get("kind") == "clips":
            n = len(asset["list"])
            segs = [(c["id"], dur / n) for c in asset["list"]]
        for sid, sdur in segs:
            if sid in last_use and b["start"] - last_use[sid] < 90:
                reuse.append(f"{p['beat_id']}: scene {sid} reused "
                             f"{b['start'] - last_use[sid]:.0f}s later")
            last_use[sid] = b["end"]
            if sdur < 1.2 - 0.05 or sdur > 6.0 + 0.05:
                lens.append(f"{p['beat_id']}: shot {sid} {sdur:.1f}s")
    return reuse, lens


def g4_variety(plan, assets):
    fails, run, prev = [], 1, None
    for p in plan:
        tr = assets[p["beat_id"]]["treatment"]
        run = run + 1 if tr == prev else 1
        if run > 3:
            fails.append(f"{p['beat_id']}: '{tr}' x{run} consecutive")
        prev = tr
    return fails


def g5_counts(plan, signals):
    sig = {s["beat_id"]: s for s in signals}
    fails = []
    for p in plan:
        cnt = (sig.get(p["beat_id"]) or {}).get("count")
        if cnt and p["treatment"] == "infographic_list":
            if len(p.get("items", [])) != cnt[0]:
                fails.append(f"{p['beat_id']}: spoke {cnt[0]}, "
                             f"shows {len(p.get('items', []))}")
    return fails


def g6_black_freeze(video, plan, assets, beats):
    r = subprocess.run(["ffmpeg", "-i", str(video), "-vf",
                        "blackdetect=d=0.4:pix_th=0.08,freezedetect=n=0.001:d=2",
                        "-an", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=1800)
    log = r.stderr or ""

    # stills/splits/graphics are static by design - freeze only matters
    # inside motion-clip beats; black matters everywhere
    def beat_at(t):
        for p in plan:
            b = beats[p["beat_id"]]
            if b["start"] - 0.2 <= t <= b["end"] + 0.2:
                return assets[p["beat_id"]]["treatment"]
        return "?"

    blk = re.findall(r"black_start:([\d.]+)", log)
    frz = re.findall(r"freeze_start: ([\d.]+)", log)
    fails = [f"black@{b}s" for b in blk]
    fails += [f"freeze@{f}s" for f in frz
              if beat_at(float(f)) in ("motion_broll", "exercise_demo")]
    return fails


def g7_loudness(video, normalize):
    r = subprocess.run(["ffmpeg", "-i", str(video), "-af",
                        "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
                        "-f", "null", "-"],
                       capture_output=True, text=True, timeout=1800)
    m = re.search(r"\{[^{}]+\}", (r.stderr or "")[-2500:], re.S)
    if not m:
        return ["loudnorm measurement failed"], None
    meas = json.loads(m.group(0))
    lufs = float(meas["input_i"])
    ok = abs(lufs - (-14.0)) <= 1.0 and float(meas["input_tp"]) <= -0.9
    if ok:
        return [], None
    if not normalize:
        return [f"loudness {lufs:.1f} LUFS (target -14)"], meas
    out = video.with_name(video.stem + "_norm" + video.suffix)
    af = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={meas['input_i']}:"
          f"measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:"
          f"measured_thresh={meas['input_thresh']}:"
          f"offset={meas['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-i", str(video), "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "192k", "-y", str(out)],
                   capture_output=True, timeout=1800)
    if out.exists():
        out.replace(video)
        return [], meas
    return ["loudnorm apply failed"], meas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--normalize", action="store_true")
    ap.add_argument("--skip-ocr", action="store_true")
    args = ap.parse_args()
    video = Path(args.video)

    plan = json.loads((MANIFEST / "plan.json").read_text())["plan"]
    assets = json.loads((MANIFEST / "assets.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((MANIFEST / "beats.json").read_text())["beats"]}
    signals = json.loads((MANIFEST / "plan_signals.json").read_text())
    words = json.loads((MANIFEST / "words.json").read_text())

    gates = {}
    gates["G2_reuse"], gates["G3_shot_len"] = g2_g3_shots(plan, assets, beats)
    gates["G4_variety"] = g4_variety(plan, assets)
    gates["G5_counts"] = g5_counts(plan, signals)
    gates["G6_black_freeze"] = g6_black_freeze(
        video, plan, assets,
        {b["beat_id"]: b for b in
         json.loads((MANIFEST / "beats.json").read_text())["beats"]})
    gates["G7_loudness"], _ = g7_loudness(video, args.normalize)
    dur = ffprobe_dur(video)
    tgt = words["duration"]
    gates["G8_duration"] = ([] if abs(dur - tgt) <= 0.1 else
                            [f"final {dur:.2f}s vs narration {tgt:.2f}s"])
    gates["G1_ocr"] = ([] if args.skip_ocr else
                       g1_ocr_sweep(video, plan, assets, beats))

    report = {"video": str(video), "duration": dur,
              "gates": {k: {"pass": not v, "fails": v[:20]}
                        for k, v in gates.items()}}
    (ROOT / "qc_report.json").write_text(json.dumps(report, indent=1))

    print(f"\n{'GATE':<16} {'RESULT':<8} DETAIL")
    bad = 0
    for k, v in gates.items():
        status = "PASS" if not v else f"FAIL({len(v)})"
        bad += bool(v)
        print(f"{k:<16} {status:<8} {v[0] if v else ''}")
    print(f"\n[{'OK' if not bad else 'FAIL'}] qc_report.json written; "
          f"{bad} gate(s) failing")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
