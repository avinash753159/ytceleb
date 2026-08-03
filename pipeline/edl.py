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
# Real voices must be a CHORUS, not a monologue: no single bite may carry
# more than this many seconds. Mirrors soundbank.MAX_BITE_S (30.0) - kept
# as a local literal, not an import, because edl.py stays dependency-free.
MAX_BITE_S = 30.0

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
    jcut: float = 0.0     # audio leads picture, seconds. INVARIANT: jcut
                          # shifts PICTURE only - the audio timeline is
                          # jcut-invariant, so edl.total() remains the
                          # audio-side truth that check_sync() and V7
                          # compare rendered output against.
    promise: str = ""     # this segment makes a withheld promise
    resolves: str = ""    # this segment resolves promise <id>
    fitness: bool = False  # picture shows training / physique / food
    text: str = ""        # narration copy, narr only - the TTS input

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"{self.seg_id}: bad kind {self.kind!r}, want one of {KINDS}")
        if self.dur <= 0:
            raise ValueError(f"{self.seg_id}: dur must be > 0")


@dataclass
class EDL:
    segs: list = field(default_factory=list)
    protocol_chapter: str = "protocol"
    subject_speaker: str = "subject"
    fitted: bool = False  # True once fit_run_durations() has overwritten
                           # placeholder narration durations with TTS-
                           # measured ones. See qc_v11.report()'s refusal
                           # to compare an unfitted EDL against a render.

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
    """V1 - real archival audio must carry >=40% of runtime, as a CHORUS
    of voices (no single bite over MAX_BITE_S), not one long monologue."""
    out = []
    over = [s.seg_id for s in edl.segs
            if s.kind == "bite" and s.dur > MAX_BITE_S]
    if over:
        out.append(Problem("V1", f"bite(s) over the {MAX_BITE_S:.0f}s "
                                 f"per-bite cap (a chorus of voices, not "
                                 f"one monologue): " + ", ".join(over)))
    total = edl.total()
    if not total:
        return out
    got = _dur([s for s in edl.segs if s.kind == "bite"]) / total
    if got < MIN_VOICE_RATIO:
        out.append(Problem("V1", f"real-voice ratio {got:.1%} < "
                                 f"{MIN_VOICE_RATIO:.0%}"))
    return out


def gate_card_containment(edl):
    """V2 - all graphic cards live inside a single contiguous Protocol
    Act. That means the Act must (a) exist as a chapter in the EDL,
    (b) be one contiguous run of segments, and (c) contain at least one
    card - and no card may appear outside it."""
    out = []
    bad = [s.seg_id for s in edl.segs
           if s.kind == "card" and s.chapter != edl.protocol_chapter]
    if bad:
        out.append(Problem("V2", "cards outside the Protocol Act: "
                                 + ", ".join(bad)))
    protocol_idx = [i for i, s in enumerate(edl.segs)
                    if s.chapter == edl.protocol_chapter]
    if not protocol_idx:
        out.append(Problem("V2", f"Protocol Act chapter "
                                 f"{edl.protocol_chapter!r} does not exist "
                                 f"in the EDL"))
        return out
    runs = 1 + sum(1 for a, b in zip(protocol_idx, protocol_idx[1:])
                   if b != a + 1)
    if runs > 1:
        out.append(Problem("V2", f"Protocol Act is not contiguous: "
                                 f"{runs} separate runs of segments"))
    # A card moved outside the Protocol Act already has a precise V2
    # diagnostic above. Do not report the same root cause a second time as
    # "Protocol Act contains no cards."
    if not bad and not any(edl.segs[i].kind == "card"
                           for i in protocol_idx):
        out.append(Problem("V2", "Protocol Act contains no cards"))
    return out


