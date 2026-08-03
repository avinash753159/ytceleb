#!/usr/bin/env python3
"""Build the measured V11 MrBeast radio edit from the three-column script.

This is an audio-first production driver. It parses the markdown master,
resolves BITE ids through manifest/mrbeast_soundbites.json, generates free
draft narration one contiguous run at a time, fits the EDL to measured TTS,
enforces the V11 gates, and produces a reviewable radio MP4.

No paid TTS and no picture edit are used here.
"""
import html
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edl import build_edl  # noqa: E402
from qc_v11 import report  # noqa: E402
from v11_assemble import (ROOT, build_audio, check_sync, fit_run_durations,
                          narration_texts, probe_dur, run)  # noqa: E402

VERSION = os.environ.get("MRBEAST_SCRIPT_VERSION", "V1").upper()
VOICE_MODE = os.environ.get("MRBEAST_VOICE_MODE", "draft").lower()
FINAL_TAG = "_final" if VOICE_MODE == "final" else ""
SCRIPT = ROOT / "dossier" / "mrbeast" / f"THREE_COLUMN_SCRIPT_{VERSION}.md"
BANK = ROOT / "manifest" / "mrbeast_soundbites.json"
CUTLIST = ROOT / "manifest" / f"mrbeast_radio_cutlist_{VERSION.lower()}{FINAL_TAG}.json"
WORK = ROOT / "final_video" / f"mrbeast_radio_{VERSION.lower()}{FINAL_TAG}"
RADIO_WAV = ROOT / "final_video" / f"MRBEAST_RADIO_{VERSION}{FINAL_TAG.upper()}.wav"
OUT = ROOT / "final_video" / f"MRBEAST_RADIO_{VERSION}{FINAL_TAG.upper()}.mp4"
SOURCES = ROOT / "dossier" / "mrbeast" / "sources"

CHAPTERS = {
    "Cold open": "open",
    "The contract he could not edit": "open",
    "The kid who was disappearing": "origin",
    "The body he lost": "origin",
    # V5 gives the disease its own act instead of folding it into the origin.
    "What it actually feels like": "illness",
    "The machine": "machine",
    "Two systems": "machine",
    "The contract": "contract",
    "The real protocol": "protocol",
    "The verified protocol": "protocol",
    "The challenge on camera": "contract",
    "When the fantasy failed": "limit",
    "The limit of control": "limit",
    # V4 splits the reversal out of "limit" so the fall gets its own
    # musical act instead of sharing the doubt cue.
    "Something had to give": "fall",
    "Reclaiming the body": "resolution",
}
FITNESS_CHAPTERS = {"contract", "protocol", "limit", "fall", "resolution"}
ROW_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
BITE_RE = re.compile(r"BITE[^`]*`([a-z0-9_]+)`")
NARR_RE = re.compile(r"\*\*NARR:\*\*\s*(.*)")


def plain(s):
    s = html.unescape(s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]*)\*", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_script():
    bank = {r["id"]: r for r in json.loads(BANK.read_text(encoding="utf-8"))}
    segs, chapter, n = [], None, 0
    beat_count = 0
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            chapter = next((slug for title, slug in CHAPTERS.items()
                            if title.lower() in line.lower()), chapter)
            continue
        m = ROW_RE.match(line)
        if not m or not chapter:
            continue
        picture, speech, _sound = m.groups()
        if speech.strip() in {"Speech", "---"}:
            continue

        # Count authored breathing markers even when the row carries a
        # narration or verified bite direction. Rows with a real silent dash
        # still become timeline beat events below; mixed direction rows remain
        # speech-bearing so the beat marker does not create an unintended
        # extra pause.
        authored_beat = "BEAT" in picture.upper()
        if authored_beat:
            beat_count += 1

        bm = BITE_RE.search(speech)
        nm = NARR_RE.search(speech)
        fitness = chapter in FITNESS_CHAPTERS
        if bm:
            bid = bm.group(1)
            if bid not in bank:
                raise KeyError(f"script references missing bite {bid}")
            b = bank[bid]
            segs.append({
                "id": f"b{n:03d}_{bid}",
                "kind": "bite",
                "dur": b["duration"],
                "chapter": chapter,
                "source": b["source_id"],
                "t0": b["t0"],
                "speaker": b["speaker"],
                "jcut": 0.4,
                "fitness": fitness or "gym" in picture.lower()
            })
            n += 1
        elif nm:
            text = plain(nm.group(1))
            words = len(text.split())
            segs.append({
                "id": f"n{n:03d}",
                "kind": "narr",
                "dur": max(words / 150 * 60, 1.0),
                "chapter": chapter,
                "text": text,
                "fitness": fitness,
            })
            n += 1
            # V11 cards are silent timeline events. The picture direction can
            # still remain on the card through the following narration, while
            # this short event gives the protocol an intentional read beat.
            if chapter == "protocol" and "Card:" in picture:
                segs.append({
                    "id": f"c{n:03d}",
                    "kind": "card",
                    "dur": 1.2,
                    "chapter": chapter,
                    "source": "MrBeastProtocolCard",
                    "fitness": True,
                })
                n += 1
        elif "BEAT" in picture.upper():
            segs.append({
                "id": f"s{n:03d}",
                "kind": "beat",
                "dur": 3.2,
                "chapter": chapter,
                "fitness": fitness,
            })
            n += 1

    # Guarantee the six-event breathing-room requirement without pretending
    # those events exist: fail the parser if the authored script lacks them.
    if beat_count < 6:
        raise ValueError(f"script has only {beat_count} authored BEAT rows")
    segs[0]["promise"] = "what_the_transformation_reclaimed"
    segs[-1]["resolves"] = "what_the_transformation_reclaimed"
    return {
        "protocol_chapter": "protocol",
        "subject_speaker": "subject",
        "segments": segs,
    }


