#!/usr/bin/env python3
"""music.py - royalty-free cue library and per-chapter scoring.

A single bed at 0.16 with ducking suits a 10-minute explainer. A 30-min
emotional arc needs cues entering and exiting on chapter boundaries.

The library is built ONCE (library/music/cues.json) so scoring an episode
is selection, not search. Only Content-ID-verified cues are eligible -
YouTube Audio Library is the safe spine because it cannot be claimed
against us; Pixabay and Uppbeat fill gaps and must be verified first.
"""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
LIB = ROOT / "library" / "music"

FUNCTIONS = ("dread", "grind", "the-turn", "protocol", "elegy", "payoff")


def load_cues(path=None):
    p = Path(path) if path else (LIB / "cues.json")
    return json.loads(p.read_text(encoding="utf-8"))


def _chapter_spans(edl):
    """[(chapter, start_offset, duration)] in first-appearance order."""
    spans, t = [], 0.0
    for s in edl.segs:
        if spans and spans[-1][0] == s.chapter:
            spans[-1][2] += s.dur
        else:
            spans.append([s.chapter, t, s.dur])
        t += s.dur
    # Check for non-contiguous chapters (same chapter appearing in multiple spans)
    chapter_counts = {}
    for c, a, d in spans:
        chapter_counts[c] = chapter_counts.get(c, 0) + 1
    for chapter, count in chapter_counts.items():
        if count > 1:
            raise ValueError(
                f"chapter {chapter!r} appears in {count} non-contiguous runs; "
                f"chapters must be contiguous blocks")
    return [(c, round(a, 6), round(d, 6)) for c, a, d in spans]


def score_plan(edl, cues, chapter_functions):
    """Assign one verified cue per chapter that has a dramatic function."""
    usable = [c for c in cues if c.get("content_id_checked")]
    by_fn = {}
    for c in usable:
        by_fn.setdefault(c["function"], []).append(c)
    out = []
    for chapter, at, dur in _chapter_spans(edl):
        fn = chapter_functions.get(chapter)
        if not fn:
            continue
        if fn not in by_fn:
            raise ValueError(
                f"chapter {chapter!r} needs a {fn!r} cue and the library has "
                f"no Content-ID-verified {fn!r} track")
        out.append({"chapter": chapter, "cue": by_fn[fn][0]["file"],
                    "at": at, "dur": dur})
    return out
