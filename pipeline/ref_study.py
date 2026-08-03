#!/usr/bin/env python3
"""Measure a reference video's storytelling, pacing and sound design.

Answers concrete questions instead of impressions:
  - how long does atmosphere run BEFORE the first narrated word?
  - what is the loudness envelope of the opening minute?
  - how fast does it cut, and does cutting speed change by act?
  - how much of the runtime is speech vs deliberate silence?
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def run(args, timeout=1800):
    r = subprocess.run([str(a) for a in args], capture_output=True,
                       text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError((r.stderr or "")[-1500:])
    return r


def pcm(path, t0=0.0, dur=None, sr=8000):
    """Mono float32 samples via ffmpeg."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
           "-ss", f"{t0:.3f}", "-i", str(path)]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=1800)
    return np.frombuffer(r.stdout, dtype=np.float32), sr


def envelope(x, sr, win=0.25):
    n = max(1, int(sr * win))
    trim = len(x) - (len(x) % n)
    if trim <= 0:
        return np.array([]), win
    f = x[:trim].reshape(-1, n)
    rms = np.sqrt((f ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12), win


def transcribe(path, t0, dur):
    from faster_whisper import WhisperModel
    tmp = ROOT / "work" / "ref_study" / "_head.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(path),
         "-vn", "-ac", "1", "-ar", "16000", str(tmp)])
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(tmp), vad_filter=False, word_timestamps=True)
    out = []
    for s in segs:
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": [(w.word, w.start) for w in (s.words or [])]})
    tmp.unlink(missing_ok=True)
    return out


def scenes(path):
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector
    v = open_video(str(path))
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=27.0))
    sm.detect_scenes(v, show_progress=False)
    return [(a.get_seconds(), b.get_seconds()) for a, b in sm.get_scene_list()]


def main() -> int:
    vid = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        ROOT / "work/ref_study/IbWl40xgw0A.mp4"
    info = vid.with_suffix(".info.json")
    meta = json.loads(info.read_text(encoding="utf-8")) if info.exists() else {}

    print("=" * 72)
    print(f"TITLE     {meta.get('title')}")
    print(f"CHANNEL   {meta.get('uploader')}")
    print(f"UPLOADED  {meta.get('upload_date')}   "
          f"VIEWS {meta.get('view_count')}")
    dur = float(meta.get("duration") or 0)
    print(f"DURATION  {dur / 60:.1f} min")

    # ---- opening sound design -----------------------------------------
    print("\n--- OPENING 60s SOUND DESIGN ---")
    x, sr = pcm(vid, 0, 60)
    env, win = envelope(x, sr)
    floor = float(np.percentile(env, 5))
    audible = np.where(env > floor + 12)[0]
    audio_start = audible[0] * win if len(audible) else None

    head = transcribe(vid, 0, 60)
    speech_start = None
    for s in head:
        if s["words"]:
            speech_start = s["words"][0][1]
            break
        if s["text"]:
            speech_start = s["start"]
            break

    print(f"first audible audio : {audio_start:.2f}s"
          if audio_start is not None else "first audible audio : n/a")
    print(f"first narrated word : {speech_start:.2f}s"
          if speech_start is not None else "first narrated word : n/a")
    if audio_start is not None and speech_start is not None:
        print(f"ATMOSPHERE LEAD-IN  : {speech_start - audio_start:.2f}s "
              f"of sound before anyone speaks")

    print("\nloudness by second (dBFS, first 30s):")
    per_s = [float(env[i * 4:(i + 1) * 4].mean())
             for i in range(min(30, len(env) // 4))]
    for i in range(0, len(per_s), 10):
        row = per_s[i:i + 10]
        print(f"  {i:2d}-{i + len(row) - 1:2d}s  " +
              " ".join(f"{v:6.1f}" for v in row))

    print("\nopening narration:")
    for s in head[:8]:
        print(f"  [{s['start']:6.2f}] {s['text'][:96]}")

    # ---- cutting pace --------------------------------------------------
    print("\n--- CUTTING PACE ---")
    try:
        sc = scenes(vid)
        lens = np.array([b - a for a, b in sc])
        print(f"shots detected      : {len(sc)}")
        print(f"mean shot length    : {lens.mean():.2f}s")
        print(f"median shot length  : {np.median(lens):.2f}s")
        print(f"shots under 2s      : {(lens < 2).mean():.0%}")
        print(f"shots over 6s       : {(lens > 6).mean():.0%}")
        if dur:
            thirds = [[], [], []]
            for (a, _b), L in zip(sc, lens):
                thirds[min(2, int(a / dur * 3))].append(L)
            for i, t in enumerate(thirds):
                if t:
                    print(f"  act {i + 1} mean shot : {np.mean(t):.2f}s "
                          f"({len(t)} shots)")
    except Exception as e:  # noqa: BLE001
        print(f"scene detection failed: {e}")

    # ---- speech vs silence across the whole film ----------------------
    print("\n--- SPEECH DENSITY (whole film) ---")
    xf, srf = pcm(vid, 0, dur or None)
    envf, winf = envelope(xf, srf, win=0.5)
    if len(envf):
        fl = float(np.percentile(envf, 5))
        quiet = (envf < fl + 8).mean()
        loud = (envf > np.percentile(envf, 60)).mean()
        print(f"near-floor (silence/air) : {quiet:.0%} of runtime")
        print(f"upper-band (speech/music): {loud:.0%} of runtime")
        # longest deliberate quiet stretches
        below = envf < fl + 8
        runs, cur = [], 0
        for b in below:
            if b:
                cur += 1
            elif cur:
                runs.append(cur * winf)
                cur = 0
        runs.sort(reverse=True)
        print("longest quiet holds      : " +
              ", ".join(f"{r:.1f}s" for r in runs[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
