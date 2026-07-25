#!/usr/bin/env python3
"""v5_prerender.py - render all v5card + library pieces NOW (they don't
depend on the dossier downloads). Parallel ffmpeg lanes; Remotion renders
sequential (each already uses many cores)."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble  # noqa: E402

MAN = ROOT / "manifest"
WORK = ROOT / "final_video" / "v5_work"
WORK.mkdir(parents=True, exist_ok=True)
assemble.WORK = WORK

assets5 = json.loads((MAN / "assets_v5.json").read_text()) \
    if (MAN / "assets_v5.json").exists() else {}
if not assets5:
    # assets_v5 not built yet (downloads pending) - build graphics-only view
    import subprocess
    subprocess.run([sys.executable,
                    str(ROOT / "pipeline" / "v5_build_assets.py")],
                   check=True)
    assets5 = json.loads((MAN / "assets_v5.json").read_text())

v4_plan = {p["beat_id"]: p for p in
           json.loads((MAN / "plan.json").read_text())["plan"]}
v4_assets = json.loads((MAN / "assets.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}

order = sorted(assets5)
done = fail = skip = 0
for idx, bid in enumerate(order):
    a5 = assets5[bid]
    if a5["type"] == "cut":
        continue                      # needs dossier files; later pass
    b = beats[bid]
    dur = round(b["end"] - b["start"], 3)
    piece = WORK / f"p_{idx:03d}_{bid}.mp4"
    if piece.exists():
        skip += 1
        continue
    try:
        if a5["type"] == "v5card":
            assemble.render_remotion(a5["comp"], dict(a5["props"]),
                                    piece, dur, alpha=False)
        else:  # library
            assemble.build_piece(v4_plan[bid], v4_assets[bid], b, idx,
                                 v4_assets)
            v4p = WORK / f"piece_{idx:03d}_{bid}.mp4"
            if v4p.exists():
                v4p.replace(piece)
        done += 1
        print(f"  [{idx}] {bid} {a5['type']} ok", flush=True)
    except Exception as e:
        fail += 1
        print(f"  [{idx}] {bid} FAIL {str(e)[:100]}", flush=True)
print(f"[PRERENDER DONE] rendered={done} skip={skip} fail={fail}")
