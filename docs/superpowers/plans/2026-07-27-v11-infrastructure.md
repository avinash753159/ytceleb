# V11 Documentary Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and prove the pipeline a 30-minute Wound documentary needs — a soundbite bank, a testable audio/video EDL that replaces v10's continuous-narration model, a royalty-free cue library, and machine-enforced format gates — without shipping a film.

**Architecture:** The central move is separating **pure computation from ffmpeg execution**. `edl.py` models the timeline and validates it with zero I/O. `v11_assemble.py` *builds ffmpeg commands as data*, then executes them in a separate step. This makes every hard-won F7 audio rule (never acrossfade, always `normalize=0`, never slice narration per beat) a unit test on a command string instead of a comment nobody reads. `soundbank.py` and `music.py` follow the same split: a tested pure core, a thin I/O shell.

**Tech Stack:** Python 3.12 (`py -3.12`), pytest 9.0.2, faster-whisper (installed), ffmpeg/ffprobe on PATH, JSON manifests under `manifest/`.

## Global Constraints

- Repo root: `C:\Users\avina\ytceleb`. All paths below are relative to it.
- Python is invoked as `py -3.12`. Never bare `python`.
- **Never commit media** (`*.mp4`, `*.wav`, `*.mp3`, `*.png`, renders, footage). Source, docs, config and small JSON manifests are all fine to track.
- `.gitignore` is **deny-all with an allowlist** (line 2 is `*`, then `!*.py`, `!*.md`, `!manifest/*.json`, …). A new non-`.py` file therefore needs its own `!` allow rule before it can be staged. Add the rule — never `git add -f` past the guard, which leaves the next person's `git status` lying to them. Verify with `git check-ignore -v <path>` printing nothing. Do not weaken the media denials.
- API keys live in gitignored `*_key.txt` files at repo root. Never inline a key in source.
- **F7 audio rules, verbatim and non-negotiable:**
  - `amix` must always carry `normalize=0`
  - every `amix` input must be `aformat`-ed to stereo *before* mixing
  - narration is never sliced per beat — only per contiguous narration *run*
  - never `acrossfade` — butt-join with 30 ms edge fades and the concat demuxer
  - hard sync gate: refuse to mux if `|video_dur − audio_dur| > 0.25`
- Existing code style: module-level `ROOT = Path(__file__).resolve().parent.parent`, a `run()` subprocess wrapper that raises on non-zero, `probe_dur()` via ffprobe. Follow it.
- Do not modify `v10_assemble.py`, `v6_assemble.py`, or `qc.py`. V11 lives alongside them.

---

## File Structure

| File | Responsibility |
|---|---|
| `pytest.ini` | pytest config (new — repo has no test infra) |
| `tests/conftest.py` | shared fixtures: a synthetic EDL, a synthetic soundbite bank |
| `pipeline/edl.py` | **pure.** `Seg`, `EDL`, `build_edl()`, all format validators. No I/O, no ffmpeg. |
| `tests/test_edl.py` | timeline math + every validator |
| `pipeline/soundbank.py` | transcribe sources → indexed utterances; query/rank bites |
| `tests/test_soundbank.py` | utterance merging + query ranking (pure parts) |
| `pipeline/music.py` | cue library load + chapter→cue assignment |
| `tests/test_music.py` | cue selection |
| `pipeline/v11_assemble.py` | builds ffmpeg commands as data, then executes; sync gate |
| `tests/test_v11_audio_cmds.py` | **F7 regression suite** — asserts on generated command strings |
| `pipeline/qc_v11.py` | runs edl validators + probes a rendered mp4 |
| `tests/test_qc_v11.py` | report assembly |

---

### Task 1: Test harness + EDL timeline model

**Files:**
- Create: `pytest.ini`
- Create: `tests/conftest.py`
- Create: `pipeline/edl.py`
- Test: `tests/test_edl.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `Seg` dataclass with fields `kind: str`, `dur: float`, `seg_id: str`, `chapter: str`, `source: str`, `t0: float`, `speaker: str`, `jcut: float`, `promise: str`, `resolves: str`, `fitness: bool`, `text: str`
  - `EDL` dataclass with fields `segs: list[Seg]`, `protocol_chapter: str`, `subject_speaker: str`; methods `total() -> float`, `offsets() -> list[float]`, `runs() -> list[tuple[int, int]]`
  - `KINDS = ("bite", "narr", "card", "beat")`

- [ ] **Step 1: Create pytest config**

`pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 2: Write the failing test**

`tests/test_edl.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from edl import EDL, Seg  # noqa: E402


def mk(kind, dur, seg_id, chapter="c1", **kw):
    return Seg(kind=kind, dur=dur, seg_id=seg_id, chapter=chapter, **kw)


def test_total_is_sum_of_durations():
    e = EDL(segs=[mk("narr", 3.0, "n0"), mk("bite", 2.5, "b0")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.total() == 5.5


def test_offsets_accumulate_from_zero():
    e = EDL(segs=[mk("narr", 3.0, "n0"), mk("bite", 2.5, "b0"),
                  mk("beat", 1.5, "s0")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.offsets() == [0.0, 3.0, 5.5]


def test_runs_groups_consecutive_narration():
    e = EDL(segs=[mk("narr", 1.0, "n0"), mk("narr", 1.0, "n1"),
                  mk("bite", 1.0, "b0"), mk("narr", 1.0, "n2")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.runs() == [(0, 2), (3, 4)]


def test_runs_is_empty_when_no_narration():
    e = EDL(segs=[mk("bite", 1.0, "b0")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.runs() == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_edl.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'edl'`

- [ ] **Step 4: Write minimal implementation**

`pipeline/edl.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_edl.py -v`
Expected: PASS — 4 passed

- [ ] **Step 6: Add the shared fixture file**

`tests/conftest.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from edl import EDL, Seg  # noqa: E402


@pytest.fixture
def good_edl():
    """A tiny EDL that passes every format gate. 100s total.

    50s bite (50%), 30s narr, 15s card in the protocol chapter, 5s beat.
    """
    segs = [
        Seg(kind="bite", dur=25.0, seg_id="b0", chapter="open",
            speaker="subject", promise="the_photo", fitness=False),
        Seg(kind="narr", dur=15.0, seg_id="n0", chapter="open"),
        Seg(kind="beat", dur=5.0, seg_id="s0", chapter="open", fitness=True),
        Seg(kind="card", dur=15.0, seg_id="c0", chapter="protocol",
            fitness=True),
        Seg(kind="narr", dur=15.0, seg_id="n1", chapter="protocol",
            fitness=True),
        Seg(kind="bite", dur=25.0, seg_id="b1", chapter="payoff",
            speaker="subject", resolves="the_photo", fitness=True),
    ]
    return EDL(segs=segs, protocol_chapter="protocol",
               subject_speaker="subject")
```

