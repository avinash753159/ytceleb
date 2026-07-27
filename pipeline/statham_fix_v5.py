#!/usr/bin/env python3
"""statham_fix_v5.py - V5 window replacements from the footage scan.

Fixes the five V4 defect classes the operator flagged:
  1. fan-comp title/still cards shipped as beats (b_016, b_021, b_041, ...)
  2. one vertical blur-pillarboxed IG clip repeated 4x (b_030/065/068/069)
  3. trailer title-text frames (WRATH OF MAN / EXPOSE THE CORRUPTION /
     ON THIS) and the ET SHARK STUNTS banner beats
  4. burned-in French subs + Getty/mensfitness watermarks
  5. letterbox/pillarbox windows shipped uncropped (b_001, b_043)

Every replacement window was motion-verified (manifest/candidates.json)
and eyeballed on contact sheets before landing here. Edits assets_v5.json
in place, then deletes the affected pieces so v5_assemble re-renders them.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "statham"
WORK = ROOT / "final_video" / "v5_work"

A = json.loads((MAN / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}
shots = json.loads((MAN / "statham_shots.json").read_text())

T7 = "tf_-7LyChJmWto"
HF = "tf_hfTRYwnoPZU"
D2 = "tf_d2V5ZgSDKFE"
XR = "xrxH5n93CzM"


def durl(p):
    p = Path(p)
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def cut(bid, src, s0, s1, crop=None):
    need = beats[bid]["end"] - beats[bid]["start"]
    t0 = round(s0 + 0.1, 2)
    avail = s1 - t0
    e = {"type": "cut", "src": str(DOS / f"{src}.mp4"), "t0": t0,
         "vid": f"{src}@{t0}", "verified": True}
    if avail < need:
        e["loop"] = True
        e["t1"] = round(s1, 2)
    else:
        e["t1"] = round(t0 + need + 0.2, 2)
    if crop:
        e["crop_box"] = crop
    A[bid] = e


def exloop(bid, name):
    need = beats[bid]["end"] - beats[bid]["start"]
    A[bid] = {"type": "cut",
              "src": str(ROOT / "library/exloops" / f"{name}.mp4"),
              "t0": 0.0, "t1": round(need + 0.2, 2),
              "vid": f"exloop:{name}", "verified": True, "loop": True}


# ---- Statham footage swaps (narration-matched) --------------------------
cut("b_002", T7, 21.3, 25.57)          # never out of shape -> muscle-up reps
cut("b_006", T7, 121.97, 129.43)       # kid on 10m platform -> diving archive
cut("b_016", T7, 76.33, 79.53)         # paid bills family way -> street candid
cut("b_021", T7, 142.83, 150.4)        # post-War casual -> flat-cap street
cut("b_027", HF, 92.26, 100.07)        # 87eleven warehouse -> dark gym wide
cut("b_030", HF, 64.03, 71.24)         # motivate yourself -> pad work
cut("b_040", HF, 27.26, 30.23)         # dynamite quote -> heavy bag
cut("b_041", HF, 126.63, 129.63,       # never make it explode -> bag (crop
    crop=[0.0, 0.06, 0.06, 0.14])      #  kills mensfitness.com bug)
cut("b_042", T7, 0.0, 3.13)            # hammer bang -> prison-orange BTS
cut("b_067", HF, 81.51, 89.26)         # MH warning -> pads, high intensity
cut("b_070", HF, 30.23, 34.97)         # training half the story -> kicking
cut("b_078", HF, 23.76, 27.26)         # before: different man -> 90s VHS spar
cut("b_088", XR, 134.0, 140.0)         # old skill set, own diving -> archive
cut("b_093", D2, 213.8, 216.5)         # phenomenal shape -> barbed-wire candid
cut("b_096", T7, 9.37, 12.73)          # movies caught him in shape -> T3 beach

# ---- named-exercise beats -> real exercise loops ------------------------
exloop("b_036", "rowing_erg")          # "ten minutes on the rowing machine"
exloop("b_038", "kettlebell_carry")    # "kettlebell and sandbag carries"
exloop("b_039", "burpee")              # "redlining the heart" finisher
exloop("b_065", "trail_run")           # "a trail run in the Hollywood Hills"
exloop("b_068", "power_clean")         # "compounds kept heavy and short"
exloop("b_069", "ball_slam")           # "intervals that end with nothing left"
exloop("b_086", "pushup")              # "mobility first, no more true maxes"
exloop("b_090", "boxing")              # "12 week camp with a trainer"
exloop("b_092", "jiujitsu")            # "hours of jujitsu"
exloop("b_095", "pullup")              # "same engine"
exloop("b_097", "front_squat")         # "you need his rules"
exloop("b_110", "deadlift")            # "could you survive deadlift day"

# ---- keep content, kill the bars (crop into active area) ----------------
A["b_001"]["crop_box"] = [0.0, 0.16, 0.0, 0.13]   # letterboxed muscle-up
A["b_043"]["crop_box"] = [0.19, 0.0, 0.02, 0.04]  # pillarboxed golden bar

# ---- b_079 "An apple. I'd have five." -> five real apples ---------------
apple = durl(ROOT / "library/food/apple.jpg")
A["b_079"] = {"type": "v5card", "comp": "PhotoBurst", "props": {
    "label": "AN APPLE? I'D HAVE FIVE",
    "labelAtMs": 200,
    "satellites": [{"src": apple, "label": f"#{i+1}", "atMs": 350 + i * 420}
                   for i in range(5)]}}

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

# ---- invalidate the affected pieces so v5_assemble re-renders them ------
changed = ["b_001", "b_002", "b_006", "b_016", "b_021", "b_027", "b_030",
           "b_036", "b_038", "b_039", "b_040", "b_041", "b_042", "b_043",
           "b_065", "b_067", "b_068", "b_069", "b_070", "b_078", "b_079",
           "b_086", "b_088", "b_090", "b_092", "b_093", "b_095", "b_096",
           "b_097", "b_110"]
order = sorted(A)
killed = 0
for bid in changed:
    p = WORK / f"p_{order.index(bid):03d}_{bid}.mp4"
    if p.exists():
        p.unlink()
        killed += 1
print(f"[OK] patched {len(changed)} beats, deleted {killed} stale pieces")
