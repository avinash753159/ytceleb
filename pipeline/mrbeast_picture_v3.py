#!/usr/bin/env python3
"""Render the narration-first MrBeast V3 picture cut with source labels.

The locked V3 performance is reused. Its initial interview bite is moved behind
the complete opening narration run, matching the corrected audio master.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["MRBEAST_SCRIPT_VERSION"] = "V3"
os.environ["MRBEAST_VOICE_MODE"] = "final"

import mrbeast_radio as radio  # noqa: E402
from edl import build_edl  # noqa: E402
from v11_assemble import fit_run_durations, probe_dur  # noqa: E402

W, H, FPS = 1920, 1080, 30
FONT = "graphics/public/fonts/Anton-Regular.ttf"
OUT = ROOT / "final_video" / "THE_DISEASE_THAT_BUILT_MRBEAST_V3.mp4"
WORK = ROOT / "work" / "mrbeast_picture_v3"
AUDIO = ROOT / "final_video" / "mrbeast_audio_v3_corrected" / "MRBEAST_V3_NARRATION_FIRST_MASTER.wav"

SOURCE_META = {
    "FjrJ2DJN_pA": ("THE DIARY OF A CEO", "YOUTUBE / INTERVIEW"),
    "cLRLEnPaJLM": ("POWERFULJRE", "YOUTUBE / INTERVIEW"),
    "9IQ_ldV9z_A": ("COLIN AND SAMIR", "YOUTUBE / INTERVIEW"),
    "7r3ORKgNUjw": ("AIRRACK", "YOUTUBE / DOCUMENTARY"),
    "WwVs1qVaOb4": ("CHRIS HEMSWORTH", "YOUTUBE / SEPT. 2024"),
    "AKJfakEsgy0": ("MRBEAST", "YOUTUBE / RECORDED OCT. 2015"),
    "2XVcLrB7B3Y": ("MRBEAST", "YOUTUBE / 2012 UPLOAD"),
}

DOCS = {
    "n006": ("dossier/mrbeast/documents/niddk_definition.png", "NIH-NIDDK", "CROHN'S DISEASE OVERVIEW"),
    "n032": ("dossier/mrbeast/documents/niddk_diet.png", "NIH-NIDDK", "EATING, DIET & NUTRITION"),
    "n044": ("dossier/mrbeast/documents/niddk_treatment.png", "NIH-NIDDK", "TREATMENT CONTEXT"),
}

SPECIAL_VISUALS = {
    "n018": ("AKJfakEsgy0", 88.0),
    "n051": ("AKJfakEsgy0", 69.0),
    "n054": ("AKJfakEsgy0", 49.0),
}

# Distinct contextual windows. Interview bites always remain on their native
# picture; narration uses dated archive or later workout evidence as indicated.
CHAPTER_ROLL = {
    "open": [("AKJfakEsgy0", 32.0), ("2XVcLrB7B3Y", 22.0)],
    "origin": [("AKJfakEsgy0", 49.0), ("AKJfakEsgy0", 69.0), ("2XVcLrB7B3Y", 7.0)],
    "machine": [("FjrJ2DJN_pA", 570.0), ("cLRLEnPaJLM", 130.0), ("AKJfakEsgy0", 95.0)],
    "contract": [("7r3ORKgNUjw", 430.67), ("7r3ORKgNUjw", 454.0), ("9IQ_ldV9z_A", 700.0)],
    "protocol": [("WwVs1qVaOb4", 117.0), ("7r3ORKgNUjw", 98.3), ("WwVs1qVaOb4", 132.91)],
    "limit": [("7r3ORKgNUjw", 1028.0), ("7r3ORKgNUjw", 1048.46), ("FjrJ2DJN_pA", 981.36)],
    "resolution": [("AKJfakEsgy0", 109.0), ("7r3ORKgNUjw", 1102.86), ("WwVs1qVaOb4", 143.23)],
}


def run(args: list[str], timeout: int = 3600) -> None:
    subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)


def esc(value: str) -> str:
    return value.replace("\\", r"\\").replace(":", r"\:").replace("'", "").replace("%", r"\%")


def label_filter(source: str, detail: str) -> str:
    source, detail = esc(source), esc(detail)
    return (
        "drawbox=x=34:y=ih-128:w=620:h=84:color=black@0.72:t=fill,"
        "drawbox=x=34:y=ih-128:w=7:h=84:color=#E3120B:t=fill,"
        f"drawtext=fontfile='{FONT}':text='SOURCE\\: {source}':fontcolor=white:fontsize=30:x=58:y=h-116,"
        f"drawtext=fontfile='{FONT}':text='{detail}':fontcolor=#CFCFCF:fontsize=21:x=58:y=h-76"
    )


def source_piece(path: Path, t0: float, dur: float, out: Path, source: str, detail: str) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
        + label_filter(source, detail) + ",format=yuv420p"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t0:.3f}",
        "-i", str(path), "-t", f"{dur:.6f}", "-an", "-vf", vf, "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out),
    ])


def document_piece(path: Path, dur: float, out: Path, source: str, detail: str) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#101010,"
        + label_filter(source, detail) + ",format=yuv420p"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(path),
        "-t", f"{dur:.6f}", "-an", "-vf", vf, "-r", str(FPS), "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out),
    ])


def card_piece(title: str, subtitle: str, dur: float, out: Path) -> None:
    vf = (
        f"drawbox=x=0:y=0:w=18:h={H}:color=#E3120B:t=fill,"
        "drawbox=x=110:y=286:w=1700:h=4:color=#E3120B:t=fill,"
        f"drawtext=fontfile='{FONT}':text='{esc(title)}':fontcolor=white:fontsize=96:x=(w-text_w)/2:y=360,"
        f"drawtext=fontfile='{FONT}':text='{esc(subtitle)}':fontcolor=#D0D0D0:fontsize=38:x=(w-text_w)/2:y=505,"
        "format=yuv420p"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
        f"color=c=#090909:s={W}x{H}:r={FPS}", "-t", f"{dur:.6f}", "-an", "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out),
    ])


def timeline():
    doc = radio.parse_script()
    edl = build_edl(doc)
    all_runs = sorted((ROOT / "final_video/mrbeast_radio_v3_final").glob("vo_run_*.wav"))
    run_count = len(radio.narration_texts(edl))
    runs = all_runs[:run_count]
    fit_run_durations(edl, [probe_dur(p) for p in runs])
    segs = list(edl.segs)
    # Original V3: bite, three contiguous narration segments, beat. The
    # corrected master is: those three narration segments, bite, beat.
    return [segs[1], segs[2], segs[3], segs[0], *segs[4:]]


def main() -> int:
    if not AUDIO.exists():
        raise FileNotFoundError(AUDIO)
    WORK.mkdir(parents=True, exist_ok=True)
    segs = timeline()
    counters: dict[str, int] = {}
    pieces: list[Path] = []
    manifest = []
    for i, seg in enumerate(segs):
        out = WORK / f"{i:03d}_{seg.seg_id}.mp4"
        pieces.append(out)
        if seg.seg_id in DOCS:
            rel, source, detail = DOCS[seg.seg_id]
            document_piece(ROOT / rel, seg.dur, out, source, detail)
            visual = rel
        elif seg.kind == "bite":
            source, detail = SOURCE_META[seg.source]
            source_piece(radio.SOURCES / f"{seg.source}.mp4", seg.t0, seg.dur, out, source, detail)
            visual = seg.source
        elif seg.kind in {"beat", "card"}:
            card_piece(seg.chapter.upper(), "THE DISEASE THAT BUILT MRBEAST", seg.dur, out)
            visual = "editorial_card"
        else:
            roll = CHAPTER_ROLL[seg.chapter]
            idx = counters.get(seg.chapter, 0)
            source_id, t0 = SPECIAL_VISUALS.get(seg.seg_id, roll[idx % len(roll)])
            counters[seg.chapter] = idx + 1
            source, detail = SOURCE_META[source_id]
            path = ROOT / (f"dossier/mrbeast/archive/{source_id}.mp4" if source_id in {"AKJfakEsgy0", "2XVcLrB7B3Y"} else f"dossier/mrbeast/sources/{source_id}.mp4")
            if seg.seg_id not in SPECIAL_VISUALS:
                t0 += (idx // len(roll)) * 18.0
            source_piece(path, t0, seg.dur, out, source, detail)
            visual = source_id
        manifest.append({"id": seg.seg_id, "duration": round(seg.dur, 6), "visual": visual})

    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8")
    silent = WORK / "picture_silent.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-pix_fmt", "yuv420p", str(silent)], timeout=7200)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent), "-i", str(AUDIO),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-shortest", "-movflags", "+faststart", str(OUT)], timeout=3600)
    (WORK / "picture_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