- [ ] **Step 7: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pytest.ini tests/conftest.py tests/test_edl.py pipeline/edl.py
git commit -m "feat(v11): EDL timeline model + test harness"
```

---

### Task 2: Format gate validators

**Files:**
- Modify: `pipeline/edl.py` (append validators)
- Test: `tests/test_edl.py` (append)

**Interfaces:**
- Consumes: `Seg`, `EDL` from Task 1
- Produces:
  - `Problem` dataclass: `code: str`, `msg: str`
  - `validate(edl: EDL) -> list[Problem]` — runs all gates, empty list means pass
  - Individual gates, each `(edl) -> list[Problem]`: `gate_voice_ratio`, `gate_card_containment`, `gate_promise_resolved`, `gate_silence_budget`, `gate_speaker_cap`, `gate_fitness_ratio`
  - Thresholds as module constants: `MIN_VOICE_RATIO = 0.40`, `MIN_BEAT_RATIO = 0.025`, `MIN_BEAT_COUNT = 6`, `MAX_SUPPORT_SPEAKER_S = 90.0`, `MIN_FITNESS_PROTOCOL = 0.90`, `MIN_FITNESS_OVERALL = 0.35`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_edl.py`:

```python
from edl import (  # noqa: E402
    gate_card_containment, gate_fitness_ratio, gate_promise_resolved,
    gate_silence_budget, gate_speaker_cap, gate_voice_ratio, validate,
)


def test_voice_ratio_passes_at_forty_percent(good_edl):
    assert gate_voice_ratio(good_edl) == []


def test_voice_ratio_fails_below_threshold(good_edl):
    good_edl.segs[0].dur = 5.0          # bite time 30/80 = 37.5%
    p = gate_voice_ratio(good_edl)
    assert len(p) == 1 and p[0].code == "V1"


def test_card_outside_protocol_act_fails(good_edl):
    good_edl.segs[3].chapter = "open"
    p = gate_card_containment(good_edl)
    assert len(p) == 1 and p[0].code == "V2"
    assert "c0" in p[0].msg


def test_unresolved_promise_fails(good_edl):
    good_edl.segs[5].resolves = ""
    p = gate_promise_resolved(good_edl)
    assert len(p) == 1 and p[0].code == "V3"


def test_promise_resolved_before_it_is_made_fails(good_edl):
    good_edl.segs[0].promise = ""
    good_edl.segs[0].resolves = "the_photo"
    good_edl.segs[5].resolves = ""
    good_edl.segs[5].promise = "the_photo"
    p = gate_promise_resolved(good_edl)
    assert len(p) == 1 and p[0].code == "V3"


def test_silence_budget_fails_with_too_few_beats(good_edl):
    p = gate_silence_budget(good_edl)      # only 1 beat seg, needs 6
    assert len(p) == 1 and p[0].code == "V4"


def test_speaker_cap_fails_for_long_supporting_speaker(good_edl):
    good_edl.segs[0].speaker = "coach"     # 25s, under cap
    good_edl.segs[5].speaker = "coach"     # +25s = 50s, still under
    assert gate_speaker_cap(good_edl) == []
    good_edl.segs[5].dur = 70.0            # 95s total, over cap
    p = gate_speaker_cap(good_edl)
    assert len(p) == 1 and p[0].code == "V5"
    assert "coach" in p[0].msg


def test_subject_speaker_is_exempt_from_cap(good_edl):
    good_edl.segs[5].dur = 500.0
    assert gate_speaker_cap(good_edl) == []


def test_fitness_ratio_fails_when_protocol_act_is_not_training(good_edl):
    good_edl.segs[3].fitness = False       # 15/30 of protocol = 50%
    p = gate_fitness_ratio(good_edl)
    assert any(x.code == "V6" for x in p)


def test_validate_aggregates_all_gates(good_edl):
    codes = {p.code for p in validate(good_edl)}
    assert codes == {"V4"}                 # only the beat-count gate fails
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_edl.py -v`
Expected: FAIL — `ImportError: cannot import name 'gate_card_containment'`

- [ ] **Step 3: Write the implementation**

Append to `pipeline/edl.py`:

```python
MIN_VOICE_RATIO = 0.40        # real archival audio, share of runtime
MIN_BEAT_RATIO = 0.025        # music-only breathing room
MIN_BEAT_COUNT = 6
MAX_SUPPORT_SPEAKER_S = 90.0  # any speaker who is not the subject
MIN_FITNESS_PROTOCOL = 0.90   # picture, inside the Protocol Act
MIN_FITNESS_OVERALL = 0.35    # picture, whole film


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_edl.py -v`
Expected: PASS — 14 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/edl.py tests/test_edl.py
git commit -m "feat(v11): format gate validators V1-V6"
```

---

### Task 3: EDL construction from a cut list

**Files:**
- Modify: `pipeline/edl.py` (append loader)
- Test: `tests/test_edl.py` (append)

**Interfaces:**
- Consumes: `Seg`, `EDL` from Task 1
- Produces: `build_edl(doc: dict) -> EDL`, `load_edl(path) -> EDL`

Cut list JSON schema (this is what the Phase 2 script authoring produces):

```json
{
  "protocol_chapter": "protocol",
  "subject_speaker": "subject",
  "segments": [
    {"kind": "bite", "dur": 25.0, "id": "b0", "chapter": "open",
     "source": "dQw4w9WgXcQ", "t0": 132.5, "speaker": "subject",
     "jcut": 0.4, "promise": "the_photo", "fitness": false}
  ]
}
```

- [ ] **Step 1: Write the failing test**

Append to `tests/test_edl.py`:

```python
from edl import build_edl  # noqa: E402


def test_build_edl_maps_id_to_seg_id():
    doc = {"protocol_chapter": "protocol", "subject_speaker": "subject",
           "segments": [{"kind": "narr", "dur": 2.0, "id": "n0",
                         "chapter": "open"}]}
    e = build_edl(doc)
    assert e.segs[0].seg_id == "n0"
    assert e.protocol_chapter == "protocol"
    assert e.subject_speaker == "subject"


def test_build_edl_applies_defaults():
    doc = {"segments": [{"kind": "bite", "dur": 2.0, "id": "b0",
                         "chapter": "open"}]}
    e = build_edl(doc)
    assert e.segs[0].jcut == 0.0
    assert e.segs[0].fitness is False
    assert e.protocol_chapter == "protocol"


def test_build_edl_rejects_unknown_kind():
    doc = {"segments": [{"kind": "sfx", "dur": 1.0, "id": "x",
                         "chapter": "open"}]}
    try:
        build_edl(doc)
    except ValueError as ex:
        assert "sfx" in str(ex)
    else:
        raise AssertionError("expected ValueError")


