#!/usr/bin/env python3
"""edl.py - pure timeline model for V11 documentary assembly.

No I/O, no ffmpeg, no subprocess. Everything here is a function of the
cut list, which is what makes the format gates unit-testable.

Segment kinds:
  bite - real archival audio, plays with its own audio (J-cut)
  narr - our voiceover
  card - Remotion graphic (Protocol Act only)
  beat - music and picture, nobody speaking
"""
from dataclasses import dataclass, field

KINDS = ("bite", "narr", "card", "beat")


@dataclass
class Seg:
    kind: str
    dur: float
    seg_id: str
    chapter: str
    source: str = ""      # source video id (bite) / wav (narr) / comp (card)
    t0: float = 0.0       # in-source start, bite only
    speaker: str = ""     # bite only
    jcut: float = 0.0     # audio leads picture, seconds
    promise: str = ""     # this segment makes a withheld promise
    resolves: str = ""    # this segment resolves promise <id>
    fitness: bool = False  # picture shows training / physique / food
    text: str = ""        # narration copy, narr only - the TTS input

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"bad kind {self.kind!r}, want one of {KINDS}")
        if self.dur <= 0:
            raise ValueError(f"{self.seg_id}: dur must be > 0")


@dataclass
class EDL:
    segs: list = field(default_factory=list)
    protocol_chapter: str = "protocol"
    subject_speaker: str = "subject"

    def total(self):
        return round(sum(s.dur for s in self.segs), 6)

    def offsets(self):
        out, t = [], 0.0
        for s in self.segs:
            out.append(round(t, 6))
            t += s.dur
        return out

    def runs(self):
        """Index ranges [start, end) of consecutive narration segments."""
        out, i = [], 0
        while i < len(self.segs):
            if self.segs[i].kind != "narr":
                i += 1
                continue
            j = i
            while j < len(self.segs) and self.segs[j].kind == "narr":
                j += 1
            out.append((i, j))
            i = j
        return out