def gate_promise_resolved(edl):
    """V3 - the cold open withholds a promise and the FINAL chapter pays
    it off. The spec calls this non-negotiable: an EDL that makes no
    promise at all must fail, not pass vacuously. Every promise must
    resolve exactly once, later than it is made, and its resolution must
    land in the film's final chapter."""
    out = []
    made_events = [(i, s.promise) for i, s in enumerate(edl.segs)
                   if s.promise]
    if not made_events:
        out.append(Problem("V3", "no promise is made - the withheld "
                                 "promise is non-negotiable"))
        return out
    resolved_events = [(i, s.resolves) for i, s in enumerate(edl.segs)
                       if s.resolves]

    made = {}
    for i, pid in made_events:
        if pid in made:
            out.append(Problem("V3", f"promise {pid!r} is made more than "
                                     f"once"))
        made[pid] = i

    resolved = {}
    for i, pid in resolved_events:
        if pid in resolved:
            out.append(Problem("V3", f"promise {pid!r} is resolved more "
                                     f"than once"))
        resolved[pid] = i

    final_chapter = edl.segs[-1].chapter if edl.segs else None
    for pid, i in made.items():
        if pid not in resolved:
            out.append(Problem("V3", f"promise {pid!r} is never resolved"))
        elif resolved[pid] <= i:
            out.append(Problem("V3", f"promise {pid!r} resolves at index "
                                     f"{resolved[pid]} before it is made "
                                     f"at {i}"))
        elif edl.segs[resolved[pid]].chapter != final_chapter:
            out.append(Problem("V3", f"promise {pid!r} resolves in "
                                     f"chapter {edl.segs[resolved[pid]].chapter!r}, "
                                     f"not the final chapter "
                                     f"{final_chapter!r}"))
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
    """V6 - F4 reinterpreted. Measured on PICTURE, not audio.

    A `protocol_chapter` that names a chapter absent from the EDL (e.g. a
    Phase 2 author forgetting the beat sheet's top-level key) must FAIL,
    not silently no-op the 90% Protocol Act check.
    """
    out = []
    total = edl.total()
    if total:
        got = _dur([s for s in edl.segs if s.fitness]) / total
        if got < MIN_FITNESS_OVERALL:
            out.append(Problem("V6", f"whole-film fitness picture {got:.1%} "
                                     f"< {MIN_FITNESS_OVERALL:.0%}"))
    if edl.protocol_chapter not in {s.chapter for s in edl.segs}:
        out.append(Problem("V6", f"Protocol Act chapter "
                                 f"{edl.protocol_chapter!r} does not exist "
                                 f"in the EDL - cannot verify the 90% "
                                 f"fitness requirement"))
        return out
    pro = [s for s in edl.segs if s.chapter == edl.protocol_chapter]
    pd = _dur(pro)
    got = _dur([s for s in pro if s.fitness]) / pd
    if got < MIN_FITNESS_PROTOCOL:
        out.append(Problem("V6", f"Protocol Act fitness picture "
                                 f"{got:.1%} < "
                                 f"{MIN_FITNESS_PROTOCOL:.0%}"))
    return out


def gate_chapter_contiguity(edl):
    """V8 - chapters must be contiguous blocks. music.py's own
    _chapter_spans() raises ValueError on a non-contiguous chapter;
    without this gate, validate() blesses a cut list that score_plan()
    then crashes on. (V7 is already taken by qc_v11's rendered-duration
    check, so this new gate is V8.)"""
    collapsed = []
    for s in edl.segs:
        if not collapsed or collapsed[-1] != s.chapter:
            collapsed.append(s.chapter)
    counts = {}
    for c in collapsed:
        counts[c] = counts.get(c, 0) + 1
    bad = sorted(c for c, n in counts.items() if n > 1)
    if bad:
        return [Problem("V8", "chapters not contiguous: " + ", ".join(bad))]
    return []


GATES = (gate_voice_ratio, gate_card_containment, gate_promise_resolved,
         gate_silence_budget, gate_speaker_cap, gate_fitness_ratio,
         gate_chapter_contiguity)


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
    for i, raw in enumerate(doc.get("segments", [])):
        # Validate required keys with helpful error messages
        required_keys = ["id", "kind", "dur", "chapter"]
        for key in required_keys:
            if key not in raw:
                if key == "id":
                    raise ValueError(f"segment {i}: missing required key {key!r}")
                elif "id" in raw:
                    raise ValueError(f"segment {i} (id {raw['id']!r}): missing required key {key!r}")
                else:
                    raise ValueError(f"segment {i}: missing required key {key!r}")

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
