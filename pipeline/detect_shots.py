#!/usr/bin/env python3
"""detect_shots.py - shot boundaries for every mp4 in a dossier dir.

Writes manifest/<slug>_shots.json: {video_id: [[start, end], ...]}.
Cuts must never cross these boundaries (ledger F3).

Run:  py -3.12 pipeline/detect_shots.py bruce_lee
"""
import json
import sys
from pathlib import Path

from scenedetect import ContentDetector, detect

ROOT = Path(__file__).resolve().parent.parent


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "bruce_lee"
    dos = ROOT / "dossier" / slug
    out = ROOT / "manifest" / f"{slug}_shots.json"
    shots = json.loads(out.read_text()) if out.exists() else {}
    for f in sorted(dos.glob("*.mp4")):
        vid = f.stem
        if vid in shots:
            continue
        print(f"[shots] {vid}", flush=True)
        scenes = detect(str(f), ContentDetector(threshold=27.0))
        shots[vid] = [[round(s.get_seconds(), 2), round(e.get_seconds(), 2)]
                      for s, e in scenes]
        json.dump(shots, open(out, "w"))
    counts = {k: len(v) for k, v in shots.items()}
    print(f"[OK] {out.name}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
