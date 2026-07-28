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
                          concat_cmd, fit_run_durations, narration_texts,
                          probe_dur, run)

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


def silence_cmd(dur, dst):
    """Stand-in for the music bed: pure silence, same stereo/48k format
    as every fd_*.wav chunk, so the concat demuxer can stream-copy it in.
    """
    return ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(dur), "-c:a", "pcm_s16le", "-y", str(dst)]


def full_timeline_audio(edl, speech_chunks, work):
    """Splice silence into the speech-only chain at every card/beat gap.

    build_audio() (Task 8) deliberately drops cards and music-only beats
    from its speech concat - audio_chunk_order() skips them by design
    (see test_chunk_order_ignores_cards_and_beats). In the finished film
    their silent screen time is meant to be filled by the music bed, but
    the cue library is deferred to Phase 2 and ships schema-only here.
    Without a stand-in, the audio track is exactly
    sum(card/beat durations) shorter than the picture, which is why the
    sync gate refuses it - correctly. This is not a gate problem, it is
    a missing piece of THIS driver, so the fix goes here rather than in
    v11_assemble.py or edl.py.

    speech_chunks: the fd_*.wav files build_audio() already produced,
    sorted in chronological order (bites and narration runs, interleaved
    exactly as audio_chunk_order() emits them). Each already fades to
    true zero at its edges, so butt-joining silence against it introduces
    no click.
    """
    run_at = {i: k for k, (i, j) in enumerate(edl.runs())}
    in_run_tail = {k for i, j in edl.runs() for k in range(i + 1, j)}
    chunks = iter(speech_chunks)
    order = []
    for idx, s in enumerate(edl.segs):
        if idx in in_run_tail:
            continue  # non-first segment of a run - already in one chunk
        if idx in run_at or s.kind == "bite":
            order.append(next(chunks))
        else:  # card or beat - no speech, stand in silence for the music
            sil = work / f"sil_{idx:03d}.wav"
            run(silence_cmd(s.dur, sil))
            order.append(sil)
    listfile = work / "full_achain.txt"
    listfile.write_text(
        "\n".join(f"file '{p.absolute().as_posix()}'" for p in order),
        encoding="utf-8")
    out = work / "full_audio.wav"
    run(concat_cmd(order, listfile, out))
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

    speech = build_audio(edl, run_wavs, sources, WORK)
    print(f"[audio-speech] {probe_dur(speech):.2f}s "
          f"(bites + narration runs only)")

    # build_audio() skips cards/beats (their time is meant to come from
    # the music bed, deferred to Phase 2) - splice silence into those
    # gaps so the audio track spans the full timeline. See
    # full_timeline_audio()'s docstring for why this belongs here.
    fd_chunks = sorted(WORK.glob("fd_*.wav"))
    audio = full_timeline_audio(edl, fd_chunks, WORK)
    ad = probe_dur(audio)
    print(f"[audio-full] {ad:.2f}s (silence stands in for the music bed)")

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
