#!/usr/bin/env python3
"""Build the FIRST MINUTE only, under rules taken from the operator's notes.

HARD RULES, enforced in code rather than by intention:
  1. NO CLIP IS EVER REUSED. A global registry rejects a second draw.
  2. NO LOOPING. -stream_loop is gone. If a clip is shorter than the shot,
     the build fails loudly instead of playing the same 5 seconds twice.
     That loop was the ugliest artefact in the last cut and I wrote it.
  3. NO SHOT OVER 6 SECONDS. Long holds read as stagnant.
  4. Stills fade in and out rather than cutting hard.
  5. Aspect is preserved - portrait sources are fitted, never stretched.

The transformation now uses his own two photographs: 29 June 2023
("I was obese") and 21 April 2025 ("Go get gains boyz").
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import fx  # noqa: E402
from mrbeast_picture_v7 import (credit_vf, scene_cuts,  # noqa: E402
                                uncut_window)

W, H, FPS = fx.W, fx.H, fx.FPS
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/MRBEAST_FIRST_MINUTE.mp4"
WORK = ROOT / "work/first_minute"
BROLL = ROOT / "library/broll"
PRIM = ROOT / "dossier/mrbeast/primary"
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"

BEFORE = PRIM / "mrbeast_transformation_2023-06-29.jpg"
AFTER = PRIM / "mrbeast_after_2025-04-21_1.jpg"
ROGAN = SRC / "cLRLEnPaJLM.mp4"
TEEN = ARC / "AKJfakEsgy0.mp4"

TOTAL = 62.0
MAX_SHOT = 6.0

_used_clips: set[str] = set()
_used_windows: list[tuple[str, float]] = []


def claim(path: Path):
    """A clip may be drawn once. Second draw is a build error."""
    k = path.name
    if k in _used_clips:
        raise RuntimeError(f"clip reused: {k} - every beat needs its own")
    _used_clips.add(k)


def no_loop(path: Path, dur: float):
    total = fx.probe_dur(path)
    if total < dur + 0.4:
        raise RuntimeError(
            f"{path.name} is {total:.1f}s but the shot needs {dur:.1f}s. "
            f"Looping is banned - pick a longer clip.")
    return total


def broll(path: Path, dur: float, dest: Path, main: str, sub: str,
          t0: float | None = None):
    """Stock shot. No loop, no reuse, gentle push, correct aspect."""
    claim(path)
    total = no_loop(path, dur)
    start = t0 if t0 is not None else max(0.4, (total - dur) * 0.35)
    start = min(start, total - dur - 0.2)
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    z = f"(1.03+0.07*{p})"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},"
          f"scale=w='iw*{z}':h='ih*{z}':eval=frame,"
          f"crop={W}:{H},"
          f"fade=t=in:st=0:d=0.35,"
          f"fade=t=out:st={max(0, dur-0.35):.3f}:d=0.35,"
          + credit_vf(main, sub))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(path), "-t", f"{dur:.4f}",
            "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


def interview(path: Path, want: float, dur: float, dest: Path,
              main: str, sub: str):
    """Jimmy sync, snapped inside one camera angle and never reused.

    uncut_window returns the longest clean run near the requested moment,
    so two nearby requests resolve to the SAME run. Walk outward until a
    genuinely different angle is found rather than repeat the shot.
    """
    start = None
    for offset in (0, -18, 18, -36, 36, -54, 54, -80, 80, -120, 120):
        cand = uncut_window(path, want + offset, dur)
        if all(not (prev == path.name and abs(pt - cand) < 4.0)
               for prev, pt in _used_windows):
            start = cand
            break
    if start is None:
        raise RuntimeError(
            f"no unused uncut window in {path.name} near {want:.0f}s")
    _used_windows.append((path.name, start))
    fx.punch_in(path, start, dur, dest.with_suffix(".raw.mp4"),
                zoom_from=1.02, zoom_to=1.10)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(dest.with_suffix(".raw.mp4")), "-an",
            "-vf", credit_vf(main, sub), *fx.ENC, str(dest)])
    dest.with_suffix(".raw.mp4").unlink(missing_ok=True)
    return dest


def photo(img: Path, dur: float, dest: Path, main: str, sub: str,
          push=0.14, fit=True):
    """Single photograph, fitted (never stretched), pushed, faded."""
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,on/{n}),3))"
    z = f"1.02+{push:.3f}*{p}"
    base = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D"
            if fit else
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}")
    vf = (f"{base},scale={W*2}:-2,"
          f"zoompan=z='{z}':d={n}:x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"fade=t=in:st=0:d=0.4,"
          f"fade=t=out:st={max(0, dur-0.4):.3f}:d=0.4,"
          f"format=yuv420p," + credit_vf(main, sub))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])
    return dest


def transform_pair(dur: float, dest: Path):
    """Before and after, both his own photographs, both dated on screen.

    Each half is FITTED inside its panel, so neither portrait photo is
    stretched or cropped through his head - the fault in the last cut.
    """
    half = W // 2
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    lab = ("drawtext=fontfile='graphics/public/fonts/Anton-Regular.ttf'"
           ":text='{t}':fontcolor=white:fontsize=40"
           ":box=1:boxcolor=#E3120B:boxborderw=12:x={x}:y=h-210")
    fc = (
        f"[0:v]scale={half}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={half}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D[l];"
        f"[1:v]scale={half}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={half}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D[r];"
        f"[l][r]hstack=inputs=2,"
        f"scale=w='iw*(1.0+0.05*{p})':h='ih*(1.0+0.05*{p})':eval=frame,"
        f"crop={W}:{H},"
        f"drawbox=x={half-3}:y=0:w=6:h={H}:color=#E3120B:t=fill,"
        + lab.format(t="JUNE 2023", x=int(half * 0.5) - 120) + ","
        + lab.format(t="APRIL 2025", x=half + int(half * 0.5) - 130) + ","
        f"fade=t=in:st=0:d=0.4,format=yuv420p,"
        + credit_vf("@MRBEAST", "HIS OWN PHOTOGRAPHS, DATED"))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(BEFORE), "-loop", "1", "-i", str(AFTER),
            "-t", f"{dur:.4f}", "-an", "-filter_complex", fc,
            "-r", str(FPS), *fx.ENC, str(dest)])
    return dest


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    for f in WORK.glob("*.mp4"):
        f.unlink()
    shots: list[tuple[str, float, object]] = []

    def add(name, dur, fn):
        if dur > MAX_SHOT + 0.01:
            raise RuntimeError(f"{name}: {dur:.1f}s exceeds the "
                               f"{MAX_SHOT:.0f}s shot ceiling")
        shots.append((name, dur, fn))

    B = BROLL
    # --- 0:00-0:14  the transformation, revealed ---------------------
    # The before photo appears ONCE before the reveal. Showing it three
    # times running was the same repetition being complained about.
    add("01_before", 5.0, lambda p, d: photo(
        BEFORE, d, p, "@MRBEAST", "29 JUNE 2023 - I WAS OBESE"))
    add("02_scale", 4.0, lambda p, d: broll(
        B / "editing_desk_1.mp4", d, p, "PEXELS", "GILMER DIAZ ESTELA"))
    add("03_pair", 5.0, lambda p, d: transform_pair(d, p))
    # --- 0:14-0:24  the contradiction --------------------------------
    add("04_rogan_a", 5.0, lambda p, d: interview(
        ROGAN, 5264.0, d, p, "POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"))
    add("05_rogan_b", 5.0, lambda p, d: interview(
        ROGAN, 5272.0, d, p, "POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"))
    # --- 0:24-0:34  the machine that ate him -------------------------
    add("06_desk", 5.0, lambda p, d: broll(
        B / "editing_desk_2.mp4", d, p, "PEXELS", "NINO SOUZA"))
    add("07_alone", 5.0, lambda p, d: broll(
        B / "teen_alone_2.mp4", d, p, "PEXELS", "MIKHAIL NILOV"))
    # --- 0:34-0:46  music-only title break, held on the after --------
    add("08_after", 6.0, lambda p, d: photo(
        AFTER, d, p, "@MRBEAST", "21 APRIL 2025 - GO GET GAINS BOYZ",
        push=0.10))
    # "gym at night empty" returned a basketball hall - wrong room for a
    # film about weights. This is the actual weight-room clip.
    add("09_gym_empty", 6.0, lambda p, d: broll(
        B / "gym_empty.mp4", d, p, "PEXELS", "DS BABARIYA"))
    # --- 0:46-1:02  the body he lost: baseball -----------------------
    add("10_baseball", 5.0, lambda p, d: broll(
        B / "baseball_kid_1.mp4", d, p, "PEXELS", "GUSTAVO FRING"))
    add("11_baseball2", 5.0, lambda p, d: broll(
        B / "baseball_kid_2.mp4", d, p, "PEXELS", "GUSTAVO FRING"))
    add("12_field", 5.0, lambda p, d: broll(
        B / "baseball_field_1.mp4", d, p, "PEXELS", "STEPHEN PIERCE"))
    add("13_teen", 5.0, lambda p, d: broll(
        TEEN, d, p, "MRBEAST", "HI ME IN 5 YEARS / ARCHIVE", t0=26.0))
    add("14_rogan_c", 5.0, lambda p, d: interview(
        ROGAN, 5240.0, d, p, "POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"))

    total = sum(d for _, d, _ in shots)
    print(f"[plan] {len(shots)} shots, {total:.1f}s "
          f"(max shot {max(d for _, d, _ in shots):.1f}s)", flush=True)

    pieces = []
    for name, dur, fn in shots:
        p = WORK / f"{name}.mp4"
        fn(p, dur)
        got = fx.probe_dur(p)
        if abs(got - dur) > 0.12:
            raise RuntimeError(f"{name}: {got:.2f}s, expected {dur:.2f}s")
        pieces.append(p)
        print(f"  ok {name:14} {dur:.1f}s", flush=True)

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
            f"fps={FPS}", *fx.ENC, str(silent)], timeout=3600)

    vdur = fx.probe_dur(silent)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-ss", "0", "-t", f"{vdur:.3f}",
            "-i", str(AUDIO), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
            "-movflags", "+faststart", str(OUT)], timeout=1800)

    print(f"[OK] {OUT}  {fx.probe_dur(OUT):.1f}s, "
          f"{len(_used_clips)} distinct clips, 0 reuse, 0 loops")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
