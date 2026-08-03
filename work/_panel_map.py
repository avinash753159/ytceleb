"""Map exactly when the Rogan screen-share panel is on screen.

Four of the film's most important bites live between 5350 and 5420 in
cLRLEnPaJLM, and Rogan pulled the Crohn's & Colitis Foundation website up on
the studio monitor while they talked - so a burned-in panel of third-party
text sits in the lower right of the frame for part of it. Sampling the
midpoint of a window misses it; the OCR detector caught it only because it
samples six frames.

OCR over the whole region would be ~250 calls. The panel is a bright
rectangle in an otherwise dark lower-right quadrant, so a luma ratio finds it
for almost nothing, and the OCR verdicts already in hand calibrate it.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources/cLRLEnPaJLM.mp4"
T0, T1, STEP = float(sys.argv[1]), float(sys.argv[2]), 0.25
W, H = 160, 90

n = int((T1 - T0) / STEP)
p = subprocess.run(
    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{T0}",
     "-t", f"{T1-T0}", "-i", str(SRC), "-vf",
     f"fps={1/STEP},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
    capture_output=True, timeout=1800).stdout
frames = np.frombuffer(p, dtype=np.uint8)
frames = frames[:(len(frames) // (W * H)) * W * H].reshape(-1, H, W)

# The panel occupies roughly x 0.52-0.98, y 0.50-0.98 of the frame.
lr = frames[:, int(H * .52):int(H * .97), int(W * .54):int(W * .97)]
rest = frames[:, :int(H * .50), :]
ratio = lr.reshape(len(frames), -1).mean(1) / (
    rest.reshape(len(frames), -1).mean(1) + 1e-6)
bright = lr.reshape(len(frames), -1).mean(1)

rows = [(T0 + i * STEP, float(ratio[i]), float(bright[i]))
        for i in range(len(frames))]
THRESH = 1.2   # calibrated: panel absent 0.70-0.73, present 1.67-1.73
clean = [r for r in rows if r[1] < THRESH]
spans, cur = [], None
for t, rt, br in rows:
    if rt < THRESH:
        cur = (t, t) if cur is None else (cur[0], t)
    elif cur:
        spans.append(cur)
        cur = None
if cur:
    spans.append(cur)

print(f"sampled {len(rows)} frames {T0}-{T1}  "
      f"ratio min {min(r[1] for r in rows):.2f} max {max(r[1] for r in rows):.2f}")
print("CLEAN spans (no panel), length >= 2.4s:")
for a, b in spans:
    if b - a >= 2.4:
        print(f"  {a:8.2f} -> {b:8.2f}   {b-a:5.2f}s")
print("\nall spans:")
for a, b in spans:
    print(f"  {a:8.2f} -> {b:8.2f}   {b-a:5.2f}s")
(ROOT / "work/panel_map.json").write_text(json.dumps(
    {"source": "cLRLEnPaJLM", "t0": T0, "t1": T1, "step": STEP,
     "thresh": THRESH,
     "clean_spans": [[round(a, 2), round(b, 2)] for a, b in spans],
     "ratio": [[round(t, 2), round(r, 3)] for t, r, _ in rows]}, indent=2))
