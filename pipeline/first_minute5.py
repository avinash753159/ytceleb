#!/usr/bin/env python3
"""First minute, revision 5.

Three changes agreed with the operator:
  - the title break is now 4s and sits immediately before "The diagnosis
    had a name", so the silence carries the diagnosis instead of being a
    hole in the opening
  - Jimmy cutaways are drawn from manifest/jimmy_pool.json - 26 windows
    verified by eye as him, each spent once - instead of the same handful
  - his posts appear as POSTS: handle, date, his wording, the engagement

Timeline is read from the edit, never from a transcript.

   2.00-11.89  "most productive person ... 300 million subscribers"
  11.89-13.99  bite: "least energetic people you'll ever meet"
  13.99-22.01  "since he was fifteen ... attacking him from the inside"
  22.01-30.80  "not a story about a workout ... take some of it back"
  30.80-34.00  beat
  34.00-44.50  "he was an athlete, a kid who played constantly"
  44.50-54.10  bite: "I got Crohn's when I was 15 ... lost like 50 pounds"
  54.10-58.10  TITLE BREAK, music only
  58.10-69.43  "The diagnosis had a name. Crohn's disease."
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import fx  # noqa: E402
from mrbeast_picture_v7 import credit_vf  # noqa: E402

W, H, FPS = fx.W, fx.H, fx.FPS
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/MRBEAST_FIRST_MINUTE.mp4"
WORK = ROOT / "work/first_minute5"
B = ROOT / "library/broll"
MED = ROOT / "dossier/mrbeast/medical"
PRIM = ROOT / "dossier/mrbeast/primary"
CARDS = ROOT / "work/post_cards"
SRC = ROOT / "dossier/mrbeast/sources"
POOL = ROOT / "manifest/jimmy_pool.json"

_spent: set[str] = set()
_hashes: list[tuple[str, np.ndarray]] = []
_pool: list[dict] = []


def load_pool():
    global _pool
    _pool = [e for e in json.loads(POOL.read_text(encoding="utf-8"))
             if e.get("verified_jimmy")]
    print(f"[pool] {len(_pool)} verified Jimmy windows available",
          flush=True)


def take_window(source: str | None, dur: float) -> dict:
    """Draw an unused, verified window of Jimmy. Optionally from one source
    (required when the audio is that interview - a sync shot)."""
    for e in _pool:
        key = f"{e['source']}@{e['t0']}"
        if key in _spent:
            continue
        if source and e["source"] != source:
            continue
        if e["run_len"] < dur + 0.6:
            continue
        _spent.add(key)
        return e
    raise RuntimeError(f"pool exhausted for source={source} dur={dur}")


def spend_file(p: Path):
    if p.name in _spent:
        raise RuntimeError(f"ASSET REUSED: {p.name}")
    _spent.add(p.name)


def dhash(p: Path):
    a = np.asarray(Image.open(p).convert("L").resize((9, 8), Image.LANCZOS),
                   dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def check_new(piece: Path, name: str, limit=10):
    tmp = WORK / f"_h_{name}.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "0.8", "-i", str(piece), "-frames:v", "1",
                    "-vf", "scale=64:64", str(tmp)], check=True, timeout=300)
    h = dhash(tmp)
    tmp.unlink(missing_ok=True)
    for prev, ph in _hashes:
        d = int(np.count_nonzero(h != ph))
        if d < limit:
            raise RuntimeError(f"{name} looks like {prev} (hamming {d})")
    _hashes.append((name, h))


def jimmy(dur, dest, source=None, zoom=(1.03, 1.11), focus=(0.5, 0.46)):
    e = take_window(source, dur)
    v = SRC / f"{e['source']}.mp4"
    raw = dest.with_suffix(".raw.mp4")
    fx.punch_in(v, e["t0"] + 0.3, dur, raw, zoom_from=zoom[0],
                zoom_to=zoom[1], focus=focus)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(raw), "-an",
            "-vf", credit_vf(e["credit_main"], e["credit_sub"]),
            *fx.ENC, str(dest)])
    raw.unlink(missing_ok=True)
    return dest


def stock(path: Path, dur, dest, t0=None, zoom=0.07):
    spend_file(path)
    total = fx.probe_dur(path)
    if total < dur + 0.4:
        raise RuntimeError(f"{path.name} too short - looping is banned")
    start = t0 if t0 is not None else max(0.4, (total - dur) * 0.3)
    start = min(start, total - dur - 0.2)
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"fps={FPS},scale=w='iw*(1.03+{zoom}*{p})'"
          f":h='ih*(1.03+{zoom}*{p})':eval=frame,crop={W}:{H},"
          f"fade=t=in:st=0:d=0.3,"
          f"fade=t=out:st={max(0, dur-0.3):.3f}:d=0.3")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(path), "-t", f"{dur:.4f}",
            "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


def photo(img: Path, dur, dest, main="", sub="", push=0.14, fit=True,
          fy=0.5):
    spend_file(img)
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,on/{n}),3))"
    base = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D" if fit else
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}")
    vf = (f"{base},scale={W*2}:-2,zoompan=z='1.02+{push:.3f}*{p}':d={n}:"
          f"x='iw/2-(iw/zoom/2)':y='ih*{fy}-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"fade=t=in:st=0:d=0.3,"
          f"fade=t=out:st={max(0, dur-0.3):.3f}:d=0.3,format=yuv420p")
    if main:
        vf += "," + credit_vf(main, sub)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])
    return dest


CUTS = [
    (0.00, 2.00, "01_before", lambda p, d: photo(
        PRIM / "mrbeast_transformation_2023-06-29.jpg", d, p,
        "@MRBEAST", "29 JUNE 2023", 0.08)),
    (2.00, 7.00, "02_channel", lambda p, d: photo(
        PRIM / "yt_channel.png", d, p, push=0.26, fit=False, fy=0.40)),
    (7.00, 11.89, "03_videos", lambda p, d: photo(
        PRIM / "yt_videos.png", d, p, push=0.22, fit=False, fy=0.58)),
    # sync - the audio IS Rogan here
    (11.89, 13.99, "04_sync_a", lambda p, d: jimmy(
        d, p, source="cLRLEnPaJLM", zoom=(1.28, 1.34))),
    (13.99, 18.00, "05_jimmy_b", lambda p, d: jimmy(d, p)),
    (18.00, 22.01, "06_tired", lambda p, d: stock(
        B / "man_tired.mp4", d, p)),
    (22.01, 26.00, "07_gym", lambda p, d: stock(B / "gym_empty.mp4", d, p)),
    # "what he did to take some of it back" - the 2025 post, as a post
    (26.00, 30.80, "08_post_gains", lambda p, d: photo(
        CARDS / "post_gains.png", d, p, push=0.07, fit=False)),
    (30.80, 34.00, "09_jimmy_c", lambda p, d: jimmy(d, p)),
    # "he was an athlete, a kid who played constantly"
    (34.00, 39.00, "10_balls", lambda p, d: stock(
        B / "bb_cand_3.mp4", d, p, zoom=0.08)),
    (39.00, 44.50, "11_bats", lambda p, d: stock(B / "bb_cand_2.mp4", d, p)),
    # sync - "I got Crohn's when I was 15 ... lost like 50 pounds"
    (44.50, 49.50, "12_sync_b", lambda p, d: jimmy(
        d, p, source="cLRLEnPaJLM", zoom=(1.03, 1.10))),
    (49.50, 54.10, "13_field", lambda p, d: stock(
        B / "baseball_field_1.mp4", d, p, zoom=0.05)),
    # 4s of silence before the diagnosis - his own post carries it
    (54.10, 58.10, "14_post_obese", lambda p, d: photo(
        CARDS / "post_obese.png", d, p, push=0.06, fit=False)),
    # "The diagnosis had a name. Crohn's disease."
    (58.10, 63.00, "15_jimmy_d", lambda p, d: jimmy(d, p)),
    (63.00, 69.43, "16_lining", lambda p, d: photo(
        MED / "mechanism.png", d, p, "WIKIMEDIA COMMONS", "CC0",
        0.14, True, 0.34)),
]


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    for f in WORK.glob("*.mp4"):
        f.unlink()
    load_pool()

    for (s1, e1, n1, _), (s2, _, n2, _) in zip(CUTS, CUTS[1:]):
        if abs(e1 - s2) > 1e-6:
            raise RuntimeError(f"gap between {n1} and {n2}")

    pieces = []
    for start, end, name, fn in CUTS:
        dur = end - start
        if dur > 6.5:
            raise RuntimeError(f"{name} is {dur:.1f}s - too long")
        dest = WORK / f"{name}.mp4"
        fn(dest, dur)
        check_new(dest, name)
        got = fx.probe_dur(dest)
        if abs(got - dur) > 0.12:
            raise RuntimeError(f"{name}: {got:.2f}s vs {dur:.2f}s")
        pieces.append(dest)
        print(f"  {start:6.2f}-{end:6.2f}  {name}", flush=True)

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{q.absolute().as_posix()}'"
                             for q in pieces), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
            f"fps={FPS}", *fx.ENC, str(silent)], timeout=3600)
    vdur, target = fx.probe_dur(silent), CUTS[-1][1]
    if abs(vdur - target) > 0.15:
        raise RuntimeError(f"picture {vdur:.2f}s vs timeline {target:.2f}s")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-i", str(AUDIO), "-map", "0:v:0",
            "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
            "-shortest", "-movflags", "+faststart", str(OUT)], timeout=1800)
    print(f"[OK] {OUT} {fx.probe_dur(OUT):.2f}s | "
          f"{len(CUTS)} shots, none repeated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