def test_build_edl_rejects_duplicate_ids():
    doc = {"segments": [{"kind": "narr", "dur": 1.0, "id": "n0",
                         "chapter": "open"},
                        {"kind": "narr", "dur": 1.0, "id": "n0",
                         "chapter": "open"}]}
    try:
        build_edl(doc)
    except ValueError as ex:
        assert "n0" in str(ex)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_edl.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_edl'`

- [ ] **Step 3: Write the implementation**

Append to `pipeline/edl.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_edl.py -v`
Expected: PASS — 18 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/edl.py tests/test_edl.py
git commit -m "feat(v11): cut-list loader with validation"
```

---

### Task 4: Soundbank — utterance indexing

**Files:**
- Create: `pipeline/soundbank.py`
- Test: `tests/test_soundbank.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `merge_words(words: list[tuple[float, float, str]], max_gap: float = 0.6, max_dur: float = 30.0) -> list[dict]` — groups whisper words into sentence-bounded utterances. Each dict: `{"t0": float, "t1": float, "text": str}`
  - `index_source(src_path, source_id, speaker, model) -> list[dict]` — full utterance records with keys `source_id, t0, t1, speaker, text, topic_tags, emotion, on_camera, audio_clean`
  - `MAX_BITE_S = 30.0`

Whisper words arrive as `(t0, t1, word)` tuples exactly as `v7_interludes.transcribe` returns them. Sentence boundaries are detected the same way v7 does — trailing `[.!?]` optionally followed by a quote.

- [ ] **Step 1: Write the failing test**

`tests/test_soundbank.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from soundbank import merge_words  # noqa: E402


def w(t0, t1, word):
    return (t0, t1, word)


def test_merge_splits_on_sentence_end():
    words = [w(0.0, 0.4, "He"), w(0.4, 0.8, "was"), w(0.8, 1.4, "fifteen."),
             w(1.5, 1.9, "Nobody"), w(1.9, 2.4, "knew.")]
    out = merge_words(words)
    assert len(out) == 2
    assert out[0]["text"] == "He was fifteen."
    assert out[0]["t0"] == 0.0 and out[0]["t1"] == 1.4
    assert out[1]["text"] == "Nobody knew."


def test_merge_splits_on_long_gap():
    words = [w(0.0, 0.4, "He"), w(0.4, 0.8, "was"),
             w(5.0, 5.4, "gone")]
    out = merge_words(words, max_gap=0.6)
    assert len(out) == 2
    assert out[0]["text"] == "He was"
    assert out[1]["text"] == "gone"


def test_merge_splits_when_utterance_exceeds_max_dur():
    words = [w(float(i), float(i) + 0.5, f"x{i}") for i in range(40)]
    out = merge_words(words, max_gap=2.0, max_dur=10.0)
    assert all(u["t1"] - u["t0"] <= 10.0 for u in out)
    assert len(out) >= 4


def test_merge_handles_quoted_sentence_end():
    words = [w(0.0, 0.5, 'gone."'), w(0.6, 1.0, "Next")]
    out = merge_words(words)
    assert len(out) == 2


def test_merge_of_empty_input_is_empty():
    assert merge_words([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_soundbank.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'soundbank'`

- [ ] **Step 3: Write the implementation**

`pipeline/soundbank.py`:

```python
#!/usr/bin/env python3
"""soundbank.py - build and query the archival soundbite bank.

The V11 format needs real voices carrying >=40% of runtime, which means
the script is written TO the material rather than the material hunted to
match the script. This module indexes every utterance in every source so
the bank exists before the script does.

Sources are transcribed with faster-whisper (punctuated + word
timestamps). YouTube auto-caption VTTs carry no punctuation and are
useless for sentence boundaries - established in v7_interludes.

Output: manifest/soundbites.json
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"

MAX_BITE_S = 30.0
SENT_END = re.compile(r"[.!?]['\"]?$")


def merge_words(words, max_gap=0.6, max_dur=MAX_BITE_S):
    """Group (t0, t1, word) tuples into sentence-bounded utterances.

    Splits on: sentence-final punctuation, a silence gap > max_gap, or
    an utterance running past max_dur.
    """
    out, cur = [], []

    def flush():
        if cur:
            out.append({"t0": round(cur[0][0], 2),
                        "t1": round(cur[-1][1], 2),
                        "text": " ".join(x[2] for x in cur)})
            cur.clear()

    for i, (t0, t1, word) in enumerate(words):
        if cur:
            if t0 - cur[-1][1] > max_gap:
                flush()
            elif t1 - cur[0][0] > max_dur:
                flush()
        cur.append((t0, t1, word))
        if SENT_END.search(word):
            flush()
    flush()
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_soundbank.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Add the I/O shell**

Append to `pipeline/soundbank.py`:

```python
def _transcribe(src, model):
    """Whisper a whole source; return [(t0, t1, word), ...]."""
    wav = Path(tempfile.gettempdir()) / f"sb_{Path(src).stem}.wav"
    subprocess.run(["ffmpeg", "-i", str(src), "-vn", "-ac", "1",
                    "-ar", "16000", "-y", str(wav)],
                   capture_output=True, check=True)
    segs, _ = model.transcribe(str(wav), word_timestamps=True, language="en")
    words = []
    for s in segs:
        for x in s.words or []:
            words.append((x.start, x.end, x.word.strip()))
    wav.unlink(missing_ok=True)
    return words


def index_source(src_path, source_id, speaker, model):
    """Transcribe one source into full utterance records."""
    return [{"source_id": source_id,
             "t0": u["t0"],
             "t1": u["t1"],
             "speaker": speaker,
             "text": u["text"],
             "topic_tags": [],
             "emotion": "",
             "on_camera": True,
             "audio_clean": True}
            for u in merge_words(_transcribe(src_path, model))]