def draft_runs(texts):
    out = []
    for k, text in enumerate(texts):
        mp3 = WORK / f"vo_run_{k:02d}.mp3"
        wav = WORK / f"vo_run_{k:02d}.wav"
        stamp = WORK / f"vo_run_{k:02d}.sha256"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # A cancelled edge-tts process can leave a non-empty but truncated
        # cache entry. Reject any cached run too short to plausibly contain its
        # word count (5.5 words/s is deliberately generous).
        min_plausible = max(len(text.split()) / 5.5, 1.0)
        cache_bad = (not mp3.exists() or mp3.stat().st_size == 0 or
                     not stamp.exists() or
                     stamp.read_text(encoding="ascii").strip() != digest or
                     (wav.exists() and probe_dur(wav) < min_plausible))
        if cache_bad:
            mp3.unlink(missing_ok=True)
            wav.unlink(missing_ok=True)
            stamp.unlink(missing_ok=True)
            if VOICE_MODE == "final":
                import requests
                key = (ROOT / "elevenlabs_key.txt").read_text(encoding="utf-8").strip()
                response = requests.post(
                    "https://api.elevenlabs.io/v1/text-to-speech/nPczCjzI2devNBz1zQrb",
                    headers={"xi-api-key": key, "Content-Type": "application/json"},
                    json={
                        "text": text,
                        "model_id": "eleven_turbo_v2_5",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.0,
                            "use_speaker_boost": True,
                        },
                    },
                    timeout=180,
                )
                response.raise_for_status()
                mp3.write_bytes(response.content)
            else:
                subprocess.run([
                    sys.executable, "-m", "edge_tts",
                    "--voice", "en-US-ChristopherNeural",
                    "--text", text, "--write-media", str(mp3)
                ], check=True)
            stamp.write_text(digest, encoding="ascii")
        if not wav.exists():
            run(["ffmpeg", "-i", str(mp3), "-ar", "48000", "-ac", "2",
                 "-y", str(wav)])
        out.append(wav)
    return out


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    doc = parse_script()
    CUTLIST.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    edl = build_edl(doc)

    runs = draft_runs(narration_texts(edl))
    fit_run_durations(edl, [probe_dur(p) for p in runs])
    # Persist the measured timeline, not the pre-TTS word-count estimates.
    # External QC and the later picture build both consume this cut list; if
    # placeholder narration durations remain here they report a false runtime
    # and cannot perform a meaningful V7 render-sync check.
    for raw, measured in zip(doc["segments"], edl.segs):
        raw["dur"] = measured.dur
    doc["fitted"] = True
    CUTLIST.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    total = edl.total()

    gated = report(edl)
    print(f"[edl] {total:.2f}s, {len(edl.segs)} segments, "
          f"{len(runs)} narration runs")
    print(f"[qc] passed={gated['passed']}")
    for p in gated["problems"]:
        print(f"  FAIL {p['code']}: {p['msg']}")
    if not gated["passed"]:
        return 1

    source_paths = {s.source: SOURCES / f"{s.source}.mp4"
                    for s in edl.segs if s.kind == "bite"}
    missing = [str(p) for p in source_paths.values() if not p.exists()]
    if missing:
        raise SystemExit("missing source video(s):\n" + "\n".join(missing))

    audio = build_audio(edl, runs, source_paths, WORK)
    # Two-pass linear normalization. Single-pass loudnorm measured -13.3 LUFS
    # / -0.6 dBTP on the first radio build, outside the delivery target.
    measured = subprocess.run(
        ["ffmpeg", "-i", str(audio), "-af",
        "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json",
         "-f", "null", "-"], capture_output=True, text=True,
        timeout=3600, check=True)
    stats = json.loads(measured.stderr[measured.stderr.rfind("{"):
                                       measured.stderr.rfind("}") + 1])
    # Leave headroom for the final AAC encode, which can add ~0.6 dB of
    # inter-sample peak versus the normalized PCM master.
    af = ("loudnorm=I=-14:TP=-2.0:LRA=11:linear=true"
          f":measured_I={stats['input_i']}"
          f":measured_TP={stats['input_tp']}"
          f":measured_LRA={stats['input_lra']}"
          f":measured_thresh={stats['input_thresh']}"
          f":offset={stats['target_offset']}")
    run(["ffmpeg", "-i", str(audio), "-af", af,
         "-ar", "48000", "-ac", "2", "-y", str(RADIO_WAV)])
    ad = probe_dur(RADIO_WAV)

    # A simple radio-review picture, deliberately not a visual rough cut.
    vtrack = WORK / "review_picture.mp4"
    run(["ffmpeg", "-f", "lavfi", "-i",
         f"color=c=0x101010:s=1920x1080:r=30:d={ad}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-an", "-y", str(vtrack)])
    vd = probe_dur(vtrack)
    check_sync(vd, ad)
    run(["ffmpeg", "-i", str(vtrack), "-i", str(RADIO_WAV),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-y", str(OUT)])
    print(f"[OK] {OUT} ({probe_dur(OUT):.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
