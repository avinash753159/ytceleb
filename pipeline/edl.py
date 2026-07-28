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

MIN_VOICE_RATIO = 0.40        # real archival audio, share of runtime
MIN_BEAT_RATIO = 0.025        # music-only breathing room
MIN_BEAT_COUNT = 6
MAX_SUPPORT_SPEAKER_S = 90.0  # any speaker who is not the subject
MIN_FITNESS_PROTOCOL = 0.90   # picture, inside the Protocol Act
MIN_FITNESS_OVERALL = 0.35    # picture, whole film

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


@dataclass
class Problem:
    code: str
    msg: str


def _dur(segs):
    return round(sum(s.dur for s in segs), 6)


def gate_voice_ratio(edl):
    """V1 - real archival audio must carry >=40% of runtime."""
    total = edl.total()
    if not total:
        return []
    got = _dur([s for s in edl.segs if s.kind == "bite"]) / total
    if got < MIN_VOICE_RATIO:
        return [Problem("V1", f"real-voice ratio {got:.1%} < "
                              f"{MIN_VOICE_RATIO:.0%}")]
    return []


def gate_card_containment(edl):
    """V2 - cards may only appear inside the Protocol Act."""
    bad = [s.seg_id for s in edl.segs
           if s.kind == "card" and s.chapter != edl.protocol_chapter]
    if bad:
        return [Problem("V2", "cards outside the Protocol Act: "
                              + ", ".join(bad))]
    return []


def gate_promise_resolved(edl):
    """V3 - every withheld promise resolves, and resolves later."""
    out = []
    made = {}
    for i, s in enumerate(edl.segs):
        if s.promise:
            made[s.promise] = i
    resolved = {}
    for i, s in enumerate(edl.segs):
        if s.resolves:
            resolved[s.resolves] = i
    for pid, i in made.items():
        if pid not in resolved:
            out.append(Problem("V3", f"promise {pid!r} is never resolved"))
        elif resolved[pid] <= i:
            out.append(Problem("V3", f"promise {pid!r} resolves at index "
                                     f"{resolved[pid]} before it is made "
                                     f"at {i}"))
    for pid in resolved:
        if pid not in made:
            out.append(Problem("V3", f"resolves unknown promise {pid!r}"))
    return out


def gate_silence_budget(edl):
    """V4 - the film must breathe: enough music-only beats."""
    beats = [s for s in edl.segs if s.kind == "beat"]
    total = edl.total()
    if len(beats) < MIN_BEAT_COUNT:
        return [Problem("V4", f"{len(beats)} music-only beats < "
                              f"{MIN_BEAT_COUNT}")]
    if total and _dur(beats) / total < MIN_BEAT_RATIO:
        return [Problem("V4", f"music-only time {_dur(beats) / total:.1%} < "
                              f"{MIN_BEAT_RATIO:.1%}")]
    return []


def gate_speaker_cap(edl):
    """V5 - no supporting speaker may dominate. Subject is exempt."""
    tally = {}
    for s in edl.segs:
        if s.kind != "bite" or not s.speaker:
            continue
        if s.speaker == edl.subject_speaker:
            continue
        tally[s.speaker] = tally.get(s.speaker, 0.0) + s.dur
    return [Problem("V5", f"speaker {k!r} has {v:.0f}s > "
                          f"{MAX_SUPPORT_SPEAKER_S:.0f}s")
            for k, v in sorted(tally.items()) if v > MAX_SUPPORT_SPEAKER_S]


def gate_fitness_ratio(edl):
    """V6 - F4 reinterpreted. Measured on PICTURE, not audio."""
    out = []
    total = edl.total()
    if total:
        got = _dur([s for s in edl.segs if s.fitness]) / total
        if got < MIN_FITNESS_OVERALL:
            out.append(Problem("V6", f"whole-film fitness picture {got:.1%} "
                                     f"< {MIN_FITNESS_OVERALL:.0%}"))
    pro = [s for s in edl.segs if s.chapter == edl.protocol_chapter]
    pd = _dur(pro)
    if pd:
        got = _dur([s for s in pro if s.fitness]) / pd
        if got < MIN_FITNESS_PROTOCOL:
            out.append(Problem("V6", f"Protocol Act fitness picture "
                                     f"{got:.1%} < "
                                     f"{MIN_FITNESS_PROTOCOL:.0%}"))
    return out


GATES = (gate_voice_ratio, gate_card_containment, gate_promise_resolved,
         gate_silence_budget, gate_speaker_cap, gate_fitness_ratio)


def validate(edl):
    out = []
    for g in GATES:
        out.extend(g(edl))
    return out


import json
from pathlib import Path


def build_edl(doc):
    """Build an EDL from a cut-list dict. Raises ValueError on bad input."""
    segs, seen = [], set()
    for raw in doc.get("segments", []):
        sid = raw["id"]
        if sid in seen:
            raise ValueError(f"duplicate segment id {sid!r}")
        seen.add(sid)
        segs.append(Seg(
            kind=raw["kind"],
            dur=float(raw["dur"]),
            seg_id=sid,
            chapter=raw["chapter"],
            source=raw.get("source", ""),
            t0=float(raw.get("t0", 0.0)),
            speaker=raw.get("speaker", ""),
            jcut=float(raw.get("jcut", 0.0)),
            promise=raw.get("promise", ""),
            resolves=raw.get("resolves", ""),
            fitness=bool(raw.get("fitness", False)),
            text=raw.get("text", ""),
        ))
    return EDL(segs=segs,
               protocol_chapter=doc.get("protocol_chapter", "protocol"),
               subject_speaker=doc.get("subject_speaker", "subject"))


def load_edl(path):
    return build_edl(json.loads(Path(path).read_text(encoding="utf-8")))
