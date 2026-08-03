#!/usr/bin/env python3
"""Build the V4 story-led radio master with real sound design.

What changed from V3, all of it from operator feedback:

  1. MUSIC FROM 0:00. V3's first cue began at 58.2s and the cold-open chapter
     had no cue entry at all. Every act now has a cue and the film opens
     scored.
  2. ATMOSPHERE LEAD-IN. Sound establishes before anyone speaks, instead of
     narration starting cold on frame one.
  3. PRE-LAP AT ACT TURNS. The next act's music enters before its first word,
     so chapters flow instead of butting together.
  4. ROOM TONE UNDER EVERYTHING. No digital-black silence between segments.
  5. SIDECHAIN DUCKING. Dialogue always sits above the bed automatically
     rather than by fixed level automation.

Audio only. No picture is built or authorised here.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = os.environ.get("MRBEAST_SCRIPT_VERSION", "V4").upper()
os.environ["MRBEAST_SCRIPT_VERSION"] = VERSION
os.environ.setdefault("MRBEAST_VOICE_MODE", "final")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mrbeast_radio as radio  # noqa: E402
from edl import build_edl  # noqa: E402
from v11_assemble import build_audio, fit_run_durations, probe_dur, run  # noqa: E402

MUSIC = ROOT / "dossier" / "mrbeast" / "audio_v3" / "music"
OUTDIR = ROOT / "final_video" / f"mrbeast_audio_{VERSION.lower()}"
WORK = OUTDIR / "work"
MASTER = OUTDIR / f"MRBEAST_{VERSION}_STORY_MASTER.wav"
REVIEW = OUTDIR / f"MRBEAST_{VERSION}_STORY_MASTER.mp3"
CUESHEET = OUTDIR / f"MRBEAST_{VERSION}_CUE_SHEET.json"

# Sound-design constants.
#
# Measured off the reference documentary the operator supplied
# (youtu.be/IbWl40xgw0A, 39.5 min) via pipeline/ref_open.py:
#   - audio present at -19.7 dBFS from 0.00s; first narrated word at 1.24s
#   - hook runs 0-17s, then a 31-SECOND MUSIC-ONLY TITLE BREAK before the
#     story proper begins at 48.3s
#   - cutting is slow and accelerates: median shot 5.15s / 5.25s / 2.92s
#     across thirds
LEAD_IN = 2.0        # atmosphere before the first narrated word
# The break was 12s sitting at the end of the cold open. That was a scaling
# error: 31s works in a 39-minute film, but 12s inside a 12-minute one is a
# hole in the opening with nothing to show. It is now short, and placed as
# the pause BEFORE the diagnosis lands - where a silence carries weight.
TITLE_BREAK = 4.0
BREAK_BEFORE = "The diagnosis had a name"   # narration the break precedes
PRE_LAP = 1.8        # next act's cue enters this early
CUE_FADE = 2.4       # cue fade-in
TAIL = 2.5           # air after the last word

# One cue per act. Volumes are pre-duck; the sidechain does the rest.
#
# Source offsets are NOT arbitrary. Measured head levels (2s blocks):
#   intervention_nomelody  0-2s = -93.9 dB  (digital silence; full at 18s)
#   descent                0-2s = -45.1 dB  (full at 4s)
#   celestial              0-2s = -41.9 dB  (full at 2s)
#   red_no_vocals          0-2s = -35.4 dB  (full at 2s)
#   chasing_daylight       0-2s = -22.0 dB  (usable from 0s)
# Starting a cue on a track's own silent intro is what made V4's first build
# open at -64.8 dB - the exact "no music at the start" defect being fixed.
CUES = {
    "open":       ("intervention_nomelody.mp3",  18.0, 0.30),
    "origin":     ("descent.mp3",                12.0, 0.26),
    # V5: the illness act is the emotional floor. Sparsest cue in the film -
    # the testimony carries it, the score stays out of the way.
    "illness":    ("descent.mp3",                62.0, 0.16),
    "machine":    ("red_no_vocals.mp3",          35.0, 0.24),
    "contract":   ("red_no_vocals.mp3",          96.0, 0.30),
    "protocol":   ("celestial.mp3",               8.0, 0.26),
    "limit":      ("descent.mp3",                 4.0, 0.22),
    "fall":       ("intervention_nomelody.mp3",  74.0, 0.24),
    "resolution": ("chasing_daylight.mp3",       10.0, 0.30),
}

ATTRIBUTION = {
    "intervention_nomelody.mp3":
        '"Intervention" by Scott Buckley, CC BY 4.0: '
        'https://www.scottbuckley.com.au/library/intervention/',
    "descent.mp3":
        '"Descent" by Scott Buckley, CC BY 4.0: '
        'https://www.scottbuckley.com.au/library/descent/',
    "red_no_vocals.mp3":
        '"Red" by Scott Buckley, CC BY 4.0: '
        'https://www.scottbuckley.com.au/library/red/',
    "celestial.mp3":
        '"Celestial" by Scott Buckley, CC BY 4.0: '
        'https://www.scottbuckley.com.au/library/celestial/',
    "chasing_daylight.mp3":
        '"Chasing Daylight" by Scott Buckley, CC BY 4.0: '
        'https://www.scottbuckley.com.au/library/chasing-daylight/',
}


def chapter_spans(edl):
    """First and last program time of each act, in running order."""
    offs = edl.offsets()
    spans, order = {}, []
    for i, seg in enumerate(edl.segs):
        c = seg.chapter
        a, b = offs[i], offs[i] + seg.dur
        if c not in spans:
            spans[c] = [a, b]
            order.append(c)
        else:
            spans[c][1] = b
    return [(c, spans[c][0], spans[c][1]) for c in order]


def insert_title_break(speech: Path, dest: Path, at: float,
                       gap: float) -> Path:
    """Open a music-only hole in the speech track after the cold open.

    The reference documentary holds 31 seconds of picture and score with no
    narration between its hook and its first chapter. That break is what
    makes the hook feel like a hook instead of the first paragraph of an
    essay. This cuts the equivalent hole; the score fills it.
    """
    a = WORK / "tb_a.wav"
    b = WORK / "tb_b.wav"
    sil = WORK / "tb_gap.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(speech), "-t", f"{at:.4f}",
         "-c:a", "pcm_s24le", str(a)], timeout=1800)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{at:.4f}", "-i", str(speech),
         "-c:a", "pcm_s24le", str(b)], timeout=1800)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", f"{gap:.4f}", "-c:a", "pcm_s24le", str(sil)], timeout=600)
    lst = WORK / "tb_concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in (a, sil, b)), encoding="utf-8")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:a", "pcm_s24le", str(dest)], timeout=1800)
    for p in (a, b, sil, lst):
        p.unlink(missing_ok=True)
    return dest


def delay_speech(speech: Path, dest: Path, lead: float) -> Path:
    """Push the whole speech timeline back so atmosphere can establish."""
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(speech), "-af",
         f"adelay={int(lead * 1000)}:all=1,"
         f"apad=pad_dur={TAIL},"
         f"aformat=sample_rates=48000:channel_layouts=stereo",
         "-c:a", "pcm_s24le", str(dest)], timeout=1800)
    return dest


def score(speech: Path, spans, lead: float):
    """Lay one cue per act over the delayed speech track, with pre-lap and
    crossfades, then duck the whole music bus under dialogue."""
    total = probe_dur(speech)
    inputs = ["-i", str(speech)]
    filters = ["[0:a]aformat=sample_rates=48000:channel_layouts=stereo"
               "[dialogue]"]
    labels, rows = [], []

    for k, (chapter, a, b) in enumerate(spans):
        spec = CUES.get(chapter)
        if not spec:
            continue
        fname, src_off, vol = spec
        track = MUSIC / fname
        if not track.exists():
            raise FileNotFoundError(track)

        # Act 1 starts at 0 so the film opens scored; later acts pre-lap.
        at = 0.0 if k == 0 else max(0.0, a + lead - PRE_LAP)
        end = min(total, b + lead + (0.0 if k == len(spans) - 1 else PRE_LAP))
        dur = max(0.5, end - at)

        # A cue must never run off the end of its track - atrim past EOF
        # yields a short stream and the act finishes in silence. Loop the
        # track when the act outlasts it, and pull the offset back when the
        # requested window would overrun.
        track_len = probe_dur(track)
        loops = 0
        if dur >= track_len - 1.0:
            loops = int(dur // max(1.0, track_len)) + 1
            src_off = 0.0
        elif src_off + dur > track_len:
            src_off = max(0.0, track_len - dur - 0.5)

        inputs += (["-stream_loop", str(loops)] if loops else []) \
            + ["-i", str(track)]
        lab = f"m{k}"
        # Opening cue blooms fast: it now starts on real content, so a long
        # fade would just recreate the silent-open defect.
        fade_in = CUE_FADE if k else 1.6
        filters.append(
            f"[{len(labels) + 1}:a]"
            f"atrim=start={src_off}:end={src_off + dur:.4f},"
            f"asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={fade_in:.2f},"
            f"afade=t=out:st={max(0.0, dur - 2.0):.4f}:d=2.0,"
            f"volume={vol},"
            f"aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={int(at * 1000)}:all=1[{lab}]"
        )
        labels.append(f"[{lab}]")
        rows.append({
            "act": chapter, "track": fname,
            "program_t0": round(at, 3), "program_t1": round(at + dur, 3),
            "source_offset": src_off, "pre_duck_volume": vol,
        })

    if not labels:
        raise RuntimeError("no music cues resolved - check CUES vs chapters")

    # Low room tone so silences are never digitally black.
    inputs += ["-f", "lavfi", "-i",
               f"anoisesrc=color=brown:amplitude=0.0022:d={total:.3f}"]
    filters.append(
        f"[{len(labels) + 1}:a]"
        f"aformat=sample_rates=48000:channel_layouts=stereo,"
        f"volume=0.5[room]"
    )

    filters.append("".join(labels)
                   + f"amix=inputs={len(labels)}:duration=longest:"
                     f"normalize=0[music_raw]")
    filters.append("[music_raw][room]amix=inputs=2:duration=longest:"
                   "normalize=0[bed]")
    filters.append("[bed][dialogue]sidechaincompress="
                   "threshold=0.028:ratio=7:attack=8:release=340[ducked]")
    filters.append("[dialogue][ducked]amix=inputs=2:duration=longest:"
                   "normalize=0,"
                   "alimiter=limit=0.92:attack=5:release=90[mixed]")

    dest = WORK / "v4_scored.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
         "-filter_complex", ";".join(filters), "-map", "[mixed]",
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(dest)],
        timeout=3600)
    return dest, rows


def loudnorm(src: Path):
    first = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
         "loudnorm=I=-14:TP=-1.5:LRA=10:print_format=json", "-f", "null",
         "NUL"], capture_output=True, text=True, timeout=3600, check=True)
    m = re.search(r"\{\s*\"input_i\".*?\}", first.stderr, re.S)
    if not m:
        raise RuntimeError("loudnorm first pass unparseable")
    s = json.loads(m.group(0))
    filt = ("loudnorm=I=-14:TP=-1.5:LRA=10:linear=true"
            f":measured_I={s['input_i']}:measured_TP={s['input_tp']}"
            f":measured_LRA={s['input_lra']}:measured_thresh="
            f"{s['input_thresh']}:offset={s['target_offset']}")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-af", filt, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le",
         str(MASTER)], timeout=3600)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(MASTER), "-c:a", "libmp3lame", "-b:a", "256k",
         "-ar", "48000", str(REVIEW)], timeout=1800)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    # radio.draft_runs writes its TTS cache here and does not create the
    # directory itself - without this the first ElevenLabs response is
    # fetched (spending credits) and then dropped on the floor.
    radio.WORK.mkdir(parents=True, exist_ok=True)

    doc = radio.parse_script()
    edl = build_edl(doc)
    texts = radio.narration_texts(edl)
    runs = radio.draft_runs(texts)
    fit_run_durations(edl, [probe_dur(p) for p in runs])

    sources = {s.source: radio.SOURCES / f"{s.source}.mp4"
               for s in edl.segs if s.kind == "bite"}
    missing = [str(p) for p in sources.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("missing sources:\n" + "\n".join(missing))

    speech = build_audio(edl, runs, sources, WORK)

    # Find where the break belongs: immediately before the diagnosis line.
    offs = edl.offsets()
    ins_at = None
    for i, seg in enumerate(edl.segs):
        if seg.kind == "narr" and BREAK_BEFORE.lower() in (
                getattr(seg, "text", "") or "").lower():
            ins_at = offs[i]
            break
    if ins_at is None:                      # fall back to end of cold open
        ins_at = chapter_spans(edl)[0][2]
        print("[warn] break anchor not found; using end of cold open")
    print(f"[break] {TITLE_BREAK}s of music before "
          f"'{BREAK_BEFORE}' at {ins_at + LEAD_IN:.2f}s", flush=True)

    broken = insert_title_break(speech, WORK / "v4_speech_break.wav",
                                ins_at, TITLE_BREAK)
    delayed = delay_speech(broken, WORK / "v4_speech_delayed.wav", LEAD_IN)

    # Shift only what falls after the insertion point. The act containing
    # the break keeps its start and gains the break in its length.
    spans = [(c,
              a + (TITLE_BREAK if a >= ins_at - 1e-6 else 0.0),
              b + (TITLE_BREAK if b > ins_at + 1e-6 else 0.0))
             for c, a, b in chapter_spans(edl)]
    scored, cue_rows = score(delayed, spans, LEAD_IN)
    loudnorm(scored)

    narr_s = sum(s.dur for s in edl.segs if s.kind == "narr")
    bite_s = sum(s.dur for s in edl.segs if s.kind == "bite")
    total = probe_dur(MASTER)
    payload = {
        "status": "v4_story_cut_for_user_approval_not_audio_lock",
        "runtime_seconds": round(total, 3),
        "lead_in_seconds": LEAD_IN,
        "title_break_seconds": TITLE_BREAK,
        "sound_design_reference": {
            "source": "https://youtu.be/IbWl40xgw0A",
            "measured_by": "pipeline/ref_open.py",
            "audio_from": "0.00s at -19.7 dBFS",
            "first_word": "1.24s",
            "music_only_title_break": "17.2s-48.3s (31s)",
            "median_shot": "5.15s / 5.25s / 2.92s across thirds",
        },
        "narration_seconds": round(narr_s, 3),
        "verified_bite_seconds": round(bite_s, 3),
        "narration_share": round(narr_s / edl.total(), 4),
        "segments": len(edl.segs),
        "narration_runs": len(runs),
        "acts": [{"act": c, "t0": round(a + LEAD_IN, 2),
                  "t1": round(b + LEAD_IN, 2)} for c, a, b in spans],
        "music": cue_rows,
        "music_license": {
            "license": "Creative Commons Attribution 4.0 International",
            "creator": "Scott Buckley",
            "attribution": sorted({ATTRIBUTION[r["track"]]
                                   for r in cue_rows
                                   if r["track"] in ATTRIBUTION}),
        },
        "outputs": {"wav": str(MASTER.relative_to(ROOT)),
                    "mp3": str(REVIEW.relative_to(ROOT))},
    }
    CUESHEET.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[OK] {MASTER}")
    print(f"[OK] {REVIEW}")
    print(f"[OK] {total / 60:.2f} min | narration {narr_s / edl.total():.1%} "
          f"| bites {bite_s:.0f}s | lead-in {LEAD_IN}s")
    for c, a, b in spans:
        print(f"     act {c:11} {a + LEAD_IN:7.1f} - {b + LEAD_IN:7.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
