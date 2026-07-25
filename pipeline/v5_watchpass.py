#!/usr/bin/env python3
"""v5_watchpass.py - extract verification frames for every planned cut.
For each 'cut' beat: frames at t0 / mid / t1-0.3 (plus 2 probes 4s either
side for retiming) -> watchpass/<bid>_*.jpg + watchpass/manifest.json.
The verify fleet READS these to confirm/adjust each window."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WP = ROOT / "final_video" / "watchpass"
WP.mkdir(parents=True, exist_ok=True)

assets5 = json.loads((ROOT / "manifest" / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((ROOT / "manifest" / "beats.json").read_text())["beats"]}
plan = json.loads((ROOT / "manifest" / "v5_plan.json").read_text())

rows = []
for bid, a in sorted(assets5.items()):
    if a["type"] != "cut":
        continue
    dur_beat = beats[bid]["end"] - beats[bid]["start"]
    t0, t1 = float(a["t0"]), float(a["t1"])
    probes = [("s", t0 + 0.2), ("m", (t0 + t1) / 2), ("e", t1 - 0.3),
              ("pre", max(t0 - 4, 0.2)), ("post", t1 + 4)]
    shots = []
    for tag, t in probes:
        f = WP / f"{bid}_{tag}.jpg"
        if not f.exists():
            subprocess.run(["ffmpeg", "-ss", f"{t:.2f}", "-i", a["src"],
                            "-frames:v", "1", "-vf", "scale=640:-2",
                            "-q:v", "4", "-y", str(f)],
                           capture_output=True, timeout=60)
        if f.exists():
            shots.append({"tag": tag, "t": round(t, 2), "img": str(f)})
    rows.append({"beat_id": bid, "title": a["title"], "vid": a["vid"],
                 "t0": t0, "t1": t1, "beat_dur": round(dur_beat, 1),
                 "narration": beats[bid]["text"][:170], "frames": shots})
json.dump(rows, open(WP / "manifest.json", "w"), indent=1)
print(f"[OK] watchpass frames for {len(rows)} cut beats -> {WP}")
