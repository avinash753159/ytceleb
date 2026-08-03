#!/usr/bin/env python3
"""First minute, revision 4 - cut to the EDL, not to a transcript.

Whisper merges long pauses into one segment, so its timestamps drift by
many seconds. Building against them put baseball twelve seconds before the
athlete line, on top of a silent title break. These times come from the
edit itself:

   2.00-11.89  "most productive person ... 300 million subscribers"
  11.89-13.99  bite: "least energetic people you'll ever meet"
  13.99-22.01  "since he was fifteen ... attacking him from the inside"
  22.01-30.80  "not a story about a workout ... take some of it back"
  30.80-34.00  beat
  34.00-46.00  TITLE BREAK, music only
  46.00-56.50  "he was an athlete, a kid who played constantly"
  56.50-66.10  bite: "I got Crohn's when I was 15 ... lost like 50 pounds"

Also gone: the childhood clip, and the side-by-side composite. The before
photograph opens the film and the after photograph pays it off at 26s, so
the transformation plays ACROSS the minute instead of as one static panel.
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
WORK = ROOT / "work/first_minute4"
B = ROOT / "library/broll"
MED = ROOT / "dossier/mrbeast/medical"
PRIM = ROOT / "dossier/mrbeast/primary"
ROGAN = ROOT / "dossier/mrbeast/sources/cLRLEnPaJLM.mp4"

BEFORE = PRIM / "mrbeast_transformation_2023-06-29.jpg"
AFTER = PRIM / "mrbeast_after_2025-04-21_1.jpg"
YT1 = PRIM / "yt_channel.png"
YT2 = PRIM / "yt_videos.png"

# start, end, key, builder-spec. Ends are the real edit boundaries.
CUTS = [
    (0.00, 2.00, "01_before", ("photo", BEFORE, "@MRBEAST",
                               "29 JUNE 2023", 0.10, True, 0.5)),
    (2.00, 7.00, "02_channel", ("photo", YT1, "", "", 0.26, False, 0.40)),
    (7.00, 11.89, "03_videos", ("photo", YT2, "", "", 0.22, False, 0.58)),
    (11.89, 13.99, "04_sync_a", ("sync", 5264.0, (1.30, 1.36),
                                 (0.47, 0.40))),
    (13.99, 18.00, "05_lining", ("photo", MED / "mechanism.png", "WIKIMEDIA",
                                 "CC0", 0.14, True, 0.34)),
    (18.00, 22.01, "06_tired", ("stock", B / "man_tired.mp4", None, 0.07)),
    (22.01, 26.00, "07_gym", ("stock", B / "gym_empty.mp4", None, 0.07)),
    (26.00, 30.80, "08_after", ("photo", AFTER, "@MRBEAST",
                                "21 APRIL 2025", 0.12, True, 0.5)),
    (30.80, 34.00, "09_night", ("stock", B / "bedroom_night_1.mp4",
                                None, 0.05)),
    # --- 12 seconds of music only: two held, atmospheric shots ---
    (34.00, 40.00, "10_walk", ("stock", B / "walking_alone_1.mp4",
                               None, 0.06)),
    (40.00, 46.00, "11_field", ("stock", B / "baseball_field_1.mp4",
                                None, 0.05)),
    # --- "he was an athlete, a kid who played constantly" ---
    (46.00, 51.00, "12_balls", ("stock", B / "bb_cand_3.mp4", None, 0.08)),
    (51.00, 56.50, "13_bats", ("stock", B / "bb_cand_2.mp4", None, 0.07)),
    # --- "I got Crohn's when I was 15 ... lost like 50 pounds" ---
    (56.50, 62.00, "14_sync_b", ("sync", 5200.0, (1.03, 1.10),
                                 (0.58, 0.50))),
    (62.00, 66.10, "15_aerial", ("stock", B / "bb_cand_4.mp4", None, 0.06)),
]

_spent: set[str] = set()
_hashes: list[tuple[str, np.ndarray]] = []


def spend(p: Path):
    if p.name in _spent:
        raise RuntimeError(f"ASSET REUSED: {p.name}")
    _spent.add(p.name)


def dhash(p: Path):
    a = np.asarray(Image.open(p).convert("L").resize((9, 8), Image.LANCZOS),
                   dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def check_new(piece: Path, name: str, limit=11):
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


def build_stock(path: Path, dur, dest, t0, zoom):
    spend(path)
    total = fx.probe_dur(path)
    if total < dur + 0.4:
        raise RuntimeError(f"{path.name} is {total:.1f}s, needs {dur:.1f}s "
                           f"- looping is banned")
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


def build_photo(img: Path, dur, dest, main, sub, push, fit, fy):
    spend(img)
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


def build_sync(want, dur, dest, zoom, focus):
    last = None
    for off in (0, -22, 22, -50, 50, -90, 90):
        start = uncut_window(ROGAN, want + off, dur)
        raw = dest.with_suffix(".raw.mp4")
        fx.punch_in(ROGAN, start, dur, raw, zoom_from=zoom[0],
                    zoom_to=zoom[1], focus=focus)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(raw), "-an", "-vf",
                credit_vf("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"),
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

    # The cut list must tile the timeline with no gap and no overlap.
    for (s1, e1, n1, _), (s2, _, n2, _) in zip(CUTS, CUTS[1:]):
        if abs(e1 - s2) > 1e-6:
            raise RuntimeError(f"gap/overlap between {n1} and {n2}: "
                               f"{e1:.2f} vs {s2:.2f}")

    pieces = []
    for start, end, name, spec in CUTS:
        dur = end - start
        dest = WORK / f"{name}.mp4"
        kind = spec[0]
        if kind == "photo":
            _, img, main, sub, push, fit, fy = spec
            build_photo(img, dur, dest, main, sub, push, fit, fy)
        elif kind == "stock":
            _, path, t0, zoom = spec
            build_stock(path, dur, dest, t0, zoom)
        else:
            _, want, zoom, focus = spec
            build_sync(want, dur, dest, zoom, focus)
        if kind != "sync":
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

    vdur = fx.probe_dur(silent)
    target = CUTS[-1][1]
    if abs(vdur - target) > 0.15:
        raise RuntimeError(f"picture {vdur:.2f}s but timeline says "
                           f"{target:.2f}s - it would drift against audio")

    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-i", str(AUDIO), "-map", "0:v:0",
            "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
            "-shortest", "-movflags", "+faststart", str(OUT)], timeout=1800)
    print(f"[OK] {OUT}  {fx.probe_dur(OUT):.2f}s vs timeline "
          f"{target:.2f}s | {len(_spent)} assets, each once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
