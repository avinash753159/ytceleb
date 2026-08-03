#!/usr/bin/env python3
"""Build the audio-only V3 MrBeast cold-open approval prototype.

This deliberately produces no video. It combines a small amount of final
ElevenLabs narration with frame/transcript-verified podcast bites and licensed
Scott Buckley score cues. Picture work remains blocked until the user approves
the later full radio master.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "final_video" / "mrbeast_audio_v3_prototype"
WORK = OUTDIR / "work"
SOURCES = ROOT / "dossier" / "mrbeast" / "sources"
MUSIC = ROOT / "dossier" / "mrbeast" / "audio_v3" / "music"
MASTER = OUTDIR / "MRBEAST_V3_COLD_OPEN_PROTOTYPE.wav"
REVIEW = OUTDIR / "MRBEAST_V3_COLD_OPEN_PROTOTYPE.mp3"
CUESHEET = OUTDIR / "MRBEAST_V3_COLD_OPEN_CUE_SHEET.json"

VOICE_ID = "nPczCjzI2devNBz1zQrb"  # ElevenLabs Brian
VOICE_MODEL = "eleven_multilingual_v2"
EDGE_FADE = 0.018


SEGMENTS = [
    {
        "id": "bite_weight_collapse",
        "kind": "bite",
        "source": "FjrJ2DJN_pA",
        "t0": 825.00,
        "dur": 16.00,
        "speaker": "Jimmy Donaldson",
        "text": (
            "When I turned 15, I got Crohn's and I went from like 190 pounds "
            "down to 139. I lost all muscle I had, and so I was like, all "
            "right, I'm not playing baseball in college anymore. So then I "
            "was like, it's just all in on YouTube."
        ),
    },
    {"id": "silence_after_origin", "kind": "silence", "dur": 1.20},
    {
        "id": "narr_title_correction",
        "kind": "narr",
        "text": (
            "Crohn's did not build MrBeast. But in Jimmy's account, it ended "
            "one future just as another obsession took over."
        ),
    },
    {
        "id": "bite_decade_obsession",
        "kind": "bite",
        "source": "cLRLEnPaJLM",
        "t0": 174.00,
        "dur": 7.10,
        "speaker": "Jimmy Donaldson",
        "text": (
            "I was as awkward as they came—no money, no nothing—and I just "
            "basically obsessed over YouTube every day for a decade."
        ),
    },
    {"id": "silence_before_neglect", "kind": "silence", "dur": 0.85},
    {
        "id": "bite_self_neglect",
        "kind": "bite",
        "source": "9IQ_ldV9z_A",
        "t0": 755.96,
        "dur": 18.64,
        "speaker": "Jimmy Donaldson",
        "text": (
            "I was so laser-focused on the channel, and I just realized one "
            "day: I have not been working out or taking care of myself. Then "
            "I called Eric and I was like, this is a problem. Let's do this."
        ),
    },
    {
        "id": "narr_accountability",
        "kind": "narr",
        "text": (
            "So he made the behavior observable: a partner, a rule, and stakes."
        ),
    },
    {
        "id": "bite_day_310_contract",
        "kind": "bite",
        "source": "9IQ_ldV9z_A",
        "t0": 731.96,
        "dur": 22.64,
        "speaker": "Jimmy Donaldson",
        "text": (
            "Today was day 310. Me and Eric signed a contract: we'd work out "
            "every day, and if we didn't we'd get a tattoo of each other. "
            "You're okay to have a day off if it's an actual part of your "
            "program, so occasionally we have rest days. For the most part, "
            "we've worked out every single day and held each other accountable."
        ),
    },
    {"id": "silence_before_verdict", "kind": "silence", "dur": 1.15},
    {
        "id": "narr_verdict_setup",
        "kind": "narr",
        "text": "After hundreds of days, Jimmy admitted this.",
    },
    {
        "id": "bite_progress_verdict",
        "kind": "bite",
        "source": "7r3ORKgNUjw",
        "t0": 1083.02,
        "dur": 3.88,
        "speaker": "Jimmy Donaldson",
        "text": (
            "I tell Alex all the time, I can't believe how little progress "
            "I've made in the amount of time."
        ),
    },
    {"id": "silence_after_verdict", "kind": "silence", "dur": 1.00},
    {
        "id": "narr_central_question",
        "kind": "narr",
        "text": (
            "What could a contract control—and what would his body refuse "
            "to guarantee?"
        ),
    },
]


def run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [str(x) for x in cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(str(x) for x in cmd[:18])
            + "\n"
            + (result.stderr or "")[-3000:]
        )
    return result


def duration(path: Path) -> float:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    return float(result.stdout.strip())


def tts_path(seg: dict, index: int) -> Path:
    text = seg["text"]
    digest = hashlib.sha256(
        (VOICE_ID + "\n" + VOICE_MODEL + "\n" + text).encode("utf-8")
    ).hexdigest()
    mp3 = WORK / f"narr_{index:02d}_{seg['id']}.mp3"
    stamp = mp3.with_suffix(".sha256")
    if (
        mp3.exists()
        and mp3.stat().st_size > 1000
        and stamp.exists()
        and stamp.read_text(encoding="ascii").strip() == digest
    ):
        return mp3

    key_path = ROOT / "elevenlabs_key.txt"
    if not key_path.exists():
        raise FileNotFoundError(f"Missing ElevenLabs key: {key_path}")
    key = key_path.read_text(encoding="utf-8").strip()
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        params={"output_format": "mp3_44100_192"},
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "model_id": VOICE_MODEL,
            "voice_settings": {
                "stability": 0.42,
                "similarity_boost": 0.78,
                "style": 0.22,
                "use_speaker_boost": True,
            },
        },
        timeout=180,
    )
    response.raise_for_status()
    mp3.write_bytes(response.content)
    stamp.write_text(digest, encoding="ascii")
    return mp3


def dialogue_filter() -> str:
    return (
        "highpass=f=65,"
        "lowpass=f=16500,"
        "loudnorm=I=-16:TP=-2.0:LRA=7,"
        "aformat=sample_rates=48000:channel_layouts=stereo"
    )


def prepare_segments() -> list[dict]:
    prepared: list[dict] = []
    narr_index = 0
    for index, source_seg in enumerate(SEGMENTS):
        seg = dict(source_seg)
        dst = WORK / f"seg_{index:02d}_{seg['id']}.wav"
        if seg["kind"] == "bite":
            source = SOURCES / f"{seg['source']}.mp4"
            if not source.exists():
                raise FileNotFoundError(source)
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{seg['t0']:.3f}",
                    "-t",
                    f"{seg['dur']:.3f}",
                    "-i",
                    str(source),
                    "-vn",
                    "-af",
                    dialogue_filter(),
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-c:a",
                    "pcm_s24le",
                    "-y",
                    str(dst),
                ]
            )
        elif seg["kind"] == "narr":
            raw = tts_path(seg, narr_index)
            narr_index += 1
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(raw),
                    "-af",
                    dialogue_filter(),
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-c:a",
                    "pcm_s24le",
                    "-y",
                    str(dst),
                ]
            )
            seg["dur"] = duration(dst)
        else:
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=stereo",
                    "-t",
                    f"{seg['dur']:.3f}",
                    "-c:a",
                    "pcm_s24le",
                    "-y",
                    str(dst),
                ]
            )

        measured = duration(dst)
        seg["dur"] = measured
        seg["prepared"] = dst
        prepared.append(seg)
    return prepared


def speech_master(prepared: list[dict]) -> tuple[Path, dict[str, float]]:
    cursor = 0.0
    starts: dict[str, float] = {}
    faded: list[Path] = []
    for index, seg in enumerate(prepared):
        starts[seg["id"]] = cursor
        cursor += seg["dur"]
        src = seg["prepared"]
        dst = WORK / f"fade_{index:02d}_{seg['id']}.wav"
        if seg["kind"] == "silence":
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(src),
                    "-c:a",
                    "pcm_s24le",
                    "-y",
                    str(dst),
                ]
            )
        else:
            out_start = max(seg["dur"] - EDGE_FADE, 0)
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(src),
                    "-af",
                    (
                        f"afade=t=in:d={EDGE_FADE},"
                        f"afade=t=out:st={out_start:.6f}:d={EDGE_FADE}"
                    ),
                    "-c:a",
                    "pcm_s24le",
                    "-y",
                    str(dst),
                ]
            )
        faded.append(dst)

    listfile = WORK / "speech_concat.txt"
    listfile.write_text(
        "\n".join(f"file '{p.absolute().as_posix()}'" for p in faded),
        encoding="utf-8",
    )
    speech = WORK / "speech_master.wav"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listfile),
            "-c:a",
            "pcm_s24le",
            "-y",
            str(speech),
        ]
    )
    return speech, starts


def mix_score(
    speech: Path, prepared: list[dict], starts: dict[str, float]
) -> tuple[Path, list[dict]]:
    by_id = {seg["id"]: seg for seg in prepared}

    cue0_at = 2.0
    cue0_end = starts["silence_after_origin"]
    cue0_dur = cue0_end - cue0_at

    cue1_at = starts["narr_title_correction"]
    cue1_end = (
        starts["bite_decade_obsession"] + by_id["bite_decade_obsession"]["dur"]
    )
    cue1_dur = cue1_end - cue1_at

    # Let the score emerge only near “this is a problem,” then build through
    # the stakes. The last portion is attenuated so programmed rest is clear.
    cue2_at = max(
        starts["bite_self_neglect"]
        + by_id["bite_self_neglect"]["dur"]
        - 4.0,
        0,
    )
    cue2_end = (
        starts["bite_day_310_contract"]
        + by_id["bite_day_310_contract"]["dur"]
    )
    cue2_dur = cue2_end - cue2_at
    rest_drop_local = max(cue2_dur - 11.0, 0)

    cue3_at = starts["narr_central_question"]
    cue3_dur = by_id["narr_central_question"]["dur"]

    intervention = MUSIC / "intervention_nomelody.mp3"
    red = MUSIC / "red_no_vocals.mp3"
    for path in (intervention, red):
        if not path.exists():
            raise FileNotFoundError(path)

    mixed = WORK / "scored_mix.wav"
    fc = ";".join(
        [
            "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[dialogue]",
            (
                f"[1:a]atrim=start=0:end={cue0_dur:.6f},"
                "asetpts=PTS-STARTPTS,"
                f"afade=t=in:d=3.2,afade=t=out:st={max(cue0_dur - 0.45, 0):.6f}:d=0.45,"
                "volume=0.14,"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                f"adelay={round(cue0_at * 1000)}:all=1[opening_score]"
            ),
            (
                f"[1:a]atrim=start=8:end={8 + cue1_dur:.6f},"
                "asetpts=PTS-STARTPTS,"
                f"afade=t=in:d=2.2,afade=t=out:st={max(cue1_dur - 0.8, 0):.6f}:d=0.8,"
                "volume=0.20,"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                f"adelay={round(cue1_at * 1000)}:all=1[origin_score]"
            ),
            (
                f"[2:a]atrim=start=46:end={46 + cue2_dur:.6f},"
                "asetpts=PTS-STARTPTS,"
                f"afade=t=in:d=2.8,afade=t=out:st={max(cue2_dur - 0.25, 0):.6f}:d=0.25,"
                "volume=0.24,"
                f"volume=0.34:enable='gte(t,{rest_drop_local:.6f})',"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                f"adelay={round(cue2_at * 1000)}:all=1[pact_score]"
            ),
            (
                f"[1:a]atrim=start=196:end={196 + cue3_dur:.6f},"
                "asetpts=PTS-STARTPTS,"
                f"afade=t=in:d=0.7,afade=t=out:st={max(cue3_dur - 0.6, 0):.6f}:d=0.6,"
                "volume=0.16,"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                f"adelay={round(cue3_at * 1000)}:all=1[question_score]"
            ),
            (
                "[opening_score][origin_score][pact_score][question_score]"
                "amix=inputs=4:duration=longest:normalize=0[music_bus]"
            ),
            (
                "[music_bus][dialogue]"
                "sidechaincompress=threshold=0.03:ratio=6:attack=12:release=300"
                "[ducked_music]"
            ),
            (
                "[dialogue][ducked_music]"
                "amix=inputs=2:duration=first:normalize=0,"
                "alimiter=limit=0.90:attack=5:release=80[scored]"
            ),
        ]
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(speech),
            "-i",
            str(intervention),
            "-i",
            str(red),
            "-filter_complex",
            fc,
            "-map",
            "[scored]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            "-y",
            str(mixed),
        ]
    )
    cues = [
        {
            "track": "Intervention (No Melody) — Scott Buckley",
            "file": intervention.name,
            "official_url": (
                "https://www.scottbuckley.com.au/library/intervention/"
            ),
            "program_t0": round(cue0_at, 3),
            "program_t1": round(cue0_end, 3),
            "purpose": (
                "barely audible tonal tension under the opening testimony; "
                "first two seconds remain completely dry"
            ),
        },
        {
            "track": "Intervention (No Melody) — Scott Buckley",
            "file": intervention.name,
            "official_url": (
                "https://www.scottbuckley.com.au/library/intervention/"
            ),
            "program_t0": round(cue1_at, 3),
            "program_t1": round(cue1_end, 3),
            "purpose": "origin correction and obsession; unresolved low texture",
        },
        {
            "track": "Red (No Vocals) — Scott Buckley",
            "file": red.name,
            "official_url": "https://www.scottbuckley.com.au/library/red/",
            "program_t0": round(cue2_at, 3),
            "program_t1": round(cue2_end, 3),
            "purpose": (
                "self-neglect decision and accountability stakes; attenuated "
                "during programmed-rest qualification"
            ),
        },
        {
            "track": "Intervention (No Melody) — Scott Buckley",
            "file": intervention.name,
            "official_url": (
                "https://www.scottbuckley.com.au/library/intervention/"
            ),
            "program_t0": round(cue3_at, 3),
            "program_t1": round(cue3_at + cue3_dur, 3),
            "purpose": "unresolved central question",
        },
    ]
    return mixed, cues


def loudness_master(scored: Path) -> None:
    first = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(scored),
            "-af",
            "loudnorm=I=-14:TP=-2.0:LRA=9:print_format=json",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    match = re.search(r"\{\s*\"input_i\".*?\}", first.stderr, re.S)
    if not match:
        raise RuntimeError("Could not parse loudnorm first-pass statistics")
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
            str(scored),
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
        ]
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


def write_cue_sheet(
    prepared: list[dict], starts: dict[str, float], music_cues: list[dict]
) -> None:
    timeline = []
    for seg in prepared:
        item = {
            "id": seg["id"],
            "kind": seg["kind"],
            "program_t0": round(starts[seg["id"]], 3),
            "program_t1": round(starts[seg["id"]] + seg["dur"], 3),
        }
        for key in ("source", "t0", "speaker", "text"):
            if key in seg:
                item[key] = seg[key]
        timeline.append(item)

    payload = {
        "status": "prototype_for_user_approval_not_audio_lock",
        "voice": {
            "provider": "ElevenLabs",
            "name": "Brian",
            "voice_id": VOICE_ID,
            "model": VOICE_MODEL,
        },
        "runtime_seconds": round(duration(MASTER), 3),
        "timeline": timeline,
        "music": music_cues,
        "music_license": {
            "license": "Creative Commons Attribution 4.0 International",
            "creator": "Scott Buckley",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "library_use_url": (
                "https://www.scottbuckley.com.au/library/using-this-music/"
            ),
            "ready_to_paste_attribution": [
                (
                    "\"Intervention\" by Scott Buckley, licensed under "
                    "CC BY 4.0: "
                    "https://www.scottbuckley.com.au/library/intervention/ — "
                    "https://creativecommons.org/licenses/by/4.0/"
                ),
                (
                    "\"Red\" by Scott Buckley, licensed under CC BY 4.0: "
                    "https://www.scottbuckley.com.au/library/red/ — "
                    "https://creativecommons.org/licenses/by/4.0/"
                ),
            ],
        },
        "claim_safety": [
            "Crohn's redirection is explicitly framed as Jimmy's account.",
            "The narration rejects literal disease-caused-success framing.",
            "Programmed rest remains in the day-310 bite.",
            "The progress statement is Jimmy's subjective assessment.",
        ],
        "outputs": {
            "wav_48khz_24bit": str(MASTER.relative_to(ROOT)),
            "mp3_review_256kbps": str(REVIEW.relative_to(ROOT)),
        },
    }
    CUESHEET.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    prepared = prepare_segments()
    speech, starts = speech_master(prepared)
    scored, music_cues = mix_score(speech, prepared, starts)
    loudness_master(scored)
    write_cue_sheet(prepared, starts, music_cues)
    print(f"[OK] WAV: {MASTER}")
    print(f"[OK] MP3: {REVIEW}")
    print(f"[OK] Cue sheet: {CUESHEET}")
    print(f"[OK] Runtime: {duration(MASTER):.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
