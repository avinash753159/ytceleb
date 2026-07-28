#!/usr/bin/env python3
"""v11_assemble.py - audio EDL assembly for the V11 documentary format.

WHY v10 DOES NOT WORK HERE
v10 assumed "one continuous narration river with 6-8 islands crossfaded
in". The V11 format interleaves 60+ archival bites with ~30 narration
runs, which is a different shape. v11 builds a real audio EDL: explicit
offsets, one encode, one loudnorm.

WHAT CARRIES OVER UNCHANGED (F7 - four bugs, never regress)
  1. amix renormalises when a short input ends -> clipping. normalize=0.
  2. mono SFX + stereo VO in amix -> narration comes back +3dB hot.
     aformat everything to stereo BEFORE mixing.
  3. NEVER slice narration per beat - per-beat AAC re-encode puts an
     audible glitch at every join. Slice per RUN.
  4. NEVER acrossfade - each crossfade OVERLAPS its inputs, shortening
     total audio ~0.3s per junction -> cumulative A/V drift. Butt-join
     with 30ms edge fades + the concat demuxer.
Plus the hard sync gate: refuse to mux past 0.25s drift.

Commands are BUILT AS DATA and executed separately so the rules above are
unit-testable. See tests/test_v11_audio_cmds.py.
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent

SYNC_TOLERANCE = 0.25
EDGE_FADE = 0.03
MUSIC_VOL = 0.16


class SyncError(Exception):
    pass


def narration_texts(edl):
    """TTS input, one string per contiguous narration RUN.

    NOT sliced from a master. In V11 bites occupy film time but no VO
    time, so a film-timeline offset does not address the right sample of
    a VO master - the v10 atrim approach is simply wrong here. One
    generation per run also means there is no slicing to glitch (F7.3).
    """
    return [" ".join(edl.segs[k].text for k in range(i, j)).strip()
            for i, j in edl.runs()]


def fit_run_durations(edl, run_durs):
    """Overwrite narration durations with what TTS actually produced.

    A run's measured duration is split across its segments in proportion
    to text length, so chapter and fitness tagging inside a run survives.
    """
    runs = edl.runs()
    if len(run_durs) != len(runs):
        raise ValueError(f"got {len(run_durs)} durations for "
                         f"{len(runs)} runs")
    for (i, j), total in zip(runs, run_durs):
        weights = [max(len(edl.segs[k].text), 1) for k in range(i, j)]
        wsum = sum(weights)
        acc = 0.0
        for n, k in enumerate(range(i, j)):
            if n == j - i - 1:
                edl.segs[k].dur = round(total - acc, 6)
            else:
                d = round(total * weights[n] / wsum, 6)
                edl.segs[k].dur = d
                acc += d


def norm_cmds(paths, workdir, prefix):
    """Normalise generated wavs to 48kHz stereo."""
    out = []
    for k, p in enumerate(paths):
        dst = Path(workdir) / f"{prefix}_{k:02d}.wav"
        out.append(([
            "ffmpeg", "-i", str(p), "-ar", "48000", "-ac", "2",
            "-y", str(dst)], dst))
    return out


def bite_cmds(edl, source_paths, workdir):
    """Extract each archival bite's audio from its source window."""
    out = []
    for s in edl.segs:
        if s.kind != "bite":
            continue
        if s.source not in source_paths:
            raise KeyError(f"{s.seg_id}: no path for source {s.source!r}")
        dst = Path(workdir) / f"bite_{s.seg_id}.wav"
        out.append(([
            "ffmpeg", "-ss", str(s.t0), "-t", str(s.dur),
            "-i", str(source_paths[s.source]), "-vn",
            "-ar", "48000", "-ac", "2", "-y", str(dst)], dst))
    return out


def fade_cmds(chunks, workdir):
    """30ms edge fades + stereo/48k normalisation. NEVER acrossfade.

    Takes (path, duration) pairs: a fade-OUT needs the duration to know
    where to start. Probing inside here would make the builder untestable,
    so the driver probes and passes it in.
    """
    out = []
    for k, (ch, dur) in enumerate(chunks):
        st = max(dur - EDGE_FADE, 0.0)
        dst = Path(workdir) / f"fd_{k:03d}.wav"
        out.append(([
            "ffmpeg", "-i", str(ch), "-af",
            f"afade=t=in:d={EDGE_FADE},"
            f"afade=t=out:st={st:.3f}:d={EDGE_FADE},"
            "aformat=channel_layouts=stereo:sample_rates=48000",
            "-y", str(dst)], dst))
    return out


def concat_cmd(faded, listfile, out):
    """Butt-join via the concat demuxer - no overlap, no drift."""
    return ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(listfile),
            "-c", "copy", "-y", str(out)]


def music_mix_cmd(base, plan, cue_dir, out):
    """Overlay scored cues onto the speech track at chapter offsets.

    The base speech track is aformat-ed to stereo/48k same as every cue -
    rule 2 ("every amix input is aformat-ed to stereo BEFORE mixing")
    must hold inside this function, not rely on an upstream invariant.
    """
    ins = ["-i", str(base)]
    parts = ["[0:a]aformat=channel_layouts=stereo:sample_rates=48000[base]"]
    mix = "[base]"
    for k, p in enumerate(plan):
        ins += ["-i", str(Path(cue_dir) / p["cue"])]
        ms = int(round(p["at"] * 1000))
        parts.append(
            f"[{k + 1}:a]atrim=0:{p['dur']},volume={MUSIC_VOL},"
            f"aformat=channel_layouts=stereo:sample_rates=48000,"
            f"adelay={ms}|{ms}[m{k}]")
        mix += f"[m{k}]"
    fc = ";".join(parts) + \
        f";{mix}amix=inputs={len(plan) + 1}:duration=first:normalize=0[a]"
    return ["ffmpeg", *ins, "-filter_complex", fc, "-map", "[a]",
            "-y", str(out)]


def check_sync(video_dur, audio_dur):
    drift = video_dur - audio_dur
    if abs(drift) > SYNC_TOLERANCE:
        raise SyncError(f"A/V DRIFT {drift:+.2f}s exceeds "
                        f"{SYNC_TOLERANCE}s - refusing to ship")


def run(cmd, timeout=3600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(" ".join(map(str, cmd))[:200] + "\n"
                           + (r.stderr or "")[-400:])
    return r


def probe_dur(f):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(f)], capture_output=True,
        text=True).stdout.strip())
