#!/usr/bin/env python3
"""Contact sheets for every broll7 candidate, for the mandatory eyes-on pass.

HANDOFF rule 7: the machine pass is necessary and NOT sufficient. Perceptual
dedupe once passed two pure green frames, five Joe Rogan singles and four
Steven Bartlett singles, because a hash cannot tell you who is in frame. So
nothing from broll7 is drawn until a human (or a model actually looking at
the pixels) has seen four frames from every clip.

One row per clip, four frames across it, labelled with segment and Pexels id
so a reject can be named precisely. Verdicts go in manifest/broll7_verdicts.json:

    {"s0_1234567": {"ok": false, "why": "burned-in logo bottom right"}}

What has to be rejected, from the rules that earned themselves:
  * any identifiable creator, presenter or commentator            (rule 1)
  * burned-in logos, watermarks or overlay text                   (rule 3/11)
  * a child who could read as young Jimmy                         (rule 9)
  * a shot that is really a different subject than the segment
Anonymous adults performing the activity are ALLOWED - the owner relaxed
rule 9 in the broll6 round.
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "library/broll7"
FRAMES = ROOT / "work/broll7_frames"
SHEETS = ROOT / "work/broll7_sheets"
N_FRAMES = 4
PER_SHEET = 14
TILE = (330, 186)


def probe(path: Path) -> dict:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration",
             "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60).stdout
        d = json.loads(out)
        s = (d.get("streams") or [{}])[0]
        dur = float(s.get("duration") or d.get("format", {}).get("duration") or 0)
        return {"w": s.get("width"), "h": s.get("height"), "dur": dur}
    except Exception:                                            # noqa: BLE001
        return {"w": None, "h": None, "dur": 0.0}


def grab(job):
    path, meta = job
    stem = path.stem
    out = FRAMES / stem
    out.mkdir(parents=True, exist_ok=True)
    dur = meta["dur"] or 0
    if dur <= 0:
        return stem, []
    made = []
    for i in range(N_FRAMES):
        t = dur * (i + 0.5) / N_FRAMES
        dst = out / f"{i}.jpg"
        if not dst.exists():
            subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path),
                 "-frames:v", "1", "-vf", f"scale={TILE[0]}:-2",
                 "-y", str(dst)],
                capture_output=True, timeout=90)
        if dst.exists():
            made.append(dst)
    return stem, made


def sheet(rows, path):
    """rows: [(label, [frame paths])]"""
    W = TILE[0] * N_FRAMES
    H = (TILE[1] + 22) * len(rows)
    sh = Image.new("RGB", (W, H), (16, 16, 16))
    d = ImageDraw.Draw(sh)
    try:
        f = ImageFont.truetype("arial.ttf", 13)
    except Exception:                                            # noqa: BLE001
        f = ImageFont.load_default()
    for r, (label, frames) in enumerate(rows):
        y = r * (TILE[1] + 22)
        for c in range(N_FRAMES):
            x = c * TILE[0]
            if c < len(frames):
                try:
                    im = Image.open(frames[c]).convert("RGB")
                    im.thumbnail((TILE[0] - 4, TILE[1] - 4), Image.LANCZOS)
                    sh.paste(im, (x + 2, y + 2))
                except Exception:                                # noqa: BLE001
                    d.text((x + 10, y + 80), "bad frame", fill=(200, 70, 70),
                           font=f)
            else:
                d.text((x + 10, y + 80), "-", fill=(90, 90, 90), font=f)
        d.text((6, y + TILE[1] + 4), label, fill=(215, 215, 215), font=f)
    path.parent.mkdir(parents=True, exist_ok=True)
    sh.save(path)


def main() -> int:
    clips = sorted(SRC.glob("*.mp4"))
    if not clips:
        print("no clips in library/broll7")
        return 1
    # `--new` screens only clips that do not already carry a verdict, so a
    # top-up round does not reprint 200 rows that were already looked at.
    if "--new" in sys.argv:
        vp = ROOT / "manifest/broll7_verdicts.json"
        seen = set(json.loads(vp.read_text(encoding="utf-8"))) if vp.exists() \
            else set()
        clips = [c for c in clips if c.stem not in seen]
        print(f"[new] {len(clips)} clips without a verdict", flush=True)
        if not clips:
            print("nothing new to screen")
            return 0
    print(f"[probe] {len(clips)} clips", flush=True)
    meta = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(probe, c): c for c in clips}
        for fut in as_completed(futs):
            meta[futs[fut]] = fut.result()

    print("[frames] extracting", flush=True)
    grabbed = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(grab, (c, meta[c])) for c in clips]
        for i, fut in enumerate(as_completed(futs), 1):
            stem, made = fut.result()
            grabbed[stem] = made
            if i % 40 == 0:
                print(f"  {i}/{len(clips)}", flush=True)

    creds = {}
    cpath = SRC / "CREDITS.json"
    if cpath.exists():
        for r in json.loads(cpath.read_text(encoding="utf-8")):
            creds[Path(r["file"]).stem] = r

    rows = []
    for c in clips:
        m, r = meta[c], creds.get(c.stem, {})
        rows.append((f"{c.stem}   seg {r.get('segment','?')}   "
                     f"{m['dur']:.1f}s  {m['w']}x{m['h']}", grabbed.get(c.stem, [])))

    SHEETS.mkdir(parents=True, exist_ok=True)
    for old in SHEETS.glob("*.png"):
        old.unlink()
    n = 0
    for i in range(0, len(rows), PER_SHEET):
        p = SHEETS / f"screen_{i // PER_SHEET:02d}.png"
        sheet(rows[i:i + PER_SHEET], p)
        n += 1
    print(f"\n[OK] {n} sheets -> {SHEETS}")
    print("     nothing is cleared until these are looked at")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
