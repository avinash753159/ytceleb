#!/usr/bin/env python3
"""First minute, revision 3 - cut to the words, with nothing used twice.

The narration was transcribed first this time, and every shot is placed
against what is actually being said:

  0-12  "most productive person ... 300 million subscribers"  -> his channel
 12-14  "least energetic people you'll ever meet"             -> him, sync
 14-20  "since he was 15 ... attacking him from the inside"   -> his archive
 20-24  "this is NOT a story about a workout"                 -> empty gym
 24-30  "took things away from a kid, and what he did to
         take some of it back"                                -> before/after
 30-48  "he was an athlete, a kid who played constantly"      -> baseball
 48-56   music-only hold                                      -> the field
 56-66  "I got Crohn's when I was 15 ... lost like 50 pounds" -> him, sync

EVERY ASSET IS USED EXACTLY ONCE. The composite before/after registers BOTH
photographs as spent, which is what was wrong last time: the pair showed
them, then each was shown again on its own, so the same mirror photo came
round twice.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import fx  # noqa: E402
from mrbeast_picture_v7 import credit_vf, uncut_window  # noqa: E402

W, H, FPS = fx.W, fx.H, fx.FPS
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/MRBEAST_FIRST_MINUTE.mp4"
WORK = ROOT / "work/first_minute3"
B = ROOT / "library/broll"
PRIM = ROOT / "dossier/mrbeast/primary"
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"

BEFORE = PRIM / "mrbeast_transformation_2023-06-29.jpg"
AFTER = PRIM / "mrbeast_after_2025-04-21_1.jpg"
YT1 = PRIM / "yt_channel.png"
YT2 = PRIM / "yt_videos.png"
ROGAN = SRC / "cLRLEnPaJLM.mp4"
TEEN = ARC / "AKJfakEsgy0.mp4"
MAX_SHOT = 6.0

_spent: set[str] = set()
_hashes: list[tuple[str, np.ndarray]] = []


def spend(*paths: Path):
    for p in paths:
        if p.name in _spent:
            raise RuntimeError(
                f"ASSET REUSED: {p.name}. Every asset appears once.")
        _spent.add(p.name)


def dhash(p: Path) -> np.ndarray:
    a = np.asarray(Image.open(p).convert("L").resize((9, 8), Image.LANCZOS),
                   dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def check_new(piece: Path, name: str, limit: int = 11):
    tmp = WORK / f"_h_{name}.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "1.2", "-i", str(piece), "-frames:v", "1",
                    "-vf", "scale=64:64", str(tmp)], check=True, timeout=300)
    h = dhash(tmp)
    tmp.unlink(missing_ok=True)
    for prev, ph in _hashes:
        d = int(np.count_nonzero(h != ph))
        if d < limit:
            raise RuntimeError(f"{name} looks like {prev} (hamming {d})")
    _hashes.append((name, h))


def stock(path: Path, dur: float, dest: Path, t0: float | None = None,
          zoom=0.07):
    spend(path)
    total = fx.probe_dur(path)
    if total < dur + 0.4:
        raise RuntimeError(f"{path.name} too short - looping is banned")
    start = t0 if t0 is not None else max(0.4, (total - dur) * 0.3)
    start = min(start, total - dur - 0.2)
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},"
          f"scale=w='iw*(1.03+{zoom}*{p})':h='ih*(1.03+{zoom}*{p})'"
          f":eval=frame,crop={W}:{H},"
          f"fade=t=in:st=0:d=0.3,"
          f"fade=t=out:st={max(0, dur-0.3):.3f}:d=0.3")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(path), "-t", f"{dur:.4f}",
            "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


def shot_photo(img: Path, dur: float, dest: Path, main="", sub="",
               push=0.16, fit=True, fy=0.5, claim=True):
    if claim:
        spend(img)
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,on/{n}),3))"
    base = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D" if fit else
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}")
    vf = (f"{base},scale={W*2}:-2,"
          f"zoompan=z='1.02+{push:.3f}*{p}':d={n}:"
          f"x='iw/2-(iw/zoom/2)':y='ih*{fy}-(ih/zoom/2)':"
          f"s={W}x{H}:fps={FPS},"
          f"fade=t=in:st=0:d=0.35,"
          f"fade=t=out:st={max(0, dur-0.35):.3f}:d=0.35,format=yuv420p")
    if main:
        vf += "," + credit_vf(main, sub)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])
    return dest


def shot_pair(dur: float, dest: Path):
    """Consumes BOTH photographs - neither can be shown again."""
    spend(BEFORE, AFTER)
    half = W // 2
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    lab = ("drawtext=fontfile='graphics/public/fonts/Anton-Regular.ttf'"
           ":text='{t}':fontcolor=white:fontsize=38:box=1"
           ":boxcolor=#E3120B:boxborderw=11:x={x}:y=h-215")
    fc = (f"[0:v]scale={half}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={half}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D[l];"
          f"[1:v]scale={half}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={half}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D[r];"
          f"[l][r]hstack=inputs=2,"
          f"scale=w='iw*(1.0+0.05*{p})':h='ih*(1.0+0.05*{p})':eval=frame,"
          f"crop={W}:{H},"
          f"drawbox=x={half-3}:y=0:w=6:h={H}:color=#E3120B:t=fill,"
          + lab.format(t="JUNE 2023", x=int(half*0.5)-118) + ","
          + lab.format(t="APRIL 2025", x=half+int(half*0.5)-128) + ","
          f"fade=t=in:st=0:d=0.35,format=yuv420p,"
          + credit_vf("@MRBEAST", "HIS OWN PHOTOGRAPHS"))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(BEFORE), "-loop", "1", "-i", str(AFTER),
            "-t", f"{dur:.4f}", "-an", "-filter_complex", fc,
            "-r", str(FPS), *fx.ENC, str(dest)])
    return dest


def sync(want: float, dur: float, dest: Path, zoom, focus):
    """Him speaking. Only used where the AUDIO is this interview."""
    last = None
    for off in (0, -22, 22, -50, 50, -90, 90):
        start = uncut_window(ROGAN, want + off, dur)
        raw = dest.with_suffix(".raw.mp4")
        fx.punch_in(ROGAN, start, dur, raw, zoom_from=zoom[0],
                    zoom_to=zoom[1], focus=focus)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(raw), "-an",
                "-vf", credit_vf("POWERFULJRE",
                                 "JOE ROGAN EXPERIENCE #1788"),
                *fx.ENC, str(dest)])
        raw.unlink(missing_ok=True)
        try:
            check_new(dest, dest.stem)
            return dest
        except RuntimeError as e:
            last = e
            dest.unlink(missing_ok=True)
    raise RuntimeError(f"no distinct sync window: {last}")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    for f in WORK.glob("*.mp4"):
        f.unlink()

    shots = [
        # 0-12  "most productive person ... 300 million subscribers"
        ("01_channel", 6.0, lambda p, d: shot_photo(
            YT1, d, p, push=0.26, fit=False, fy=0.40)),
        ("02_videos", 6.0, lambda p, d: shot_photo(
            YT2, d, p, push=0.22, fit=False, fy=0.58)),
        # 12-14  "least energetic people you'll ever meet"  (sync)
        ("03_sync_a", 2.0, lambda p, d: sync(
            5264.0, d, p, (1.30, 1.36), (0.47, 0.40))),
        # 14-20  "since he was 15 ... attacking him from the inside"
        ("04_teen", 6.0, lambda p, d: stock(TEEN, d, p, t0=24.0)),
        # 20-24  "this is NOT a story about a workout"
        ("05_gym", 4.0, lambda p, d: stock(B / "gym_empty.mp4", d, p)),
        # 24-30  "took things from a kid ... take some of it back"
        ("06_pair", 6.0, lambda p, d: shot_pair(d, p)),
        # 30-48  "he was an athlete, a kid who played constantly"
        ("07_balls", 6.0, lambda p, d: stock(B / "bb_cand_3.mp4", d, p)),
        ("08_bats", 6.0, lambda p, d: stock(B / "bb_cand_2.mp4", d, p)),
        ("09_aerial", 6.0, lambda p, d: stock(B / "bb_cand_4.mp4", d, p)),
        # 48-56  music-only hold
        ("10_field", 5.0, lambda p, d: stock(
            B / "baseball_field_1.mp4", d, p, zoom=0.05)),
        ("11_field2", 3.0, lambda p, d: stock(B / "bb_cand_8.mp4", d, p)),
        # 56-66  "I got Crohn's when I was 15 ... lost like 50 pounds"
        ("12_sync_b", 6.0, lambda p, d: sync(
            5200.0, d, p, (1.03, 1.10), (0.58, 0.50))),
        # No person here either. An empty field under "I lost like 50
        # pounds" says the thing the line is about.
        ("13_empty", 4.0, lambda p, d: stock(
            B / "baseball_field_2.mp4", d, p, zoom=0.05)),
    ]

    total = sum(d for _, d, _ in shots)
    print(f"[plan] {len(shots)} shots, {total:.1f}s", flush=True)

    pieces = []
    for name, dur, fn in shots:
        if dur > MAX_SHOT + 0.01:
            raise RuntimeError(f"{name} over {MAX_SHOT}s")
        p = WORK / f"{name}.mp4"
        fn(p, dur)
        if not name.startswith(("03_", "12_")):
            check_new(p, name)
        got = fx.probe_dur(p)
        if abs(got - dur) > 0.12:
            raise RuntimeError(f"{name}: {got:.2f}s vs {dur:.2f}s")
        pieces.append(p)
        print(f"  ok {name:12} {dur:.1f}s", flush=True)

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{q.absolute().as_posix()}'"
                             for q in pieces), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
            f"fps={FPS}", *fx.ENC, str(silent)], timeout=3600)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-i", str(AUDIO), "-map", "0:v:0",
            "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
            "-shortest", "-movflags", "+faststart", str(OUT)], timeout=1800)
    print(f"[OK] {OUT}  {fx.probe_dur(OUT):.1f}s | "
          f"{len(_spent)} assets, each used once | "
          f"{len(_hashes)} visually distinct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
