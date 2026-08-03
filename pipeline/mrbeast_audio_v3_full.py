#!/usr/bin/env python3
"""Build the complete narration-led MrBeast V3 radio cut.

The output is a 48 kHz WAV and a review MP3 only. It deliberately does not
assemble picture. The user signs off this full radio cut before any visual
asset acquisition or video render.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["MRBEAST_SCRIPT_VERSION"] = "V3"
os.environ["MRBEAST_VOICE_MODE"] = "final"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mrbeast_radio as radio  # noqa: E402
from edl import build_edl  # noqa: E402
from v11_assemble import (  # noqa: E402
    build_audio,
    fit_run_durations,
    probe_dur,
    run,
)

MUSIC = ROOT / "dossier" / "mrbeast" / "audio_v3" / "music"
OUTDIR = ROOT / "final_video" / "mrbeast_audio_v3_full"
WORK = OUTDIR / "work"
MASTER = OUTDIR / "MRBEAST_V3_FULL_NARRATION_MASTER.wav"
REVIEW = OUTDIR / "MRBEAST_V3_FULL_NARRATION_MASTER.mp3"
CUESHEET = OUTDIR / "MRBEAST_V3_FULL_NARRATION_CUE_SHEET.json"


def loudnorm(path: Path) -> None:
    first = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-14:TP=-2.0:LRA=9:print_format=json",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        timeout=1800,
        check=True,
    )
    match = re.search(r"\{\s*\"input_i\".*?\}", first.stderr, re.S)
    if not match:
        raise RuntimeError("could not parse loudnorm first pass")
    stats = json.loads(match.group(0))
    filt = (
        "loudnorm=I=-14:TP=-2.0:LRA=9:linear=true"
        f":measured_I={stats['input_i']}"
        f":measured_TP={stats['input_tp']}"
        f":measured_LRA={stats['input_lra']}"
        f":measured_thresh={stats['input_thresh']}"
        f":offset={stats['target_offset']}"
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-af",
            filt,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            "-y",
            str(MASTER),
        ],
        timeout=1800,
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(MASTER),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "256k",
            "-ar",
            "48000",
            "-y",
            str(REVIEW),
        ]
    )


def chapter_ranges(edl):
    offsets = edl.offsets()
    out = {}
    for i, seg in enumerate(edl.segs):
        start = offsets[i]
        end = start + seg.dur
        if seg.chapter not in out:
            out[seg.chapter] = [start, end]
        else:
            out[seg.chapter][1] = end
    return out


def score_speech(speech: Path, edl):
    ranges = chapter_ranges(edl)
    # Each cue mutates at a story turn. Source offsets avoid dropping every
    # chapter on the first bar of a library track.
    cue_specs = [
        ("origin", "intervention_nomelody.mp3", 0.0, 0.18),
        ("machine", "red_no_vocals.mp3", 35.0, 0.15),
        ("contract", "red_no_vocals.mp3", 75.0, 0.19),
        ("protocol", "celestial.mp3", 0.0, 0.16),
        ("limit", "descent.mp3", 22.0, 0.13),
        ("resolution", "chasing_daylight.mp3", 30.0, 0.17),
    ]
    inputs = ["-i", str(speech)]
    filters = [
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[dialogue]"
    ]
    cue_rows = []
    cue_labels = []
    for k, (chapter, filename, source_start, volume) in enumerate(cue_specs):
        if chapter not in ranges:
            continue
        at, end = ranges[chapter]
        dur = max(end - at, 0.2)
        track = MUSIC / filename
        if not track.exists():
            raise FileNotFoundError(track)
        inputs += ["-i", str(track)]
        label = f"m{k}"
        filters.append(
            f"[{k + 1}:a]atrim=start={source_start}:end={source_start + dur:.6f},"
            "asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=2.2,afade=t=out:st={max(dur - 1.0, 0):.6f}:d=1.0,"
            f"volume={volume},aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={round(at * 1000)}:all=1[{label}]"
        )
        cue_labels.append(f"[{label}]")
        cue_rows.append(
            {
                "chapter": chapter,
                "file": filename,
                "program_t0": round(at, 3),
                "program_t1": round(end, 3),
                "source_offset": source_start,
                "volume": volume,
            }
        )

    filters.append(
        "".join(cue_labels)
        + f"amix=inputs={len(cue_labels)}:duration=longest:normalize=0[music_bus]"
    )
    filters.append(
        "[music_bus][dialogue]"
        "sidechaincompress=threshold=0.03:ratio=6:attack=12:release=300"
        "[ducked_music]"
    )
    filters.append(
        "[dialogue][ducked_music]"
        "amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.90:attack=5:release=80[mixed]"
    )
    mixed = WORK / "full_scored.wav"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[mixed]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            "-y",
            str(mixed),
        ],
        timeout=1800,
    )
    return mixed, cue_rows


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    radio.WORK.mkdir(parents=True, exist_ok=True)
    doc = radio.parse_script()
    edl = build_edl(doc)
    narr_runs = radio.draft_runs(radio.narration_texts(edl))
    fit_run_durations(edl, [probe_dur(p) for p in narr_runs])

    source_paths = {
        seg.source: radio.SOURCES / f"{seg.source}.mp4"
        for seg in edl.segs
        if seg.kind == "bite"
    }
    missing = [str(p) for p in source_paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("missing source video(s):\n" + "\n".join(missing))

    speech = build_audio(edl, narr_runs, source_paths, WORK)
    scored, cue_rows = score_speech(speech, edl)
    loudnorm(scored)

    narration_seconds = sum(seg.dur for seg in edl.segs if seg.kind == "narr")
    bite_seconds = sum(seg.dur for seg in edl.segs if seg.kind == "bite")
    payload = {
        "status": "full_audio_for_user_approval_not_audio_lock",
        "runtime_seconds": round(probe_dur(MASTER), 3),
        "narration_seconds": round(narration_seconds, 3),
        "verified_bite_seconds": round(bite_seconds, 3),
        "narration_share_estimate": round(narration_seconds / edl.total(), 4),
        "segments": len(edl.segs),
        "narration_runs": len(narr_runs),
        "voice": {
            "provider": "ElevenLabs",
            "name": "Brian",
            "voice_id": "nPczCjzI2devNBz1zQrb",
            "model": "eleven_multilingual_v2",
        },
        "music": cue_rows,
        "music_license": {
            "license": "Creative Commons Attribution 4.0 International",
            "creator": "Scott Buckley",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "library_use_url": "https://www.scottbuckley.com.au/library/using-this-music/",
            "attribution": [
                '"Intervention" by Scott Buckley, licensed under CC BY 4.0: https://www.scottbuckley.com.au/library/intervention/',
                '"Red" by Scott Buckley, licensed under CC BY 4.0: https://www.scottbuckley.com.au/library/red/',
                '"Celestial" by Scott Buckley, licensed under CC BY 4.0: https://www.scottbuckley.com.au/library/celestial/',
                '"Descent" by Scott Buckley, licensed under CC BY 4.0: https://www.scottbuckley.com.au/library/descent/',
                '"Chasing Daylight" by Scott Buckley, licensed under CC BY 4.0: https://www.scottbuckley.com.au/library/chasing-daylight/',
            ],
        },
        "outputs": {
            "wav_48khz_24bit": str(MASTER.relative_to(ROOT)),
            "mp3_review_256kbps": str(REVIEW.relative_to(ROOT)),
        },
        "approval_gate": "No picture work until this full audio master is explicitly approved.",
    }
    CUESHEET.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[OK] WAV: {MASTER}")
    print(f"[OK] MP3: {REVIEW}")
    print(f"[OK] Cue sheet: {CUESHEET}")
    print(f"[OK] Runtime: {probe_dur(MASTER):.3f}s")
    print(f"[OK] Narration share: {narration_seconds / edl.total():.1%}")
    print(f"[OK] Verified bites: {bite_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