def main():
    """Index every source listed in manifest/bank_sources.json.

    bank_sources.json: [{"id": "<yt id>", "path": "dossier/x/<id>.mp4",
                         "speaker": "subject"}, ...]
    """
    from faster_whisper import WhisperModel
    model = WhisperModel("base.en", compute_type="int8")
    srcs = json.loads((MAN / "bank_sources.json").read_text(encoding="utf-8"))
    bank = []
    for s in srcs:
        p = ROOT / s["path"]
        if not p.exists():
            print(f"{s['id']}: MISSING {p} - skipped")
            continue
        recs = index_source(p, s["id"], s.get("speaker", "unknown"), model)
        bank.extend(recs)
        print(f"{s['id']}: {len(recs)} utterances", flush=True)
    (MAN / "soundbites.json").write_text(
        json.dumps(bank, indent=1), encoding="utf-8")
    print(f"[OK] {len(bank)} utterances -> manifest/soundbites.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run tests again to confirm nothing broke**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/ -v`
Expected: PASS — 26 passed

- [ ] **Step 7: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/soundbank.py tests/test_soundbank.py
git commit -m "feat(v11): soundbank utterance indexing"
```

---

### Task 5: Soundbank — query and ranking

**Files:**
- Modify: `pipeline/soundbank.py` (append)
- Test: `tests/test_soundbank.py` (append)

**Interfaces:**
- Consumes: utterance records from Task 4
- Produces: `query(bank: list[dict], topic: str = "", speaker: str = "", emotion: str = "", max_dur: float = MAX_BITE_S, limit: int = 20) -> list[dict]`

Ranking: exact `topic_tags` match scores 2, a case-insensitive substring hit in `text` scores 1, matching `emotion` adds 1, `audio_clean` adds 0.5. Records failing a hard filter (`speaker`, `max_dur`) are excluded entirely. Ties break by shorter duration — short bites cut better.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_soundbank.py`:

```python
from soundbank import query  # noqa: E402


def rec(sid, t0, t1, speaker, text, tags=(), emotion="", clean=True):
    return {"source_id": sid, "t0": t0, "t1": t1, "speaker": speaker,
            "text": text, "topic_tags": list(tags), "emotion": emotion,
            "on_camera": True, "audio_clean": clean}


BANK = [
    rec("a", 0, 5, "subject", "I was going ten times a day.",
        tags=["crohns"], emotion="pain"),
    rec("b", 0, 4, "coach", "He never missed a session.", tags=["training"]),
    rec("c", 0, 40, "subject", "Long rambling crohns answer.",
        tags=["crohns"]),
    rec("d", 0, 3, "subject", "The crohns thing was brutal.", clean=False),
]


def test_query_filters_by_speaker():
    out = query(BANK, speaker="coach")
    assert [r["source_id"] for r in out] == ["b"]


def test_query_excludes_bites_over_max_dur():
    out = query(BANK, topic="crohns", max_dur=30.0)
    assert "c" not in [r["source_id"] for r in out]


def test_query_ranks_tag_match_above_text_match():
    out = query(BANK, topic="crohns", max_dur=30.0)
    assert out[0]["source_id"] == "a"


def test_query_emotion_boosts_score():
    out = query(BANK, topic="crohns", emotion="pain", max_dur=30.0)
    assert out[0]["source_id"] == "a"


def test_query_respects_limit():
    assert len(query(BANK, limit=2)) == 2


def test_query_with_no_criteria_returns_everything_under_max_dur():
    assert len(query(BANK, max_dur=30.0)) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_soundbank.py -v`
Expected: FAIL — `ImportError: cannot import name 'query'`

- [ ] **Step 3: Write the implementation**

Append to `pipeline/soundbank.py`:

```python
def _score(r, topic, emotion):
    s = 0.0
    if topic:
        if topic in r.get("topic_tags", []):
            s += 2.0
        elif topic.lower() in r.get("text", "").lower():
            s += 1.0
    if emotion and r.get("emotion") == emotion:
        s += 1.0
    if r.get("audio_clean"):
        s += 0.5
    return s


def query(bank, topic="", speaker="", emotion="", max_dur=MAX_BITE_S,
          limit=20):
    """Rank soundbites for a chapter. Hard filters first, then score."""
    hits = []
    for r in bank:
        if speaker and r.get("speaker") != speaker:
            continue
        if (r["t1"] - r["t0"]) > max_dur:
            continue
        hits.append((_score(r, topic, emotion), -(r["t1"] - r["t0"]), r))
    hits.sort(key=lambda x: (-x[0], -x[1]))
    return [r for _, _, r in hits[:limit]]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_soundbank.py -v`
Expected: PASS — 11 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/soundbank.py tests/test_soundbank.py
git commit -m "feat(v11): soundbank query + ranking"
```

---

### Task 6: Music cue library

**Files:**
- Create: `pipeline/music.py`
- Create: `library/music/cues.json` (metadata only — no audio committed)
- Test: `tests/test_music.py`

**Interfaces:**
- Consumes: `EDL` from Task 1
- Produces:
  - `FUNCTIONS = ("dread", "grind", "the-turn", "protocol", "elegy", "payoff")`
  - `load_cues(path) -> list[dict]` — each `{"file": str, "function": str, "bpm": int, "dur": float, "source": str, "license": str, "content_id_checked": bool}`
  - `score_plan(edl: EDL, cues: list[dict], chapter_functions: dict) -> list[dict]` — returns `[{"chapter": str, "cue": str, "at": float, "dur": float}]`, one cue per chapter, entering at the chapter's first segment offset

`chapter_functions` maps chapter name → dramatic function, e.g. `{"open": "dread", "protocol": "protocol", "payoff": "payoff"}`.

Only cues with `content_id_checked: true` are eligible — an unverified track is a copyright claim waiting to happen.

- [ ] **Step 1: Write the failing tests**

`tests/test_music.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from music import score_plan  # noqa: E402


CUES = [
    {"file": "dread_a.mp3", "function": "dread", "bpm": 70, "dur": 180.0,
     "source": "YouTube Audio Library", "license": "YTAL",
     "content_id_checked": True},
    {"file": "protocol_a.mp3", "function": "protocol", "bpm": 120,
     "dur": 200.0, "source": "Pixabay", "license": "CC0",
     "content_id_checked": True},
    # unverified listed FIRST so a naive implementation would pick it
    {"file": "payoff_unverified.mp3", "function": "payoff", "bpm": 60,
     "dur": 200.0, "source": "Uppbeat", "license": "free",
     "content_id_checked": False},
    {"file": "payoff_a.mp3", "function": "payoff", "bpm": 60, "dur": 200.0,
     "source": "YouTube Audio Library", "license": "YTAL",
     "content_id_checked": True},
]

CHAPTER_FN = {"open": "dread", "protocol": "protocol", "payoff": "payoff"}


def test_score_plan_assigns_one_cue_per_chapter(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert [p["chapter"] for p in plan] == ["open", "protocol", "payoff"]


def test_score_plan_cue_enters_at_chapter_start(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert plan[0]["at"] == 0.0
    assert plan[1]["at"] == 45.0        # 25 + 15 + 5
    assert plan[2]["at"] == 75.0        # + 15 + 15


def test_score_plan_cue_spans_the_whole_chapter(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert plan[0]["dur"] == 45.0
    assert plan[1]["dur"] == 30.0
    assert plan[2]["dur"] == 25.0


def test_score_plan_never_picks_an_unverified_cue(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert plan[2]["cue"] == "payoff_a.mp3"


def test_score_plan_raises_when_a_function_has_only_unverified_cues(
        good_edl):
    cues = [c for c in CUES if c["file"] != "payoff_a.mp3"]
    try:
        score_plan(good_edl, cues, CHAPTER_FN)
    except ValueError as ex:
        assert "payoff" in str(ex)
    else:
        raise AssertionError("expected ValueError")


def test_score_plan_raises_when_no_cue_for_a_used_function(good_edl):
    try:
        score_plan(good_edl, [CUES[1]], CHAPTER_FN)
    except ValueError as ex:
        assert "dread" in str(ex)
    else:
        raise AssertionError("expected ValueError")


def test_score_plan_ignores_chapters_with_no_dramatic_function(good_edl):
    plan = score_plan(good_edl, CUES, {"protocol": "protocol"})
    assert [p["chapter"] for p in plan] == ["protocol"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_music.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'music'`

- [ ] **Step 3: Write the implementation**

`pipeline/music.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_music.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: Create the empty cue library with its schema documented**

`library/music/cues.json`:

```json
[
  {
    "file": "PLACEHOLDER-DELETE-ME.mp3",
    "function": "dread",
    "bpm": 70,
    "dur": 0.0,
    "source": "YouTube Audio Library",
    "license": "YTAL - free to use, no attribution, cannot be claimed",
    "content_id_checked": false,
    "note": "Schema example only. content_id_checked=false makes it ineligible. Replace with real cues; 20-30 tracks across dread/grind/the-turn/protocol/elegy/payoff."
  }
]
```

`.gitignore` in this repo is **deny-all with an allowlist** (line 2 is `*`,
followed by `!*.py`, `!manifest/*.json`, etc.). Audio is therefore already
ignored — but so is `cues.json`, which means it cannot be staged until you add
an allow rule. Add exactly this line, next to the other `!` entries:

```
!library/music/cues.json
```

Verify before committing: `git check-ignore -v library/music/cues.json` must
print nothing. Do NOT add `library/music/*.mp3` / `*.wav` deny rules — they are
redundant under the deny-all and only obscure the real rule.

- [ ] **Step 6: Run the full suite**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/ -v`
Expected: PASS — 39 passed

- [ ] **Step 7: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/music.py tests/test_music.py library/music/cues.json .gitignore
git commit -m "feat(v11): royalty-free cue library + per-chapter scoring"
```

---

### Task 7: v11 audio command builder — the F7 regression suite

**Files:**
- Create: `pipeline/v11_assemble.py`
- Test: `tests/test_v11_audio_cmds.py`

**Interfaces:**
- Consumes: `EDL`, `Seg` from Task 1
- Produces:
  - `Cmd = list[str]` (an ffmpeg argv)
  - `narration_texts(edl) -> list[str]` — the TTS input for each narration **run**, joined from its segments' `text`
  - `fit_run_durations(edl, run_durs: list[float]) -> None` — after TTS, distribute each run's *measured* duration across its segments in proportion to text length
  - `norm_cmds(paths: list[Path], workdir, prefix: str) -> list[tuple[Cmd, Path]]` — normalise any wav to 48 kHz stereo
  - `bite_cmds(edl, source_paths: dict, workdir) -> list[tuple[Cmd, Path]]`
  - `fade_cmds(chunks: list[tuple[Path, float]], workdir) -> list[tuple[Cmd, Path]]` — 30 ms edge fades. **Takes (path, duration) pairs** — a fade-out needs the duration to compute its start time, and probing inside the builder would make it untestable.
  - `concat_cmd(faded: list[Path], listfile: Path, out: Path) -> Cmd`
  - `music_mix_cmd(base: Path, plan: list[dict], cue_dir: Path, out: Path) -> Cmd`
  - `check_sync(video_dur: float, audio_dur: float) -> None` — raises `SyncError` past 0.25 s
  - `SyncError(Exception)`, `SYNC_TOLERANCE = 0.25`

**Why narration is generated per run rather than sliced from a master.** v10
could `atrim` a VO master at beat offsets because narration *was* the timeline —
beats mapped 1:1 onto VO time. In V11 that is false: bites occupy film time but
no VO time, so a film-timeline offset does not address the right sample in a VO
master. Narration is therefore **generated** one wav per run (the spec's "~25–35
generations"), never sliced. This also satisfies F7 bug 3 by construction — there
is no slicing to glitch — and it means run durations are an *output* of TTS, so
the cut list's `dur` for narration segments is a placeholder that
`fit_run_durations` overwrites before validation runs.

This is the task that turns the F7 ledger into tests. **Every assertion below corresponds to a bug that shipped.**

- [ ] **Step 1: Write the failing tests**

`tests/test_v11_audio_cmds.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from edl import EDL, Seg  # noqa: E402
from v11_assemble import (  # noqa: E402
    SyncError, bite_cmds, check_sync, concat_cmd, fade_cmds,
    fit_run_durations, music_mix_cmd, narration_texts, norm_cmds,
)

WORK = Path("/tmp/v11work")


def _edl():
    return EDL(
        segs=[Seg(kind="narr", dur=10.0, seg_id="n0", chapter="open",
                  text="He was fifteen."),
              Seg(kind="narr", dur=8.0, seg_id="n1", chapter="open",
                  text="Nobody knew."),
              Seg(kind="bite", dur=6.0, seg_id="b0", chapter="open",
                  source="vid1", t0=42.0, speaker="subject"),
              Seg(kind="narr", dur=5.0, seg_id="n2", chapter="open",
                  text="Not for eight years.")],
        protocol_chapter="protocol", subject_speaker="subject")


# ---- F7(3): narration is GENERATED per run, never sliced -------------

def test_one_tts_input_per_run_not_per_segment():
    texts = narration_texts(_edl())
    assert len(texts) == 2          # two runs, not three narr segments


def test_run_text_joins_its_segments_in_order():
    assert narration_texts(_edl())[0] == "He was fifteen. Nobody knew."


def test_fit_distributes_measured_duration_across_a_run():
    e = _edl()
    fit_run_durations(e, [30.0, 5.0])
    # run 0 texts are 15 and 12 chars -> 30s split 15:12
    assert round(e.segs[0].dur + e.segs[1].dur, 3) == 30.0
    assert e.segs[0].dur > e.segs[1].dur
    assert e.segs[3].dur == 5.0


def test_fit_leaves_bites_untouched():
    e = _edl()
    fit_run_durations(e, [30.0, 5.0])
    assert e.segs[2].dur == 6.0


def test_fit_rejects_wrong_number_of_runs():
    try:
        fit_run_durations(_edl(), [30.0])
    except ValueError as ex:
        assert "2 runs" in str(ex)
    else:
        raise AssertionError("expected ValueError")


# ---- F7(4): never acrossfade -----------------------------------------

def test_no_command_ever_uses_acrossfade():
    e = _edl()
    all_cmds = [c for c, _ in norm_cmds([Path("r0.wav")], WORK, "narr")]
    all_cmds += [c for c, _ in bite_cmds(e, {"vid1": Path("v1.mp4")}, WORK)]
    all_cmds += [c for c, _ in fade_cmds([(Path("a.wav"), 5.0)], WORK)]
    all_cmds.append(concat_cmd([Path("a.wav")], WORK / "l.txt",
                               WORK / "o.wav"))
    all_cmds.append(music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "c.mp3", "at": 0.0, "dur": 10.0}],
        Path("cues"), WORK / "m.wav"))
    for c in all_cmds:
        assert "acrossfade" not in " ".join(c)


# ---- butt-join with 30ms edge fades ----------------------------------

def test_fade_applies_30ms_in_and_out_at_the_right_offset():
    (cmd, _), = fade_cmds([(Path("a.wav"), 5.0)], WORK)
    joined = " ".join(cmd)
    assert "afade=t=in:d=0.03" in joined
    assert "afade=t=out:st=4.970:d=0.03" in joined


def test_fade_out_start_never_goes_negative_on_a_tiny_chunk():
    (cmd, _), = fade_cmds([(Path("a.wav"), 0.01)], WORK)
    assert "afade=t=out:st=0.000:d=0.03" in " ".join(cmd)


def test_fade_normalises_to_stereo_48k():
    (cmd, _), = fade_cmds([(Path("a.wav"), 5.0)], WORK)
    joined = " ".join(cmd)
    assert "channel_layouts=stereo" in joined
    assert "sample_rates=48000" in joined


def test_concat_uses_the_demuxer_and_stream_copy():
    cmd = concat_cmd([Path("a.wav")], WORK / "l.txt", WORK / "o.wav")
    assert "-f" in cmd and "concat" in cmd
    assert "-c" in cmd and "copy" in cmd


# ---- F7(1)+(2): amix normalize=0, stereo before mixing ---------------

def test_music_mix_disables_amix_renormalisation():
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "c.mp3", "at": 0.0, "dur": 10.0}],
        Path("cues"), WORK / "m.wav")
    assert "normalize=0" in " ".join(cmd)


def test_every_music_input_is_stereo_before_mixing():
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "a.mp3", "at": 0.0, "dur": 10.0},
         {"chapter": "protocol", "cue": "b.mp3", "at": 10.0, "dur": 8.0}],
        Path("cues"), WORK / "m.wav")
    joined = " ".join(cmd)
    assert joined.count("channel_layouts=stereo") >= 2


def test_music_cue_is_delayed_to_its_chapter_offset():
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "protocol", "cue": "b.mp3", "at": 12.5, "dur": 8.0}],
        Path("cues"), WORK / "m.wav")
    assert "adelay=12500|12500" in " ".join(cmd)


# ---- bites ------------------------------------------------------------

def test_bite_is_extracted_from_its_source_window():
    (cmd, _), = bite_cmds(_edl(), {"vid1": Path("v1.mp4")}, WORK)
    joined = " ".join(cmd)
    assert "-ss" in cmd and "42.0" in joined
    assert "-t" in cmd and "6.0" in joined


def test_bite_for_missing_source_raises():
    with pytest.raises(KeyError):
        bite_cmds(_edl(), {}, WORK)


# ---- the hard sync gate ----------------------------------------------

def test_sync_gate_passes_within_tolerance():
    check_sync(100.0, 100.2)


def test_sync_gate_raises_past_tolerance():
    with pytest.raises(SyncError):
        check_sync(100.0, 100.4)


def test_sync_gate_is_symmetric():
    with pytest.raises(SyncError):
        check_sync(100.4, 100.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_v11_audio_cmds.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'v11_assemble'`

- [ ] **Step 3: Write the implementation**

`pipeline/v11_assemble.py`:

```python
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
    """Overlay scored cues onto the speech track at chapter offsets."""
    ins = ["-i", str(base)]
    parts, mix = [], "[0:a]"
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_v11_audio_cmds.py -v`
Expected: PASS — 18 passed

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/ -v`
Expected: PASS — 57 passed

- [ ] **Step 6: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/v11_assemble.py tests/test_v11_audio_cmds.py
git commit -m "feat(v11): audio command builder + F7 regression suite"
```

---

### Task 8: v11 audio driver

**Files:**
- Modify: `pipeline/v11_assemble.py` (append)
- Test: `tests/test_v11_audio_cmds.py` (append)

**Interfaces:**
- Consumes: everything from Task 7, `load_edl` from Task 3, `score_plan`/`load_cues` from Task 6
- Produces:
  - `audio_chunk_order(edl, workdir) -> list[Path]` — the chunk sequence in timeline order, interleaving narration runs and bites
  - `build_audio(edl, run_wavs: list[Path], source_paths: dict, workdir, music_plan=None, cue_dir=None) -> Path`

`run_wavs` is one already-generated TTS wav per narration run, in run order — produced by the caller (edge-tts for drafts, ElevenLabs once at the end), never sliced from a master.

`audio_chunk_order` is pure and testable; `build_audio` executes.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_v11_audio_cmds.py`:

```python
from v11_assemble import audio_chunk_order  # noqa: E402


def test_chunk_order_interleaves_runs_and_bites():
    names = [p.name for p in audio_chunk_order(_edl(), WORK)]
    assert names == ["narr_00.wav", "bite_b0.wav", "narr_01.wav"]


def test_chunk_order_ignores_cards_and_beats():
    e = EDL(segs=[Seg(kind="card", dur=3.0, seg_id="c0",
                      chapter="protocol"),
                  Seg(kind="beat", dur=2.0, seg_id="s0", chapter="open"),
                  Seg(kind="narr", dur=4.0, seg_id="n0", chapter="open")],
            protocol_chapter="protocol", subject_speaker="subject")
    names = [p.name for p in audio_chunk_order(e, WORK)]
    assert names == ["narr_00.wav"]


def test_chunk_order_is_empty_for_an_empty_edl():
    e = EDL(segs=[], protocol_chapter="protocol",
            subject_speaker="subject")
    assert audio_chunk_order(e, WORK) == []
```

Note: cards and beats carry no speech — their audio is silence under the music bed, laid in by `music_mix_cmd` against the video timeline, so they contribute no speech chunk.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_v11_audio_cmds.py -v`
Expected: FAIL — `ImportError: cannot import name 'audio_chunk_order'`

- [ ] **Step 3: Write the implementation**

Append to `pipeline/v11_assemble.py`:

```python
def audio_chunk_order(edl, workdir):
    """Speech chunks in timeline order: narration runs and bites.

    Cards and music-only beats carry no speech; their silence comes from
    the video timeline and the music bed.
    """
    run_at = {i: k for k, (i, _) in enumerate(edl.runs())}
    out = []
    for i, s in enumerate(edl.segs):
        if i in run_at:
            out.append(Path(workdir) / f"narr_{run_at[i]:02d}.wav")
        elif s.kind == "bite":
            out.append(Path(workdir) / f"bite_{s.seg_id}.wav")
    return out


def build_audio(edl, run_wavs, source_paths, workdir,
                music_plan=None, cue_dir=None):
    """Normalise, extract, fade, butt-join, then lay the music bed.

    run_wavs: one already-generated TTS wav per narration run, in run
    order. Never a master to be sliced - see narration_texts().
    """
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)

    if len(run_wavs) != len(edl.runs()):
        raise ValueError(f"got {len(run_wavs)} run wavs for "
                         f"{len(edl.runs())} narration runs")
    for cmd, _ in norm_cmds(run_wavs, work, "narr"):
        run(cmd)
    for cmd, _ in bite_cmds(edl, source_paths, work):
        run(cmd)

    chunks = [(p, probe_dur(p)) for p in audio_chunk_order(edl, work)]
    faded = []
    for cmd, dst in fade_cmds(chunks, work):
        run(cmd)
        faded.append(dst)

    listfile = work / "achain.txt"
    listfile.write_text(
        "\n".join(f"file '{f.absolute().as_posix()}'" for f in faded),
        encoding="utf-8")
    speech = work / "speech.wav"
    run(concat_cmd(faded, listfile, speech))

    if not music_plan:
        return speech
    mixed = work / "speech_music.wav"
    run(music_mix_cmd(speech, music_plan, cue_dir, mixed))
    return mixed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/ -v`
Expected: PASS — 60 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/v11_assemble.py tests/test_v11_audio_cmds.py
git commit -m "feat(v11): audio driver - extract, fade, butt-join, score"
```

---

### Task 9: QC runner

**Files:**
- Create: `pipeline/qc_v11.py`
- Test: `tests/test_qc_v11.py`

**Interfaces:**
- Consumes: `validate`, `Problem`, `load_edl` from Tasks 2–3; `probe_dur`, `SYNC_TOLERANCE` from Task 7
- Produces:
  - `report(edl, rendered_dur=None) -> dict` — `{"passed": bool, "problems": [{"code","msg"}], "runtime_s": float}`
  - `main()` CLI: `py -3.12 pipeline/qc_v11.py manifest/cutlist.json [rendered.mp4]`, exits non-zero on any failure

- [ ] **Step 1: Write the failing tests**

`tests/test_qc_v11.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from qc_v11 import report  # noqa: E402


def test_report_flags_the_failing_gate(good_edl):
    r = report(good_edl)
    assert r["passed"] is False
    assert [p["code"] for p in r["problems"]] == ["V4"]


def test_report_passes_a_clean_edl(good_edl):
    from edl import Seg
    for i in range(6):
        good_edl.segs.append(
            Seg(kind="beat", dur=1.0, seg_id=f"s{i + 1}", chapter="payoff",
                fitness=True))
    r = report(good_edl)
    assert r["passed"] is True
    assert r["problems"] == []


def test_report_includes_runtime(good_edl):
    assert report(good_edl)["runtime_s"] == 100.0


def test_rendered_duration_mismatch_is_a_problem(good_edl):
    r = report(good_edl, rendered_dur=104.0)
    assert any(p["code"] == "V7" for p in r["problems"])


def test_rendered_duration_within_tolerance_is_fine(good_edl):
    r = report(good_edl, rendered_dur=100.1)
    assert not any(p["code"] == "V7" for p in r["problems"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/test_qc_v11.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'qc_v11'`

- [ ] **Step 3: Write the implementation**

`pipeline/qc_v11.py`:

```python
#!/usr/bin/env python3
"""qc_v11.py - V11 format gates.

Runs the pure EDL validators (V1-V6) and, when given a rendered file,
checks the render matches the timeline (V7).

This sits ALONGSIDE qc.py - qc.py's G1-G8 render checks still apply.

Run: py -3.12 pipeline/qc_v11.py manifest/cutlist.json [rendered.mp4]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edl import load_edl, validate  # noqa: E402
from v11_assemble import SYNC_TOLERANCE, probe_dur  # noqa: E402


def report(edl, rendered_dur=None):
    problems = [{"code": p.code, "msg": p.msg} for p in validate(edl)]
    total = edl.total()
    if rendered_dur is not None and abs(rendered_dur - total) > \
            SYNC_TOLERANCE:
        problems.append({
            "code": "V7",
            "msg": f"rendered {rendered_dur:.2f}s vs timeline {total:.2f}s "
                   f"(drift {rendered_dur - total:+.2f}s)"})
    return {"passed": not problems, "problems": problems,
            "runtime_s": total}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    edl = load_edl(argv[0])
    dur = probe_dur(argv[1]) if len(argv) > 1 else None
    r = report(edl, dur)
    print(json.dumps(r, indent=1))
    for p in r["problems"]:
        print(f"  FAIL {p['code']}: {p['msg']}", file=sys.stderr)
    print(f"[{'OK' if r['passed'] else 'FAIL'}] "
          f"{r['runtime_s'] / 60:.1f} min, {len(r['problems'])} problems")
    Path("qc_v11_report.json").write_text(json.dumps(r, indent=1),
                                          encoding="utf-8")
    return 0 if r["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/avina/ytceleb && py -3.12 -m pytest tests/ -v`
Expected: PASS — 65 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/avina/ytceleb
git add pipeline/qc_v11.py tests/test_qc_v11.py
git commit -m "feat(v11): QC runner for format gates V1-V7"
```

---

### Task 10: Three-minute slice proof

The spec requires v11 be proven on a short slice before a 30-minute film touches it. This task produces an actual rendered artifact and measures it.

**Files:**
- Create: `manifest/slice_cutlist.json`
- Create: `pipeline/v11_slice.py`

**Interfaces:**
- Consumes: `build_audio`, `check_sync`, `probe_dur` (Task 8/7), `load_edl` (Task 3), `report` (Task 9)
- Produces: `final_video/V11_SLICE.mp4` and a passing `qc_v11_report.json`

- [ ] **Step 1: Pick two real local sources and write the slice cut list**

Use two already-downloaded sources so nothing needs fetching. List them:

Run: `cd /c/Users/avina/ytceleb && ls dossier/statham/*.mp4`

The cut list below uses `fSS10kxDFVk` (Flaa junket, 277 s — WATCH_NOTES verifies
clean speech at 131–180 s) and `xrxH5n93CzM` (BBC diving feature, 154 s — all
windows verified). Both are present in the repo. Do NOT substitute ids from the
OneDrive mirror; several sources there were never committed and are absent here.

Write `manifest/slice_cutlist.json`, ~180 s total, deliberately built to pass every gate: ≥40% bite time, ≥6 beat segments, cards only in `"protocol"`, one promise resolved at the end, fitness picture ≥35% overall and ≥90% in protocol.

```json
{
  "protocol_chapter": "protocol",
  "subject_speaker": "subject",
  "segments": [
    {"kind": "bite", "dur": 20.0, "id": "b0", "chapter": "open",
     "source": "fSS10kxDFVk", "t0": 131.0, "speaker": "subject",
     "promise": "the_dive", "fitness": false},
    {"kind": "narr", "dur": 12.0, "id": "n0", "chapter": "open",
     "text": "This is a proving run for the version eleven audio assembly. The narration you are hearing was generated one run at a time, never sliced from a master."},
    {"kind": "beat", "dur": 3.0, "id": "s0", "chapter": "open",
     "fitness": true},
    {"kind": "bite", "dur": 18.0, "id": "b1", "chapter": "open",
     "source": "xrxH5n93CzM", "t0": 20.0, "speaker": "subject",
     "fitness": true},
    {"kind": "beat", "dur": 3.0, "id": "s1", "chapter": "open",
     "fitness": true},
    {"kind": "narr", "dur": 10.0, "id": "n1", "chapter": "protocol",
     "text": "Every join in this file is a butt join with thirty millisecond edge fades, because crossfading overlaps the inputs and drifts the picture."},
    {"kind": "card", "dur": 14.0, "id": "c0", "chapter": "protocol",
     "fitness": true},
    {"kind": "beat", "dur": 3.0, "id": "s2", "chapter": "protocol",
     "fitness": true},
    {"kind": "card", "dur": 14.0, "id": "c1", "chapter": "protocol",
     "fitness": true},
    {"kind": "beat", "dur": 3.0, "id": "s3", "chapter": "protocol",
     "fitness": true},
    {"kind": "bite", "dur": 20.0, "id": "b2", "chapter": "protocol",
     "source": "fSS10kxDFVk", "t0": 151.0, "speaker": "subject",
     "fitness": true},
    {"kind": "beat", "dur": 3.0, "id": "s4", "chapter": "payoff",
     "fitness": true},
    {"kind": "narr", "dur": 12.0, "id": "n2", "chapter": "payoff",
     "text": "If the sync gate passes and no join clips, the version eleven audio timeline is sound and a thirty minute film can be built on it."},
    {"kind": "beat", "dur": 3.0, "id": "s5", "chapter": "payoff",
     "fitness": true},
    {"kind": "bite", "dur": 22.0, "id": "b3", "chapter": "payoff",
     "source": "xrxH5n93CzM", "t0": 90.0, "speaker": "subject",
     "resolves": "the_dive", "fitness": true}
  ]
}
```

- [ ] **Step 2: Structural pre-check of the slice cut list**

Run: `cd /c/Users/avina/ytceleb && py -3.12 pipeline/qc_v11.py manifest/slice_cutlist.json`
Expected: `[OK] 2.7 min, 0 problems`, exit 0.

This runs against the cut list's *placeholder* narration durations, so it
verifies structure (card containment, promise resolution, beat count) rather
than final ratios. The authoritative gate run happens inside `v11_slice.py`
after `fit_run_durations` replaces the placeholders with measured TTS lengths.

If a gate fails at either point, adjust the cut list. **Do not weaken a
threshold in `edl.py` to make this pass** — the gate is the product.

- [ ] **Step 3: Write the slice driver**

`pipeline/v11_slice.py`:

```python
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

    audio = build_audio(edl, run_wavs, sources, WORK)
    ad = probe_dur(audio)
    print(f"[audio] {ad:.2f}s")

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
```

- [ ] **Step 4: Run the slice end-to-end**

Run: `cd /c/Users/avina/ytceleb && py -3.12 pipeline/v11_slice.py`
Expected: prints `[sync] ... OK` and `[OK] .../V11_SLICE.mp4 (~180.0s)`, exit 0.

If the sync gate raises, that is the gate doing its job — do not raise `SYNC_TOLERANCE`. Debug the chunk durations: `py -3.12 -c "import sys; sys.path.insert(0,'pipeline'); from v11_assemble import probe_dur; from pathlib import Path; [print(p.name, probe_dur(p)) for p in sorted(Path('final_video/v11_work').glob('fd_*.wav'))]"`

- [ ] **Step 5: Listen to the joins**

The whole point of v11 is that joins are inaudible. Extract 2 s around each junction and listen:

Run: `cd /c/Users/avina/ytceleb && py -3.12 -c "import sys; sys.path.insert(0,'pipeline'); from v11_assemble import probe_dur, run; from pathlib import Path; t=0.0; W=Path('final_video/v11_work'); [ (run(['ffmpeg','-ss',str(max(t-1,0)),'-t','2','-i','final_video/V11_SLICE.mp4','-vn','-y',str(W/f'join_{i:02d}.wav')]), print(f'join {i} at {t:.2f}s')) for i,t in enumerate(__import__('itertools').accumulate(probe_dur(p) for p in sorted(W.glob('fd_*.wav')))) ]"`

Then verify no clipping at any join:

Run: `cd /c/Users/avina/ytceleb && for f in final_video/v11_work/join_*.wav; do echo "$f"; ffmpeg -i "$f" -af volumedetect -f null - 2>&1 | grep max_volume; done`
Expected: every `max_volume` below `0.0 dB`. A join at exactly `0.0 dB` means clipping — that is F7 bug 1 or 2 returning.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/avina/ytceleb
git add manifest/slice_cutlist.json pipeline/v11_slice.py
git commit -m "feat(v11): 3-minute slice proof with join + clipping checks"
```

---

## Definition of done

- [ ] `py -3.12 -m pytest tests/ -v` → 65 passed
- [ ] `py -3.12 pipeline/qc_v11.py manifest/slice_cutlist.json` → exit 0
- [ ] `py -3.12 pipeline/v11_slice.py` → exit 0, `V11_SLICE.mp4` exists at ~170–200 s
      (exact length depends on measured TTS run durations)
- [ ] Every join's `max_volume` is below 0.0 dB
- [ ] No media committed (`git log --stat` shows only `.py`, `.md`, `.json`)

**Deferred to the Phase 2 plan (the MrBeast film), deliberately not built here:**

- video-track assembly from the EDL — cards, cuts, J-cut picture offsets, logo
  bug, brand sting. Task 10 renders colour bars precisely because this plan is
  proving the *audio* timeline, not the picture.
- the research fleet and `story/facts.json`, and with it the spec §4.6 gate
  "every fact traced to a primary source" — that gate cannot be written before
  the artifact it validates exists.
- the cue library's actual 20–30 verified tracks (`cues.json` ships as schema
  only; `score_plan` is tested but has nothing to select from yet).
- `library/universe.json` and outro cross-linking.
