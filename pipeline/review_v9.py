#!/usr/bin/env python3
"""Eyes-on review sheets for the FINISHED cut, not for the source clips.

The screening pass looked at candidate clips in isolation. This looks at what
actually reached the screen, in programme order, with the words being spoken
over it printed underneath. That is the only way to catch the failure this
project keeps repeating - a shot that is fine on its own and wrong under its
sentence.

It also catches what a machine pass cannot: rule 7 exists because perceptual
dedupe once passed two pure green frames, five Joe Rogan singles and four
Steven Bartlett singles.

Frames come from the rendered MP4 itself, so what is reviewed is what will
play - not the plan's intention.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

MP4 = ROOT / "final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V9.mp4"
EDL = ROOT / "manifest/edl_full.json"
FRAMES = ROOT / "work/review_v9/frames"
SHEETS = ROOT / "work/review_v9"
TILE = (440, 248)
PER_SHEET = 10


def shot_list() -> list[dict]:
    import mrbeast_picture_v9 as M
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    return M.allocate(edl, M.fx.probe_dur(M.AUDIO))


def words_at(edl: dict, t: float) -> str:
    for s in edl["segs"]:
        if s["start"] <= t < s["end"]:
            kind = s["kind"]
            txt = (s.get("text") or "").strip()
            if kind == "beat":
                return "[music only]"
            tag = {"bite": "BITE", "narr": "NARR", "card": "CARD"}.get(kind, kind)
            return f"{tag}: {txt}"
    return "[lead-in / tail]"


def grab(job):
    i, t, dst = job
    if not dst.exists():
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(MP4),
             "-frames:v", "1", "-vf", f"scale={TILE[0]}:-2", "-y", str(dst)],
            capture_output=True, timeout=120)
    return i, dst


def main() -> int:
    if not MP4.exists():
        print(f"missing {MP4}")
        return 1
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    shots = shot_list()
    print(f"[plan] {len(shots)} shots", flush=True)

    FRAMES.mkdir(parents=True, exist_ok=True)
    jobs = []
    for i, s in enumerate(shots):
        mid = s["prog_start"] + s["dur"] / 2
        jobs.append((i, mid, FRAMES / f"{i:03d}.jpg"))
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(grab, jobs))

    try:
        f_big = ImageFont.truetype("arialbd.ttf", 15)
        f_sm = ImageFont.truetype("arial.ttf", 13)
    except Exception:                                            # noqa: BLE001
        f_big = f_sm = ImageFont.load_default()

    SHEETS.mkdir(parents=True, exist_ok=True)
    for old in SHEETS.glob("review_*.png"):
        old.unlink()

    rows_per = PER_SHEET
    n_sheets = 0
    for start in range(0, len(shots), rows_per):
        chunk = shots[start:start + rows_per]
        row_h = TILE[1] + 66
        sh = Image.new("RGB", (TILE[0] + 640, row_h * len(chunk)), (15, 15, 15))
        d = ImageDraw.Draw(sh)
        for r, s in enumerate(chunk):
            idx = start + r
            y = r * row_h
            fp = FRAMES / f"{idx:03d}.jpg"
            if fp.exists():
                try:
                    im = Image.open(fp).convert("RGB")
                    im.thumbnail((TILE[0] - 6, TILE[1] - 6), Image.LANCZOS)
                    sh.paste(im, (4, y + 4))
                except Exception:                                # noqa: BLE001
                    d.text((12, y + 100), "bad frame", fill=(210, 70, 70),
                           font=f_big)
            t = s["prog_start"]
            spec = s["spec"]
            head = (f"#{idx:03d}  {int(t//60)}:{t%60:05.2f}  "
                    f"{s['dur']:.2f}s  span {s['span']}  "
                    f"{spec[0]}:{spec[1] if len(spec) > 1 else ''}")
            d.text((TILE[0] + 14, y + 8), head, fill=(255, 220, 120), font=f_big)
            body = words_at(edl, t + 0.05)
            for j, line in enumerate(textwrap.wrap(body, 74)[:6]):
                d.text((TILE[0] + 14, y + 34 + j * 18), line,
                       fill=(220, 220, 220), font=f_sm)
            d.line([(0, y + row_h - 1), (sh.width, y + row_h - 1)],
                   fill=(55, 55, 55))
        p = SHEETS / f"review_{start // rows_per:02d}.png"
        sh.save(p)
        n_sheets += 1
    print(f"[OK] {n_sheets} review sheets -> {SHEETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
