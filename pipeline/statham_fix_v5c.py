#!/usr/bin/env python3
"""statham_fix_v5c.py - round-3 fixes from the claude-video watch agent.

Blockers: ET premiere + AP junket interludes carried full third-party
graphics packages (banner/chyron/captions - uncroppable) -> removed;
logo bug PNG stream ended after 1 frame under the concat demuxer ->
-loop 1 (fixed in v10_assemble); Getty-still tail bleed on b_067;
windowboxed dark-gym windows; explosion montage under the diary line.
Minors: ExerciseCard stat labels (weights/pace under REPS), Big Five 55
row overflow (fixed in v9cards.tsx), back-squat clip on the Front Squat
card (replaced with a verified Pexels front squat), NIKE-PRO still pan
on b_109, ball-slam gym logo.
"""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "statham"
WORK = ROOT / "final_video" / "v5_work"
V6W = ROOT / "final_video" / "v6_work"
TMP = WORK / "looptmp"
SCR = Path(r"C:\Users\avina\AppData\Local\Temp\claude\C--Users-avina"
           r"\1dd0ecf0-e4df-4b0a-b72a-629f1a099aef\scratchpad")

A = json.loads((MAN / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}
order = sorted(A)
HF, D2 = "tf_hfTRYwnoPZU", "tf_d2V5ZgSDKFE"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{r.stderr[-1200:]}")


def crop_vf(cb):
    if not cb:
        return ""
    l, t, rr, b = cb
    return f"crop=iw*{1-l-rr:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},"


def loop_piece(bid, src_path, t0, t1, crop=None, vid=None):
    dur = round(beats[bid]["end"] - beats[bid]["start"], 3)
    seg = TMP / f"seg_{bid}.mp4"
    vf = (crop_vf(crop) +
          "scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,fps=30,setsar=1,format=yuv420p")
    run(["ffmpeg", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i",
         str(src_path), "-vf", vf, "-an", "-c:v", "libx264", "-preset",
         "veryfast", "-crf", "19", "-y", str(seg)])
    piece = WORK / f"p_{order.index(bid):03d}_{bid}.mp4"
    run(["ffmpeg", "-stream_loop", "-1", "-i", str(seg), "-t",
         f"{dur:.3f}", "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "19", "-r", "30", "-pix_fmt", "yuv420p", "-y",
         str(piece)])
    e = {"type": "cut", "src": str(src_path), "t0": round(t0, 2),
         "t1": round(t1, 2), "vid": vid or f"{src_path}", "verified": True,
         "loop": True, "manual_loop": True}
    if crop:
        e["crop_box"] = crop
    A[bid] = e
    print(f"[loop] {bid} {e['vid']} {t0}-{t1}")


# ---- interludes: drop the two with third-party graphics packages --------
inters = json.loads((MAN / "interludes.json").read_text())
inters = [i for i in inters if i["id"] not in ("int_dive2", "int_ap")]
json.dump(inters, open(MAN / "interludes.json", "w"), indent=1)
print(f"[OK] interludes -> {[i['id'] for i in inters]}")

# ---- footage fixes ------------------------------------------------------
# b_017: Death Race explosions under the "training diary" line
loop_piece("b_017", DOS / f"{HF}.mp4", 35.07, 38.0,
           crop=[0.0, 0.06, 0.06, 0.08], vid=f"{HF}@35.07")
# b_067: Getty-still tail bleed + windowboxed dark gym
loop_piece("b_067", DOS / f"{HF}.mp4", 81.61, 89.2,
           crop=[0.123, 0.0, 0.13, 0.0], vid=f"{HF}@81.61")
# b_109: NIKE-PRO still pan -> plate-carry (real motion) part of the shot
loop_piece("b_109", DOS / f"{D2}.mp4", 126.8, 129.5,
           crop=[0.0, 0.10, 0.12, 0.0], vid=f"{D2}@126.8")
# b_030: windowboxed dark gym - crop into active area (window fits beat)
A["b_030"]["crop_box"] = [0.123, 0.0, 0.15, 0.085]
A["b_030"]["manual_loop"] = False
# b_069: ball-slam loop has a gym logo top-left
A["b_069"]["crop_box"] = [0.12, 0.12, 0.0, 0.0]

# ---- card fixes ---------------------------------------------------------
A["b_047"]["props"]["repsLabel"] = "LOAD"       # 135->365 lb is a load
A["b_047"]["props"]["restLabel"] = "SCHEME"     # "singles" is the scheme
A["b_056"]["props"]["repsLabel"] = "PACE"       # 1:38-1:50 /500m is pace

# ---- front squat: replace back-squat stock with verified front squat ----
fs = SCR / "fs_6114481.mp4"
for dest in (ROOT / "library/exloops/front_squat.mp4",
             ROOT / "graphics/public/exloops/front_squat.mp4"):
    bak = dest.with_suffix(".bak.mp4")
    if dest.exists() and not bak.exists():
        dest.replace(bak)
    shutil.copy(fs, dest)
print("[OK] front_squat.mp4 replaced (backups kept as .bak.mp4)")

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

# ---- invalidate: re-render list + stale remotion bundle -----------------
for bid in ["b_030", "b_047", "b_053", "b_056", "b_060", "b_069", "b_097"]:
    p = WORK / f"p_{order.index(bid):03d}_{bid}.mp4"
    if p.exists():
        p.unlink()
bundle = WORK / "remotion_bundle"
if bundle.exists():
    shutil.rmtree(bundle)     # TSX changed (StepCards2/ExerciseCard)
print("[OK] round-3 patch applied")
