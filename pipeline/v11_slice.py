#!/usr/bin/env python3
"""v11_slice.py - prove the v11 audio EDL on ~3 minutes before betting a
30-minute film on it.

Generates a draft narration WAV with edge-tts (free - never spend paid
TTS credits on a proving run), builds the audio chain, renders a colour-
bar video track of the exact timeline length, muxes through the sync
gate, and QCs the result.

Run: py -3.12 pipeline/v11_slice.py
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edl import load_edl  # noqa: E402
from qc_v11 import report  # noqa: E402
from v11_assemble import (ROOT, build_audio, check_sync,  # noqa: E402
                          fit_run_durations, narration_texts, probe_dur,
                          run)

WORK = ROOT / "final_video" / "v11_work"
OUT = ROOT / "final_video" / "V11_SLICE.mp4"
DOSSIER = ROOT / "dossier" / "statham"


def draft_runs(texts):
    """One free edge-tts generation per narration RUN.

    AUDIO LAST: proving runs never spend paid TTS credits. Returns the
    generated wavs in run order.
    """
    out = []
    for k, text in enumerate(texts):
        mp3 = WORK / f"vo_run_{k:02d}.mp3"
        subprocess.run([sys.executable, "-m", "edge_tts", "--voice",
                        "en-US-ChristopherNeural", "--text", text,
                        "--write-media", str(mp3)], check=True)
        wav = mp3.with_suffix(".wav")
        run(["ffmpeg", "-i", str(mp3), "-ar", "48000", "-ac", "2",
             "-y", str(wav)])
        out.append(wav)
    return out


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    edl = load_edl(ROOT / "manifest" / "slice_cutlist.json")

    # narration durations in the cut list are PLACEHOLDERS - TTS decides
    # how long the copy actually takes, so generate first, then fit.
    run_wavs = draft_runs(narration_texts(edl))
    fit_run_durations(edl, [probe_dur(w) for w in run_wavs])
    total = edl.total()
    print(f"[edl] {total:.1f}s, {len(edl.segs)} segments, "
          f"{len(run_wavs)} narration runs")

    gated = report(edl)
    if not gated["passed"]:
        for p in gated["problems"]:
            print(f"  FAIL {p['code']}: {p['msg']}")
        raise SystemExit("cut list fails the format gates after fitting")

    sources = {s.source: DOSSIER / f"{s.source}.mp4"
               for s in edl.segs if s.kind == "bite"}
    for sid, p in sources.items():
        if not p.exists():
            raise SystemExit(f"missing source {sid}: {p}")

    # build_audio() now consumes timeline_audio_plan() internally, so the
    # returned track already spans the full EDL timeline - cards/beats
    # are filled with silence standing in for the not-yet-built music
    # bed, in their correct timeline position (not appended at the tail).
    audio = build_audio(edl, run_wavs, sources, WORK)
    ad = probe_dur(audio)
    print(f"[audio] {ad:.2f}s (full timeline: speech + silence)")

    vtrack = WORK / "slice_video.mp4"
    run(["ffmpeg", "-f", "lavfi",
         "-i", f"testsrc=size=1920x1080:rate=30:duration={total}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-an", "-y", str(vtrack)])
    vd = probe_dur(vtrack)

    check_sync(vd, ad)
    print(f"[sync] video={vd:.2f}s audio={ad:.2f}s "
          f"drift={vd - ad:+.2f}s OK")

    run(["ffmpeg", "-i", str(vtrack), "-i", str(audio),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-y", str(OUT)])

    post = report(edl, probe_dur(OUT))
    print(f"[qc] passed={post['passed']} problems={post['problems']}")
    if not post["passed"]:
        return 1
    print(f"[OK] {OUT} ({probe_dur(OUT):.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
