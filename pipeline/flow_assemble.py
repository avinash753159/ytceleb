#!/usr/bin/env python3
"""Cut the picture against the locked audio, frame-exactly.

Every shot in manifest/flow_shots.json owns an integer frame count; the
counts of all 135 shots sum to exactly 17667 frames. The audio master
(final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav) runs ~2.48s
(60 frames at 24fps) longer than the last shot's picture, so a black,
faded TAIL_FRAMES pad is appended to the video only -- the audio needs no
padding, it already has that content. TOTAL_FRAMES = 17667 + 60 = 17727 is
the whole film's frame count end to end.

Each rendered piece is copy-trimmed to its exact frame count with
`-frames:v N`. A piece that comes up short is an ERROR -- it is never
padded, never frozen and never looped (`-stream_loop` is banned outright).
That rule exists because rounding across shots once accumulated 3.8
seconds of drift, and the first fix padded the gap with a frozen frame,
producing an 18-second stall in the middle of the film.

Pieces are cached on a fingerprint of their content, not on the shot name.
Shot names are positional: swap a clip (or, for a sync shot, re-derive a
different src_t0 in-point) and a name-keyed cache serves the old render
forever.

BUDGET: the owner's immediate deliverable is the first 63.75s (the first
14 shots), not the full film -- so this module takes --from/--to (seconds,
default the whole film) and assembles any contiguous, shot-boundary-
aligned range. Nothing about "the first minute" is hardcoded; the full
film is simply the default range.

Generated clips (library/veo/<shot_id>.mp4) carry a Veo-produced AAC audio
track that cannot be disabled on this API tier (see pipeline/flow_gen.py).
Real interview footage (dossier/mrbeast/sources/<source>.mp4) carries its
own audio too. Neither is used: `-an` on every piece render discards a
piece's own audio outright (not `-shortest`, which only affects a stream's
duration if it is present), and the final mux maps exactly one audio
stream -- the locked master's.

Real footage sources are 1280x720 at mixed frame rates (30, 29.97, 25,
23.976 depending on the source) and must be conformed to 24fps; generated
clips are already 720p/24fps. Both are scaled to the locked 1920x1080
output -- generated clips upscale from 720p on purpose, because every
interview source is also 720p, so upscaling is uniform across the cut
rather than a visible seam at every sync shot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/flow_shots.json"
GEN_STATUS = ROOT / "manifest/flow_gen_status.json"
VEO = ROOT / "library/veo"
# A shot generated as a still and animated with a depth push-in (flow_dibr)
# costs about $0.04 against $0.30 for the same beat as Veo video, so it is the
# default medium. This directory is checked FIRST: when a still render exists
# for a shot it wins over any Veo clip, which lets a shot be moved onto the
# cheap path without deleting the expensive one it replaces.
STILLVID = ROOT / "library/stillvid"
VIDEO_SHOTS = ROOT / "manifest/video_shots.json"

_VIDEO_IDS: set[str] | None = None


def _video_shot_ids() -> set[str]:
    """Shots deliberately chosen to keep real motion. Cached: read once."""
    global _VIDEO_IDS
    if _VIDEO_IDS is None:
        if VIDEO_SHOTS.exists():
            _VIDEO_IDS = set(json.loads(
                VIDEO_SHOTS.read_text(encoding="utf-8"))["video"])
        else:
            _VIDEO_IDS = set()
    return _VIDEO_IDS
SRC = ROOT / "dossier/mrbeast/sources"
PIECES = ROOT / "work/v12_pieces"
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V12.mp4"

FPS = 24
OUT_W, OUT_H = 1920, 1080
TOTAL_FRAMES = 17727          # 17667 shot frames + a 60-frame silent tail
TAIL_FRAMES = 60              # 2.5s -- the audio master's own trailing
                               # content past the last shot's picture
# ffmpeg will not accept "#111" as a colour -- six hex digits or it errors.
TAIL_COLOUR = "0x000000"

# ffmpeg grabs all 20 cores on this machine by default; cap every process
# so several pieces can render without starving each other / the OS.
THREADS = "2"


def fingerprint(shot: dict) -> str:
    """A short, content-keyed hash for this shot's rendered piece.

    Deliberately NOT keyed on position alone. `shot_id` is included (so a
    stale piece from a renamed/reordered shot doesn't get reused by
    accident), but so is everything that actually determines what ends up
    on screen: the prompt and frame count for a generated shot, and the
    source file plus the exact in-point (`src_t0`) for a real-footage cut.
    `src_t0` matters specifically because bite_windows.py can re-derive a
    different in-point for the same shot_id/source pair -- without it in
    the fingerprint, a corrected cut point would silently keep serving the
    old, wrong stretch of footage forever.
    """
    payload = json.dumps(
        {k: shot.get(k) for k in (
            "shot_id", "prompt", "frames", "kind", "source", "src_t0",
            "start", "end")},
        sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def piece_path(shot: dict) -> Path:
    return PIECES / f"{shot['shot_id']}_{fingerprint(shot)}.mp4"


def _load_gen_status() -> dict:
    if GEN_STATUS.exists():
        return json.loads(GEN_STATUS.read_text(encoding="utf-8"))
    return {}


def render_piece(shot: dict, gen_status: dict | None = None) -> Path:
    """Render (or reuse) one shot's frame-exact, 1920x1080/24fps piece.

    Fails loudly, naming the shot, if the source it needs isn't there --
    never silently skips a shot. For a "gen" shot that specifically means
    checking flow_gen_status.json says state == "done": only a "done"
    entry has a usable file (a "failed"/"interrupted" entry, or a leftover
    partial file from a killed run, must not be trusted just because a
    file happens to exist at that path).
    """
    dest = piece_path(shot)
    if dest.exists():
        return dest

    shot_id = shot["shot_id"]
    if shot["kind"] == "gen":
        still = STILLVID / f"{shot_id}.mp4"
        # A shot chosen for real motion prefers its Veo clip when one exists.
        # Everything else prefers the still. Veo's quota is periodic and ran
        # out mid-run, so stills are generated for the video shots too as a
        # floor: the film is always complete, and a video clip upgrades over
        # its still the moment quota allows, with no manifest edit.
        wants_video = shot_id in _video_shot_ids()
        if wants_video and (VEO / f"{shot_id}.mp4").exists():
            pass
        elif still.exists():
            # Already an eased 1920x1080/24fps render of exactly this shot's
            # frame count; it needs no seek and no further conform.
            src, ss = still, 0.0
            PIECES.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".tmp.mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(src),
                 "-frames:v", str(shot["frames"]),
                 "-an", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                 "-pix_fmt", "yuv420p", "-threads", THREADS, str(tmp)],
                check=True)
            tmp.replace(dest)
            return dest
        if gen_status is None:
            gen_status = _load_gen_status()
        state = gen_status.get(shot_id, {}).get("state")
        if state != "done":
            raise SystemExit(
                f"{shot_id}: generated clip is not done (state="
                f"{state!r}) -- cannot assemble this shot")
        src, ss = VEO / f"{shot_id}.mp4", 0.0
        if not src.exists():
            raise SystemExit(
                f"{shot_id}: ledger says done but the file is missing: "
                f"{src}")
    else:
        src = SRC / f"{shot['source']}.mp4"
        ss = shot.get("src_t0", 0.0)
        if not src.exists():
            raise SystemExit(f"{shot_id}: missing source footage {src}")

    PIECES.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(src),
         "-frames:v", str(shot["frames"]),
         "-vf", f"scale={OUT_W}:{OUT_H}:flags=lanczos,fps={FPS}",
         "-an",                                    # discard: see docstring
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-threads", THREADS, str(tmp)],
        check=True)
    tmp.replace(dest)
    return dest


_FRAME_COUNT_RE = re.compile(r"(\d+)")


def _parse_frame_count(text: str) -> int:
    """Parse ffprobe's `-count_frames` output, which is a leading integer
    but not always a clean one -- some files yield "70,\\n" (trailing
    comma), which fails a plain `str.isdigit()` check on the raw line.
    Parses the leading run of digits instead of testing the whole string.
    """
    m = _FRAME_COUNT_RE.search(text)
    if not m:
        raise ValueError(f"no frame count found in ffprobe output: {text!r}")
    return int(m.group(1))


def verify_pieces(shots: list[dict]) -> list[str]:
    """Every piece must have exactly the frames it was allocated."""
    bad = []
    for s in shots:
        p = piece_path(s)
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-count_frames", "-show_entries", "stream=nb_read_frames",
             "-of", "csv=p=0", str(p)],
            capture_output=True, text=True).stdout
        got = _parse_frame_count(out) if out.strip() else 0
        if got != s["frames"]:
            bad.append(f"{s['shot_id']}: {got} frames, wanted {s['frames']}")
    return bad


def select_range(shots: list[dict], from_sec: float, to_sec: float | None
                  ) -> tuple[list[dict], int, int, int]:
    """Pick the contiguous, shot-boundary-aligned slice covering
    [from_sec, to_sec), frame for frame.

    `to_sec=None` means the whole film, including its TAIL_FRAMES silent
    pad. Returns (selected_shots, from_frame, to_frame, tail_frames) where
    `to_frame - from_frame` is the range's own total frame count and
    `tail_frames` is how many of those are the trailing pad (0 unless the
    range reaches the film's end).

    Raises ValueError if `from_sec`/`to_sec` don't land exactly on shot
    boundaries -- a partial-shot range can't be frame-exact by
    construction, so this refuses rather than silently rounding.
    """
    offsets = []
    off = 0
    for s in shots:
        offsets.append(off)
        off += s["frames"]
    full_frames = off                              # 17667 across all shots

    from_frame = round(from_sec * FPS)
    to_frame = (full_frames + TAIL_FRAMES if to_sec is None
                else round(to_sec * FPS))

    tail_frames = max(0, to_frame - full_frames)
    if tail_frames > TAIL_FRAMES:
        raise ValueError(
            f"--to {to_sec}s ({to_frame} frames) reaches "
            f"{tail_frames - TAIL_FRAMES} frames past the film's end "
            f"({full_frames} frames) plus its {TAIL_FRAMES}-frame "
            f"silent tail")
    body_to_frame = to_frame - tail_frames

    selected = [s for s, o in zip(shots, offsets)
                if o >= from_frame and o + s["frames"] <= body_to_frame]

    covered_start = offsets[shots.index(selected[0])] if selected else None
    covered = sum(s["frames"] for s in selected)
    if (not selected or covered_start != from_frame
            or covered != body_to_frame - from_frame):
        raise ValueError(
            f"--from {from_sec}s / --to {to_sec}s do not land on shot "
            f"boundaries: requested frames [{from_frame}, {to_frame}) but "
            f"shots only cover exact spans starting/ending on their own "
            f"boundaries -- partial-shot ranges are not supported")

    return selected, from_frame, to_frame, tail_frames


def concat_and_mux(pieces: list[Path], out: Path, *,
                    audio_from: float = 0.0, audio_to: float | None = None,
                    tail_frames: int = TAIL_FRAMES,
                    total_frames: int = TOTAL_FRAMES) -> None:
    """Concat the pieces, mux against a slice of the locked master audio,
    pad the picture with `tail_frames` of black+fade if this range reaches
    the film's end, and hard-cap the output at exactly `total_frames`.

    Defaults reproduce the old whole-film behaviour (full master audio,
    the standard tail, the standard total). A partial range passes its own
    audio bounds and (usually) `tail_frames=0` so no black pad is added to
    a slice that ends mid-film.
    """
    PIECES.mkdir(parents=True, exist_ok=True)
    lst = PIECES / f"concat_{out.stem}.txt"
    lst.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8")
    body = PIECES / f"body_{out.stem}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", "-threads", THREADS, str(body)],
        check=True)

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(body),
           "-ss", f"{audio_from:.6f}"]
    if audio_to is not None:
        cmd += ["-t", f"{max(audio_to - audio_from, 0.0):.6f}"]
    cmd += ["-i", str(AUDIO)]

    if tail_frames > 0:
        cmd += ["-filter_complex",
                f"[0:v]tpad=stop_mode=add:stop_duration="
                f"{tail_frames / FPS:.6f}:color={TAIL_COLOUR}[v]",
                "-map", "[v]", "-map", "1:a"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-frames:v", str(total_frames),
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-threads", THREADS,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            str(out)]
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="from_sec", type=float, default=0.0,
                     help="range start, seconds (default: 0, film start)")
    ap.add_argument("--to", dest="to_sec", type=float, default=None,
                     help="range end, seconds (default: the whole film)")
    ap.add_argument("--out", type=Path, default=OUT,
                     help="output path (default: the full-film filename)")
    args = ap.parse_args(argv)

    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    selected, from_frame, to_frame, tail_frames = select_range(
        shots, args.from_sec, args.to_sec)
    range_frames = to_frame - from_frame

    gen_status = _load_gen_status()
    for i, s in enumerate(selected, 1):
        render_piece(s, gen_status=gen_status)
        if i % 10 == 0:
            print(f"  {i}/{len(selected)} pieces")

    bad = verify_pieces(selected)
    if bad:
        raise SystemExit("frame-count failures:\n  " + "\n  ".join(bad))

    concat_and_mux(
        [piece_path(s) for s in selected], out_path,
        audio_from=from_frame / FPS, audio_to=(to_frame - tail_frames) / FPS,
        tail_frames=tail_frames, total_frames=range_frames)
    print(f"wrote {out_path} ({range_frames} frames, "
          f"{range_frames / FPS:.3f}s, {len(selected)} shots)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
