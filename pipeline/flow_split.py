#!/usr/bin/env python3
"""Turn a timeline segment into the shots that will cover it.

Veo will not generate longer than 8 seconds, and rule 4 caps a cutaway at 6,
so a 9.95s median segment cannot be one shot. Each over-length segment becomes
the two or three beats its sentence actually contains.

Everything here is integer frames on purpose. Allocating in seconds and
rounding at render time accumulated 3.8 seconds of drift across 130 shots in
V7; the fix padded the gap with a frozen frame and produced an 18-second
stall. Frames are allocated once, they sum to the exact target, and a short
render is an error rather than something to pad.

A cheaper split exists - choosing the beat count that minimises billed seconds
rather than the fewest beats saves $1.90 - but it drops the average shot to
3.93s against the 5.15s median of the documentary this film is modelled on.
Editorial rhythm wins over $1.90.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

FPS = 24
MAX_SHOT = 6.0
# Veo 3.1 Lite accepts only these durations. 1080p would additionally require
# 8s, which is why the film generates at 720p and upscales.
LEGAL_DURATIONS = (4, 6, 8)


@dataclass(frozen=True)
class Beat:
    idx: int
    start: float
    end: float
    frames: int
    gen_dur: int

    @property
    def dur(self) -> float:
        return self.end - self.start


def gen_duration(seconds: float) -> int:
    """Smallest Veo duration that covers `seconds`."""
    for d in LEGAL_DURATIONS:
        if seconds <= d + 1e-9:
            return d
    raise ValueError(f"{seconds:.3f}s exceeds Veo's 8s ceiling")


def beat_count(dur: float) -> int:
    """How many shots a segment of `dur` needs to stay under MAX_SHOT."""
    if dur <= 0:
        raise ValueError(f"non-positive duration {dur}")
    return max(1, math.ceil(dur / MAX_SHOT))


def allocate_frames(total_frames: int, weights: list[float]) -> list[int]:
    """Split `total_frames` across `weights`, summing to exactly the total.

    Largest-remainder: floor everything, then hand the shortfall to whoever
    lost the most in the rounding. Every shot is guaranteed at least 1 frame;
    if the minimum constraint cannot be satisfied, raises ValueError.
    """
    if total_frames < len(weights):
        raise ValueError(
            f"{total_frames} frames cannot cover {len(weights)} shots")
    scale = total_frames / sum(weights)
    exact = [w * scale for w in weights]
    out = [max(1, math.floor(x)) for x in exact]
    short = total_frames - sum(out)

    if short != 0:
        # When subtracting (negative shortfall), only take from indices where
        # out[i] > 1 to maintain the ≥1 frame guarantee
        if short < 0:
            eligible_indices = [i for i in range(len(out)) if out[i] > 1]
            if not eligible_indices:
                raise ValueError(
                    f"Cannot allocate {total_frames} frames across {len(weights)} shots: "
                    f"minimum guarantee (≥1 frame per shot) requires {sum(out)} frames")
            order = sorted(eligible_indices, key=lambda i: exact[i] - out[i],
                           reverse=False)
        else:
            order = sorted(range(len(out)), key=lambda i: exact[i] - out[i],
                           reverse=True)

        step = 1 if short > 0 else -1
        for i in range(abs(short)):
            out[order[i % len(order)]] += step

    return out


def split_segment(start: float, end: float) -> list[Beat]:
    """Split [start, end) into contiguous beats, frame-exact."""
    dur = end - start
    if dur <= 0:
        raise ValueError(f"non-positive segment {start}..{end}")
    n = beat_count(dur)
    frames = allocate_frames(round(dur * FPS), [1.0] * n)
    beats, t = [], start
    for i, f in enumerate(frames):
        nxt = end if i == n - 1 else t + f / FPS
        beats.append(Beat(idx=i, start=t, end=nxt, frames=f,
                          gen_dur=gen_duration(nxt - t)))
        t = nxt
    return beats
