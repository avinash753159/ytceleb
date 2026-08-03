#!/usr/bin/env python3
"""First minute, revision 2. Every change traces to a specific note.

  "why is that a video editor showing up ... take a picture of his YouTube
   account and zoom into that"        -> real @MrBeast channel screenshot
  "why is there a guy playing guitar" -> cut, replaced with his own archive
  "don't put in sources like Pexels"  -> stock carries NO on-screen credit;
                                          attribution moves to the
                                          description. Only the interviews,
                                          which genuinely require it, are
                                          credited on screen.
  "why is it a black kid playing baseball"
      -> no stand-in child at all. The beat now runs on equipment and the
         field, so nothing is cast as young Jimmy and nothing mismatches.
  "you're using the same Joe Rogan clips ... 1:07 is exactly 0:23"
      -> perceptual hashing. A shot is rejected if it LOOKS like one
         already used, not merely if its timecode differs.
  "you can include the real interview clip of him talking about this"
      -> the actual "I got Crohn's when I was 15 ... I lost like 50 pounds"
         window closes the minute.
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
WORK = ROOT / "work/first_minute2"
B = ROOT / "library/broll"
PRIM = ROOT / "dossier/mrbeast/primary"
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"

BEFORE = PRIM / "mrbeast_transformation_2023-06-29.jpg"
AFTER = PRIM / "mrbeast_after_2025-04-21_1.jpg"
YT = PRIM / "yt_channel.png"
ROGAN = SRC / "cLRLEnPaJLM.mp4"
TEEN = ARC / "AKJfakEsgy0.mp4"
MAX_SHOT = 6.0

_clips: set[str] = set()
_hashes: list[tuple[str, np.ndarray]] = []


def dhash(img_path: Path) -> np.ndarray:
    im = Image.open(img_path).convert("L").resize((9, 8), Image.LANCZOS)
    a = np.asarray(im, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def assert_looks_new(piece: Path, name: str, limit: int = 12):
    """Reject a shot that LOOKS like one already used.

    Timecode uniqueness was not enough: the podcast cycles two or three
    camera angles, so different timestamps produced visually identical
    shots. This compares the actual pictures.
    """
    tmp = WORK / f"_h_{name}.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "1.5", "-i", str(piece), "-frames:v", "1",
                    "-vf", "scale=64:64", str(tmp)], check=True, timeout=300)
    h = dhash(tmp)
    tmp.unlink(missing_ok=True)
    for prev, ph in _hashes:
        dist = int(np.count_nonzero(h != ph))
        if dist < limit:
            raise RuntimeError(
                f"{name} looks like {prev} (hamming {dist} < {limit}) - "
                f"pick a visually different angle")
    _hashes.append((name, h))


def claim(path: Path):
    if path.name in _clips:
        raise RuntimeError(f"clip reused: {path.name}")
    _clips.add(path.name)


def no_loop(path: Path, dur: float) -> float:
    total = fx.probe_dur(path)
    if total < dur + 0.4:
        raise RuntimeError(f"{path.name} is {total:.1f}s, shot needs "
                           f"{dur:.1f}s - looping is banned")
    return total


def stock(path: Path, dur: float, dest: Path, t0: float | None = None):
    """Stock b-roll. No on-screen credit - attribution is in the
    description, which is what the licence actually asks for."""
    claim(path)
    total = no_loop(path, dur)
    start = t0 if t0 is not None else max(0.4, (total - dur) * 0.3)
    start = min(start, total - dur - 0.2)
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},"
          f"scale=w='iw*(1.03+0.07*{p})':h='ih*(1.03+0.07*{p})':eval=frame,"
          f"crop={W}:{H},"
          f"fade=t=in:st=0:d=0.35,"
          f"fade=t=out:st={max(0, dur-0.35):.3f}:d=0.35")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(path), "-t", f"{dur:.4f}",
            "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


def interview(path: Path, want: float, dur: float, dest: Path,
              main: str, sub: str, zoom=(1.02, 1.10), focus=(0.5, 0.5)):
    """Jimmy sync.

    The audio IS this interview, so the picture must be him speaking - a
    different source would be a voice/picture mismatch. The podcast only
    has two or three angles, so distinctness comes from FRAMING instead:
    a wide, a tight close-up and an off-centre punch read as different
    shots even when the camera behind them is the same.
    """
    last = None
    for off in (0, -20, 20, -45, 45, -75, 75, -110, 110, -160, 160):
        start = uncut_window(path, want + off, dur)
        raw = dest.with_suffix(".raw.mp4")
        fx.punch_in(path, start, dur, raw, zoom_from=zoom[0],
                    zoom_to=zoom[1], focus=focus)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(raw), "-an", "-vf", credit_vf(main, sub),
                *fx.ENC, str(dest)])
        raw.unlink(missing_ok=True)
        try:
            assert_looks_new(dest, dest.stem)
            return dest
        except RuntimeError as e:
            last = e
            dest.unlink(missing_ok=True)
    raise RuntimeError(f"no visually distinct window in {path.name}: {last}")


def photo(img: Path, dur: float, dest: Path, main: str, sub: str,
          push=0.14, fit=True, focus_y=0.5):
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,on/{n}),3))"
    base = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D" if fit else
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}")
    vf = (f"{base},scale={W*2}:-2,"
          f"zoompan=z='1.02+{push:.3f}*{p}':d={n}:"
          f"x='iw/2-(iw/zoom/2)':y='ih*{focus_y}-(ih/zoom/2)':"
          f"s={W}x{H}:fps={FPS},"
          f"fade=t=in:st=0:d=0.4,"
          f"fade=t=out:st={max(0, dur-0.4):.3f}:d=0.4,"
          f"format=yuv420p")
    if main:
        vf += "," + credit_vf(main, sub)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])
    return dest


def pair(dur: float, dest: Path):
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
          f"fade=t=in:st=0:d=0.4,format=yuv420p,"
          + credit_vf("@MRBEAST", "HIS OWN PHOTOGRAPHS"))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(BEFORE), "-loop", "1", "-i", str(AFTER),
            "-t", f"{dur:.4f}", "-an", "-filter_complex", fc,
            "-r", str(FPS), *fx.ENC, str(dest)])
    return dest


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    for f in WORK.glob("*.mp4"):
        f.unlink()
    JRE = ("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788")
    shots = [
        ("01_before", 5.0, lambda p, d: photo(
            BEFORE, d, p, "@MRBEAST", "29 JUNE 2023 - I WAS OBESE")),
        # "a story about a kid on YouTube" - so show the channel itself.
        ("02_youtube", 5.0, lambda p, d: photo(
            YT, d, p, "", "", push=0.30, fit=False, focus_y=0.42)),
        ("03_pair", 5.0, lambda p, d: pair(d, p)),
        # Three Rogan shots, three distinct framings: wide, tight, offset.
        ("04_rogan_a", 5.0, lambda p, d: interview(
            ROGAN, 5264.0, d, p, *JRE, zoom=(1.02, 1.09))),
        ("05_teen", 5.0, lambda p, d: stock(TEEN, d, p, t0=26.0)),
        ("06_rogan_b", 6.0, lambda p, d: interview(
            ROGAN, 5330.0, d, p, *JRE, zoom=(1.34, 1.44),
            focus=(0.46, 0.40))),
        ("07_after", 6.0, lambda p, d: photo(
            AFTER, d, p, "@MRBEAST", "21 APRIL 2025", push=0.10)),
        ("08_gym", 6.0, lambda p, d: stock(B / "gym_empty.mp4", d, p)),
        # Baseball WITHOUT a stand-in child: equipment and the field.
        ("09_balls", 5.0, lambda p, d: stock(B / "bb_cand_3.mp4", d, p)),
        ("10_bats", 5.0, lambda p, d: stock(B / "bb_cand_2.mp4", d, p)),
        ("11_field", 5.0, lambda p, d: stock(
            B / "baseball_field_1.mp4", d, p)),
        # The real clip: "I got Crohn's when I was 15 ... lost like 50 lbs"
        ("12_crohns", 5.0, lambda p, d: interview(
            ROGAN, 5200.0, d, p, *JRE, zoom=(1.18, 1.26),
            focus=(0.60, 0.46))),
    ]
    total = sum(d for _, d, _ in shots)
    print(f"[plan] {len(shots)} shots, {total:.1f}s", flush=True)

    pieces = []
    for name, dur, fn in shots:
        if dur > MAX_SHOT + 0.01:
            raise RuntimeError(f"{name} exceeds {MAX_SHOT}s")
        p = WORK / f"{name}.mp4"
        fn(p, dur)
        if name.startswith(("05", "08", "09", "10", "11")):
            assert_looks_new(p, name)
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
          f"{len(_clips)} clips, {len(_hashes)} hash-checked, 0 loops")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
