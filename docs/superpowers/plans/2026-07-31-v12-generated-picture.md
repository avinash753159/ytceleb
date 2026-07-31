# V12 Generated Picture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the picture layer for a locked 738.6s documentary audio master, generating 117 cutaway shots with Veo 3.1 Lite and cutting them frame-exactly against 17 verified real-footage sync bites.

**Architecture:** Five single-responsibility modules in `pipeline/`. `flow_doc` parses the shot-prompt document into blocks. `flow_split` is pure geometry — it turns a segment into beats and allocates integer frames. `flow_plan` joins document, EDL and bite windows into one manifest. `flow_gen` is a resumable background worker against the Gemini API. `flow_qc` gates every downloaded clip, and `flow_assemble` conforms and cuts. Timing always derives from `manifest/edl_full.json`, never from a transcript.

**Tech Stack:** Python 3.14, pytest, `google-genai` 2.14.0, ffmpeg/ffprobe, Pillow, numpy.

**Spec:** `docs/superpowers/specs/2026-07-31-v12-generated-picture-design.md`

## Global Constraints

- **Timing is derived from `manifest/edl_full.json` only.** Never a transcript, never the Doc's own timestamps.
- **Delivery: 24fps, 1920×1080.** Veo generates 1280×720; upscale at assembly.
- **Frame budget: 17,667 picture frames + 60 tail frames = 17,727 total.** Per-shot counts are integers summing to exactly 17,667.
- **Model:** `veo-3.1-lite-generate-preview`, 720p, 16:9, `duration_seconds` ∈ {4, 6, 8}.
- **Auth:** API key passed as `key=` — the `AQ.`-format key. Passing it as an OAuth bearer returns `API_KEY_SERVICE_BLOCKED`, which looks exactly like a dead key.
- **Project:** `gen-lang-client-0088838569`. Funding: $21.08 Gemini API prepay = 421 billed seconds.
- **`-stream_loop` is banned.** A clip shorter than its allocated frames is a build error, never a freeze and never a repeat.
- **No shot over 6.0s** for generated cutaways. Sync bites may exceed it.
- **Never reuse a clip or a window.** A registry throws on a second draw.
- **Rule 9 (rewritten):** any human visible in a generated shot must be consistent with Jimmy Donaldson (white man, late twenties) or unreadable as him — hands operating a prop, a crowd, a figure at distance. Nothing cast as him.
- Follow existing `pipeline/` conventions: `ROOT = Path(__file__).resolve().parents[1]`, module docstring explaining *why*, calibrated constants carrying the measurement that justifies them.
- Tests live in `tests/`, run with `python -m pytest`. `tests/conftest.py` already puts `pipeline/` on `sys.path`.

---

### Task 1: Vendor the shot-prompt document

The Doc is the source of all 59 base prompts. It must live in the repo so the pipeline is reproducible and diffable, not re-fetched from Drive on every run.

**Files:**
- Create: `dossier/mrbeast/FLOW_DOC.md`

- [ ] **Step 1: Export the Doc to the repo**

The document is Google Doc `1VoOBGxuFWpRK91JOknjxRw31gn7viSKw8Wf7jQSkzwE`. Read it with the Google Drive MCP tool `read_file_content`, take the `fileContent` field, and write it verbatim to `dossier/mrbeast/FLOW_DOC.md` as UTF-8.

- [ ] **Step 2: Verify the export is complete**

```bash
python -c "
c = open('dossier/mrbeast/FLOW_DOC.md', encoding='utf-8').read()
assert len(c) > 50000, 'truncated: %d chars' % len(c)
assert c.count('FLOW PROMPT') == 59, 'expected 59 prompts, got %d' % c.count('FLOW PROMPT')
assert 'USE THE REAL FOOTAGE' in c
print('OK  %d chars  %d prompts' % (len(c), c.count('FLOW PROMPT')))
"
```

Expected: `OK  55749 chars  59 prompts`

- [ ] **Step 3: Commit**

```bash
git add dossier/mrbeast/FLOW_DOC.md
git commit -m "docs(v12): vendor the shot-prompt document"
```

---

### Task 2: Split geometry

Pure functions, no I/O, no network. This is where frame drift is prevented, so it carries the heaviest test load in the plan.

**Files:**
- Create: `pipeline/flow_split.py`
- Test: `tests/test_flow_split.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `FPS = 24`
  - `MAX_SHOT = 6.0`
  - `@dataclass(frozen=True) class Beat: idx: int; start: float; end: float; frames: int; gen_dur: int`
  - `def gen_duration(seconds: float) -> int` — smallest legal Veo duration covering `seconds`
  - `def beat_count(dur: float) -> int`
  - `def split_segment(start: float, end: float) -> list[Beat]`
  - `def allocate_frames(total_frames: int, weights: list[float]) -> list[int]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_flow_split.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_split import (  # noqa: E402
    FPS, MAX_SHOT, Beat, allocate_frames, beat_count, gen_duration,
    split_segment,
)


def test_gen_duration_picks_smallest_legal_value():
    assert gen_duration(2.0) == 4
    assert gen_duration(4.0) == 4
    assert gen_duration(4.01) == 6
    assert gen_duration(6.0) == 6
    assert gen_duration(6.01) == 8


def test_gen_duration_rejects_over_eight():
    with pytest.raises(ValueError):
        gen_duration(8.01)


def test_short_segment_is_one_beat():
    beats = split_segment(30.80, 34.00)
    assert len(beats) == 1
    assert beats[0].gen_dur == 4


def test_no_beat_exceeds_max_shot():
    for start, end in [(2.0, 11.892), (34.0, 44.5), (100.0, 118.34)]:
        for b in split_segment(start, end):
            assert b.end - b.start <= MAX_SHOT + 1e-9


def test_beats_are_contiguous_and_cover_the_segment():
    beats = split_segment(2.0, 11.892)
    assert beats[0].start == pytest.approx(2.0)
    assert beats[-1].end == pytest.approx(11.892)
    for a, b in zip(beats, beats[1:]):
        assert a.end == pytest.approx(b.start)


def test_frames_sum_to_the_segments_own_frame_count():
    """The whole point: no drift. 130 shots once accumulated 3.8s."""
    for start, end in [(2.0, 11.892), (30.8, 34.0), (100.0, 118.34)]:
        beats = split_segment(start, end)
        assert sum(b.frames for b in beats) == round((end - start) * FPS)


def test_gen_dur_always_covers_the_beat():
    for start, end in [(2.0, 11.892), (100.0, 118.34), (0.0, 2.0)]:
        for b in split_segment(start, end):
            assert b.gen_dur >= b.end - b.start


def test_beat_indices_are_sequential_from_zero():
    beats = split_segment(100.0, 118.34)
    assert [b.idx for b in beats] == list(range(len(beats)))


def test_longest_real_segment_splits_to_four_beats():
    """18.34s is the longest generated segment in the film."""
    assert beat_count(18.34) == 4


def test_allocate_frames_sums_exactly():
    assert sum(allocate_frames(100, [1.0, 1.0, 1.0])) == 100
    assert sum(allocate_frames(17667, [1.0] * 117)) == 17667


def test_allocate_frames_distributes_remainder_not_drops_it():
    got = allocate_frames(100, [1.0, 1.0, 1.0])
    assert sorted(got) == [33, 33, 34]


def test_allocate_frames_respects_weights():
    assert allocate_frames(120, [1.0, 2.0, 3.0]) == [20, 40, 60]


def test_allocate_frames_never_returns_zero():
    got = allocate_frames(10, [1.0] * 10)
    assert all(f >= 1 for f in got)


def test_zero_length_segment_is_rejected():
    with pytest.raises(ValueError):
        split_segment(10.0, 10.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_flow_split.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow_split'`

- [ ] **Step 3: Write the implementation**

```python
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
    lost the most in the rounding.
    """
    if total_frames < len(weights):
        raise ValueError(
            f"{total_frames} frames cannot cover {len(weights)} shots")
    scale = total_frames / sum(weights)
    exact = [w * scale for w in weights]
    out = [max(1, math.floor(x)) for x in exact]
    short = total_frames - sum(out)
    order = sorted(range(len(out)), key=lambda i: exact[i] - out[i],
                   reverse=(short > 0))
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flow_split.py -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add pipeline/flow_split.py tests/test_flow_split.py
git commit -m "feat(v12): frame-exact split geometry for generated shots"
```

---

### Task 3: Parse the shot-prompt document

**Files:**
- Create: `pipeline/flow_doc.py`
- Test: `tests/test_flow_doc.py`
- Reads: `dossier/mrbeast/FLOW_DOC.md`
- Writes: `manifest/flow_doc_blocks.json`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `@dataclass(frozen=True) class DocBlock: kind: str; start: float; end: float; text: str; prompt: str; real_footage: bool; source_label: str`
  - `def parse_timestamp(s: str) -> float`
  - `def parse_doc(markdown: str) -> list[DocBlock]`
  - `def main() -> None` — writes `manifest/flow_doc_blocks.json`

`kind` is one of `lead_in`, `narration`, `bite`, `beat`, `title_break`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_flow_doc.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_doc import DocBlock, parse_doc, parse_timestamp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SAMPLE = """## **COLD OPEN**

**LEAD-IN — music only**   0:00–0:02

*FLOW PROMPT: Extreme slow push onto a single overhead work light. no text, 24fps*

**NARRATION**   0:02.00–11.89

This is the most productive person on the internet.

*FLOW PROMPT: High aerial descending over an enormous outdoor film set. 24fps*

**BITE — HIS OWN VOICE — Joe Rogan Experience \\#1788**   0:11.89–0:13.99

“I'm probably one of the least energetic people you'll ever meet.”

**USE THE REAL FOOTAGE.** Joe Rogan Experience \\#1788, around 1:27:45

**BEAT — music only**   0:30.80–0:34.00

*FLOW PROMPT: An empty running track at dawn, mist low in the lanes. 24fps*
"""


def test_parse_timestamp_handles_minutes_and_seconds():
    assert parse_timestamp("0:02.00") == pytest.approx(2.0)
    assert parse_timestamp("1:27.45") == pytest.approx(87.45)
    assert parse_timestamp("11.89") == pytest.approx(11.89)
    assert parse_timestamp("0:00") == pytest.approx(0.0)


def test_parse_doc_finds_every_block():
    blocks = parse_doc(SAMPLE)
    assert [b.kind for b in blocks] == [
        "lead_in", "narration", "bite", "beat"]


def test_lead_in_carries_its_prompt():
    b = parse_doc(SAMPLE)[0]
    assert b.start == pytest.approx(0.0)
    assert b.end == pytest.approx(2.0)
    assert "overhead work light" in b.prompt
    assert b.real_footage is False


def test_bite_is_marked_real_footage_and_has_no_prompt():
    b = parse_doc(SAMPLE)[2]
    assert b.kind == "bite"
    assert b.real_footage is True
    assert b.prompt == ""
    assert "Joe Rogan Experience" in b.source_label


def test_narration_text_is_captured_without_the_prompt():
    b = parse_doc(SAMPLE)[1]
    assert b.text.startswith("This is the most productive person")
    assert "FLOW PROMPT" not in b.text


def test_real_document_has_fiftynine_prompts():
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    blocks = parse_doc(doc)
    assert sum(1 for b in blocks if b.prompt) == 59


def test_real_document_blocks_are_in_ascending_time_order():
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    blocks = parse_doc(doc)
    for a, b in zip(blocks, blocks[1:]):
        assert a.start <= b.start, f"{a.kind}@{a.start} before {b.kind}@{b.start}"


def test_every_non_bite_block_has_a_prompt():
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    for b in parse_doc(doc):
        if not b.real_footage:
            assert b.prompt, f"{b.kind}@{b.start} has no prompt"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_flow_doc.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow_doc'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Read the shot-prompt document into structured blocks.

The document is the film's picture script: 59 prompts, one per segment of the
locked audio, plus the eight bites that have no clean Jimmy window and so need
generated picture too.

Its timestamps are NOT authoritative and are parsed only to align blocks with
the EDL. Whisper-derived timings drifted ten seconds in V7 and put baseball
footage over a silent title break; every downstream duration comes from
manifest/edl_full.json. These are used for ordering and cross-checking only.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "dossier/mrbeast/FLOW_DOC.md"
OUT = ROOT / "manifest/flow_doc_blocks.json"

# The document uses an en-dash between times and an em-dash inside headings.
DASHES = "–—-"
HEAD = re.compile(
    r"^\*\*(?P<label>[A-Z][^*]*?)\*\*\s+"
    r"(?P<t0>\d+(?::\d+)?(?:\.\d+)?)\s*[" + DASHES + r"]\s*"
    r"(?P<t1>\d+(?::\d+)?(?:\.\d+)?)\s*$",
    re.MULTILINE)
PROMPT = re.compile(r"\*FLOW PROMPT:\s*(?P<body>.+?)\*", re.DOTALL)
REAL = re.compile(r"\*\*USE THE REAL FOOTAGE\.\*\*(?P<rest>[^\n]*)")

KINDS = (
    ("LEAD-IN", "lead_in"),
    ("TITLE BREAK", "title_break"),
    ("NARRATION", "narration"),
    ("BITE", "bite"),
    ("BEAT", "beat"),
)


@dataclass(frozen=True)
class DocBlock:
    kind: str
    start: float
    end: float
    text: str
    prompt: str
    real_footage: bool
    source_label: str


def parse_timestamp(s: str) -> float:
    """'0:02.00' -> 2.0 ; '11.89' -> 11.89 ; '1:27.45' -> 87.45"""
    s = s.strip()
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m) * 60 + float(sec)
    return float(s)


def _kind_of(label: str) -> str:
    up = label.upper()
    for needle, kind in KINDS:
        if up.startswith(needle):
            return kind
    return "narration"


def parse_doc(markdown: str) -> list[DocBlock]:
    heads = list(HEAD.finditer(markdown))
    blocks: list[DocBlock] = []
    for i, h in enumerate(heads):
        body = markdown[h.end():heads[i + 1].start() if i + 1 < len(heads)
                        else len(markdown)]
        pm = PROMPT.search(body)
        rm = REAL.search(body)
        text = PROMPT.sub("", REAL.sub("", body))
        # Strip the empty reference-image table the document carries.
        text = re.sub(r"^\|.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^references only.*$", "", text, flags=re.MULTILINE)
        blocks.append(DocBlock(
            kind=_kind_of(h.group("label")),
            start=parse_timestamp(h.group("t0")),
            end=parse_timestamp(h.group("t1")),
            text=" ".join(text.split()),
            prompt=" ".join(pm.group("body").split()) if pm else "",
            real_footage=bool(rm),
            source_label=" ".join(h.group("label").split()),
        ))
    return blocks


def main() -> None:
    blocks = parse_doc(DOC.read_text(encoding="utf-8"))
    OUT.write_text(json.dumps([asdict(b) for b in blocks], indent=1),
                   encoding="utf-8")
    prompts = sum(1 for b in blocks if b.prompt)
    real = sum(1 for b in blocks if b.real_footage)
    print(f"{len(blocks)} blocks  {prompts} prompts  {real} real-footage")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flow_doc.py -v`
Expected: PASS, 8 tests

If `test_real_document_has_fiftynine_prompts` fails, the regexes need adjusting to the document's actual punctuation — inspect with `python -c "import re; print(open('dossier/mrbeast/FLOW_DOC.md',encoding='utf-8').read()[:2000])"` and fix the pattern. Do not change the assertion; 59 is the known count.

- [ ] **Step 5: Generate the manifest and commit**

```bash
python pipeline/flow_doc.py
git add pipeline/flow_doc.py tests/test_flow_doc.py manifest/flow_doc_blocks.json
git commit -m "feat(v12): parse the shot-prompt document into blocks"
```

---

### Task 4: Build the shot manifest

Joins the EDL (authoritative timing), the document blocks (prompts), and `bite_windows.json` (which bites can be sync) into the single source of truth for everything downstream.

**Files:**
- Create: `pipeline/flow_plan.py`
- Test: `tests/test_flow_plan.py`
- Reads: `manifest/edl_full.json`, `manifest/flow_doc_blocks.json`, `manifest/bite_windows.json`
- Writes: `manifest/flow_shots.json`

**Interfaces:**
- Consumes: `flow_split.split_segment`, `flow_split.FPS`, `flow_doc.DocBlock`
- Produces:
  - `def sync_capable(bite: dict) -> bool`
  - `def build_shots() -> list[dict]`
  - `def main() -> None`
  - Each shot dict: `{"shot_id": str, "seg_i": int, "seg_id": str, "kind": str, "start": float, "end": float, "frames": int, "gen_dur": int, "beat_idx": int, "beat_of": int, "prompt": str, "narration": str, "source": str, "status": "pending"}`
  - `kind` ∈ `"gen"` (generate) or `"sync"` (real footage).
  - `shot_id` is `f"s{seg_i:03d}{chr(97 + beat_idx)}"`, e.g. `s000a`, `s000b`. The lead-in is `s_lead`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_flow_plan.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_plan import build_shots, sync_capable  # noqa: E402
from flow_split import FPS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PICTURE_FRAMES = 17667      # round(736.107 * 24)


@pytest.fixture(scope="module")
def shots():
    return build_shots()


def test_sync_capable_requires_a_verified_untexted_run():
    assert sync_capable({"sync_possible": True, "runs": [
        {"verified_jimmy": True, "has_text": False}]}) is True
    assert sync_capable({"sync_possible": True, "runs": [
        {"verified_jimmy": True, "has_text": True}]}) is False
    assert sync_capable({"sync_possible": False, "runs": [
        {"verified_jimmy": True, "has_text": False}]}) is False
    assert sync_capable({"sync_possible": True, "runs": []}) is False


def test_seventeen_bites_are_sync(shots):
    assert sum(1 for s in shots if s["kind"] == "sync") == 17


def test_one_hundred_seventeen_shots_are_generated(shots):
    assert sum(1 for s in shots if s["kind"] == "gen") == 117


def test_frames_sum_to_the_picture_budget(shots):
    assert sum(s["frames"] for s in shots) == PICTURE_FRAMES


def test_shots_are_contiguous_with_no_gaps_or_overlaps(shots):
    for a, b in zip(shots, shots[1:]):
        assert a["end"] == pytest.approx(b["start"], abs=1e-6)


def test_timeline_starts_at_zero_and_ends_at_the_edl_end(shots):
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(
        encoding="utf-8"))
    assert shots[0]["start"] == pytest.approx(0.0)
    assert shots[-1]["end"] == pytest.approx(edl["end"], abs=1e-6)


def test_no_generated_shot_exceeds_six_seconds(shots):
    for s in shots:
        if s["kind"] == "gen":
            assert s["end"] - s["start"] <= 6.0 + 1e-9, s["shot_id"]


def test_every_generated_shot_has_a_prompt(shots):
    for s in shots:
        if s["kind"] == "gen":
            assert s["prompt"].strip(), s["shot_id"]


def test_shot_ids_are_unique(shots):
    ids = [s["shot_id"] for s in shots]
    assert len(ids) == len(set(ids))


def test_gen_dur_covers_every_generated_shot(shots):
    for s in shots:
        if s["kind"] == "gen":
            assert s["gen_dur"] >= s["end"] - s["start"], s["shot_id"]


def test_billed_seconds_match_the_budget(shots):
    billed = sum(s["gen_dur"] for s in shots if s["kind"] == "gen")
    assert billed == 664


def test_sync_shots_carry_their_source_id(shots):
    for s in shots:
        if s["kind"] == "sync":
            assert s["source"], s["shot_id"]


def test_sync_shots_carry_the_timecode_to_cut_from(shots):
    """Without src_t0 the assembler renders every sync shot from t=0 of a
    two-hour podcast instead of the moment he says the line."""
    for s in shots:
        if s["kind"] == "sync":
            assert s.get("src_t0", 0) > 0, s["shot_id"]


def test_best_run_prefers_the_longest_usable_window():
    from flow_plan import best_run
    bite = {"sync_possible": True, "runs": [
        {"key": "a@1", "t0": 1.0, "usable": 2.8,
         "verified_jimmy": True, "has_text": False},
        {"key": "a@9", "t0": 9.0, "usable": 5.1,
         "verified_jimmy": True, "has_text": False},
        {"key": "a@4", "t0": 4.0, "usable": 9.9,
         "verified_jimmy": True, "has_text": True},
    ]}
    assert best_run(bite)["key"] == "a@9"


def test_best_run_returns_none_when_nothing_is_verified():
    from flow_plan import best_run
    assert best_run({"sync_possible": True, "runs": [
        {"key": "a@1", "t0": 1.0, "usable": 9.0,
         "verified_jimmy": False, "has_text": False}]}) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_flow_plan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow_plan'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Join the EDL, the prompt document and the bite windows into one manifest.

manifest/flow_shots.json is the single source of truth for the picture layer:
what is generated, what is real footage, where each shot sits on the timeline,
and how many frames it owns.

The sync split is derived, not asserted. A bite keeps the real man on screen
when bite_windows.json shows it has at least one run that is verified_jimmy
and carries no burned-in text. Exactly 17 of 25 qualify. The other 8 are six
from Airrack's video, where twelve frame-checked windows contained no
Jimmy-only frame, and two from Rogan, where the Crohn's & Colitis Foundation
site sits on a studio monitor behind him.

That reverses the KEEP_SYNC policy in picture_plan_v8.py, which cut his face
to ten bites. The reason for cutting away was that the alternative was bad
stock footage; generated cutaways remove that reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from flow_split import FPS, split_segment

ROOT = Path(__file__).resolve().parents[1]
EDL = ROOT / "manifest/edl_full.json"
BLOCKS = ROOT / "manifest/flow_doc_blocks.json"
BITES = ROOT / "manifest/bite_windows.json"
OUT = ROOT / "manifest/flow_shots.json"

GEN_KINDS = {"narr", "beat", "card"}


def sync_capable(bite: dict) -> bool:
    """True when this bite can show the real man saying the real words."""
    return best_run(bite) is not None


def best_run(bite: dict) -> dict | None:
    """The longest verified, text-free run inside this bite's own span.

    Verdicts are keyed by sid@t0, never by sheet index: verify_pool.py once
    hard-coded tile indices, so adding a source re-sorted the thumbnails and
    silently re-pointed every verdict at a different frame.
    """
    if not bite.get("sync_possible"):
        return None
    ok = [r for r in bite.get("runs", [])
          if r.get("verified_jimmy") and not r.get("has_text")]
    return max(ok, key=lambda r: r.get("usable", 0.0)) if ok else None


def _prompt_for(blocks: list[dict], start: float, end: float) -> str:
    """The document block whose span best overlaps [start, end)."""
    best, score = "", 0.0
    for b in blocks:
        if not b["prompt"]:
            continue
        ov = min(end, b["end"]) - max(start, b["start"])
        if ov > score:
            best, score = b["prompt"], ov
    return best


def build_shots() -> list[dict]:
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    blocks = json.loads(BLOCKS.read_text(encoding="utf-8"))
    bites = {b["i"]: b for b in json.loads(BITES.read_text(encoding="utf-8"))}

    shots: list[dict] = []

    # The lead-in: 0 -> first segment, music only, generated.
    lead_end = edl["segs"][0]["start"]
    for b in split_segment(0.0, lead_end):
        shots.append({
            "shot_id": "s_lead", "seg_i": -1, "seg_id": "lead_in",
            "kind": "gen", "start": b.start, "end": b.end,
            "frames": b.frames, "gen_dur": b.gen_dur,
            "beat_idx": b.idx, "beat_of": 1,
            "prompt": _prompt_for(blocks, 0.0, lead_end),
            "narration": "", "source": "", "status": "pending",
        })

    for seg in edl["segs"]:
        i, kind = seg["i"], seg["kind"]
        bite = bites.get(i)
        is_sync = kind == "bite" and bite is not None and sync_capable(bite)

        if is_sync:
            run = best_run(bite)
            shots.append({
                "shot_id": f"s{i:03d}s", "seg_i": i, "seg_id": seg["seg_id"],
                "kind": "sync", "start": seg["start"], "end": seg["end"],
                "frames": round((seg["end"] - seg["start"]) * FPS),
                "gen_dur": 0, "beat_idx": 0, "beat_of": 1,
                "prompt": "", "narration": seg["text"],
                "source": seg["source"],
                # Where in the interview to cut from. Without this the
                # assembler renders every sync shot from t=0 of the source.
                "src_t0": run["t0"], "src_run_key": run["key"],
                "status": "pending",
            })
            continue

        if kind not in GEN_KINDS and not (kind == "bite" and not is_sync):
            continue

        beats = split_segment(seg["start"], seg["end"])
        prompt = _prompt_for(blocks, seg["start"], seg["end"])
        for b in beats:
            shots.append({
                "shot_id": f"s{i:03d}{chr(97 + b.idx)}",
                "seg_i": i, "seg_id": seg["seg_id"], "kind": "gen",
                "start": b.start, "end": b.end, "frames": b.frames,
                "gen_dur": b.gen_dur, "beat_idx": b.idx,
                "beat_of": len(beats), "prompt": prompt,
                "narration": seg["text"], "source": "", "status": "pending",
            })

    # Frames were allocated per segment; make the film total exact.
    total = sum(s["frames"] for s in shots)
    want = round(edl["end"] * FPS)
    if total != want:
        raise SystemExit(f"frame budget {total} != {want}; refusing to pad")
    return shots


def main() -> None:
    shots = build_shots()
    OUT.write_text(json.dumps(shots, indent=1), encoding="utf-8")
    gen = [s for s in shots if s["kind"] == "gen"]
    billed = sum(s["gen_dur"] for s in gen)
    print(f"{len(shots)} shots  {len(gen)} generated  "
          f"{len(shots) - len(gen)} sync  "
          f"{sum(s['frames'] for s in shots)} frames  "
          f"{billed}s billed  ${billed * 0.05:.2f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flow_plan.py -v`
Expected: PASS, 15 tests

At this point every beat of a split segment inherits the same segment-level prompt, so three sibling shots would generate three near-identical images. That is not yet a test failure — the prompts are non-empty — and Task 5 replaces them with authored per-beat prompts and adds the test that catches the duplication.

- [ ] **Step 5: Generate the manifest and commit**

```bash
python pipeline/flow_plan.py
git add pipeline/flow_plan.py tests/test_flow_plan.py manifest/flow_shots.json
git commit -m "feat(v12): build the 134-entry shot manifest from EDL + prompts"
```

---

### Task 5: Author the per-beat prompts

**This is the task that decides whether the film works.** Code cannot write these; they are prose. 68 shots inherit a segment-level prompt shared with their siblings, and each needs its own.

**Files:**
- Create: `manifest/flow_beat_prompts.json`
- Modify: `pipeline/flow_plan.py` — prefer a per-beat prompt when one exists
- Test: `tests/test_flow_plan.py` — add the coverage assertion

**Interfaces:**
- Consumes: `manifest/flow_shots.json` from Task 4.
- Produces: `manifest/flow_beat_prompts.json` — `{shot_id: prompt_text}`.

- [ ] **Step 1: List the shots needing an authored prompt**

```bash
python -c "
import json
s=json.load(open('manifest/flow_shots.json',encoding='utf-8'))
need=[x for x in s if x['kind']=='gen' and x['beat_of']>1]
print('%d shots need authored prompts' % len(need))
for x in need[:5]:
    print(' %-7s %6.2f-%6.2f (%.2fs) beat %d/%d  %s' % (
        x['shot_id'], x['start'], x['end'], x['end']-x['start'],
        x['beat_idx']+1, x['beat_of'], x['narration'][:56]))
"
```

- [ ] **Step 2: Write the prompts**

For each shot with `beat_of > 1`, write one prompt. Rules, all from the spec:

1. **Split the sentence, not the image.** A 9.89s segment holds two or three clauses; give each beat the clause it sits under. Beat A of "Three hundred million subscribers. Videos that cost more than films." shows scale; beat B shows cost.
2. **Every prompt ends with the shared style tail**, verbatim: *cinematic, shot on anamorphic lenses, shallow depth of field, near-black shadows, muted desaturated palette with deep red as the only warm accent, slow deliberate camera move, volumetric haze, no text, no logos, no recognisable faces, 24fps*
3. **Rule 9 (rewritten).** Any visible human must be consistent with Jimmy Donaldson — white man, late twenties — or unreadable as him. No stand-in body, no silhouette training, no child playing baseball, no legs walking.
4. **Where the line states a fact, show the fact.** Where it is interpretation, use a metaphor that resolves in about a second.
5. **No narration echo.** The picture must not restate the words. The script says "Normal" and "Crohn's Disease" over the mechanism plate; a prompt that renders those words on screen is a double failure.
6. Medical beats use the medical tail instead: *photoreal medical visualisation, macro, wet biological surfaces, near-black surround, deep red and raw pink as the only saturated colours, slow deliberate camera move, shallow depth of field, no text, no labels, no logos, 24fps*

Write to `manifest/flow_beat_prompts.json` as `{"s000a": "...", "s000b": "...", ...}`.

- [ ] **Step 3: Wire per-beat prompts into the planner**

In `pipeline/flow_plan.py`, add near the other path constants:

```python
BEAT_PROMPTS = ROOT / "manifest/flow_beat_prompts.json"
```

and inside `build_shots`, after `blocks` is loaded:

```python
    beat_prompts = (json.loads(BEAT_PROMPTS.read_text(encoding="utf-8"))
                    if BEAT_PROMPTS.exists() else {})
```

then in the generated-shot loop replace `"prompt": prompt,` with:

```python
                "prompt": beat_prompts.get(
                    f"s{i:03d}{chr(97 + b.idx)}", prompt),
```

- [ ] **Step 4: Add the coverage test**

```python
def test_every_split_beat_has_its_own_authored_prompt(shots):
    """A shared prompt across siblings means three identical shots."""
    seen = {}
    for s in shots:
        if s["kind"] != "gen" or s["beat_of"] == 1:
            continue
        key = (s["seg_i"], s["prompt"])
        seen[key] = seen.get(key, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    assert not dupes, f"segments with repeated prompts: {sorted(dupes)}"
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_flow_plan.py -v`
Expected: PASS, 16 tests

- [ ] **Step 6: Regenerate and commit**

```bash
python pipeline/flow_plan.py
git add manifest/flow_beat_prompts.json manifest/flow_shots.json pipeline/flow_plan.py tests/test_flow_plan.py
git commit -m "feat(v12): author per-beat prompts for split segments"
```

- [ ] **Step 7: OWNER REVIEW GATE — STOP HERE**

Produce a readable prompt list and hand it to the owner:

```bash
python -c "
import json
s=json.load(open('manifest/flow_shots.json',encoding='utf-8'))
for x in s:
    if x['kind']!='gen': continue
    print('%-7s %7.2f-%7.2f  %.2fs  gen%ds' % (
        x['shot_id'], x['start'], x['end'], x['end']-x['start'], x['gen_dur']))
    if x['narration']: print('   LINE: %s' % x['narration'][:100])
    print('   SHOT: %s' % x['prompt'])
    print()
" > dossier/mrbeast/V12_PROMPTS.txt
```

**Do not generate anything until the owner has read `dossier/mrbeast/V12_PROMPTS.txt` and approved it.** The prompts are the film. If they are wrong, no amount of clean pipeline saves it.

---

### Task 6: Veo generation worker

**Files:**
- Create: `pipeline/flow_gen.py`
- Test: `tests/test_flow_gen.py`
- Reads: `manifest/flow_shots.json`
- Writes: `library/veo/<shot_id>.mp4`, `manifest/flow_gen_status.json`

**Interfaces:**
- Consumes: `manifest/flow_shots.json`.
- Produces:
  - `MODEL = "veo-3.1-lite-generate-preview"`, `RATE_PER_SECOND = 0.05`
  - `def load_key() -> str`
  - `def estimate_cost(shots: list[dict]) -> float`
  - `def pending(shots: list[dict], status: dict) -> list[dict]`
  - `def record(status_path: Path, shot_id: str, **fields) -> None` — atomic write
  - `def generate_one(client, shot: dict, out_dir: Path) -> Path`
  - `def main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Confirm the installed SDK's actual call shape**

Do not write against a remembered API. Introspect what is installed:

```bash
python -c "
from google.genai import types
import inspect
print([f for f in types.GenerateVideosConfig.model_fields])
print(inspect.signature(__import__('google.genai',fromlist=['Client']).Client().models.generate_videos))
"
```

Record the real field names. The code below assumes `aspect_ratio`, `resolution`, `duration_seconds`, `number_of_videos`; **adjust to whatever the introspection prints.**

- [ ] **Step 2: Write the failing tests**

These test budget, resumability and status handling — never the network.

```python
# tests/test_flow_gen.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_gen import (  # noqa: E402
    RATE_PER_SECOND, estimate_cost, pending, record,
)


def mk(shot_id, gen_dur=6, kind="gen"):
    return {"shot_id": shot_id, "gen_dur": gen_dur, "kind": kind}


def test_estimate_cost_counts_only_generated_shots():
    shots = [mk("a", 6), mk("b", 4), mk("c", 0, kind="sync")]
    assert estimate_cost(shots) == pytest.approx(10 * RATE_PER_SECOND)


def test_estimate_cost_of_the_full_film():
    assert estimate_cost([mk(str(i), 6) for i in range(100)]) == pytest.approx(30.0)


def test_pending_skips_completed_shots():
    shots = [mk("a"), mk("b"), mk("c")]
    status = {"a": {"state": "done"}, "b": {"state": "failed"}}
    assert [s["shot_id"] for s in pending(shots, status)] == ["b", "c"]


def test_pending_skips_sync_shots():
    shots = [mk("a"), mk("b", kind="sync")]
    assert [s["shot_id"] for s in pending(shots, {})] == ["a"]


def test_record_is_atomic_and_readable(tmp_path):
    p = tmp_path / "status.json"
    record(p, "s000a", state="done", path="x.mp4")
    record(p, "s000b", state="failed", error="boom")
    got = json.loads(p.read_text(encoding="utf-8"))
    assert got["s000a"]["state"] == "done"
    assert got["s000b"]["error"] == "boom"


def test_record_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "status.json"
    record(p, "s000a", state="done")
    assert [f.name for f in tmp_path.iterdir()] == ["status.json"]


def test_record_preserves_earlier_entries(tmp_path):
    p = tmp_path / "status.json"
    for i in range(5):
        record(p, f"s{i:03d}", state="done")
    assert len(json.loads(p.read_text(encoding="utf-8"))) == 5
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_flow_gen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow_gen'`

- [ ] **Step 4: Write the implementation**

```python
#!/usr/bin/env python3
"""Generate the picture layer with Veo, in the background, resumably.

Runs as a detached worker: it submits a shot, polls its long-running
operation, downloads the mp4, and records the result before moving on. Kill it
and restart it and it resumes - status is written atomically after every shot,
so a killed run never loses more than the shot in flight.

The spend cap STOPS SUBMISSION rather than warning. Funding is a $21.08
prepay against a $33.20 full pass, so an unattended runaway would exhaust the
balance before anyone looked.

The API key goes in `key=`. Passing this AQ.-format key as an OAuth bearer
returns API_KEY_SERVICE_BLOCKED, which reads exactly like a revoked key and
cost an hour of debugging once already.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/flow_shots.json"
STATUS = ROOT / "manifest/flow_gen_status.json"
OUTDIR = ROOT / "library/veo"
KEYFILE = ROOT / ".veo_key"

MODEL = "veo-3.1-lite-generate-preview"
RESOLUTION = "720p"
ASPECT = "16:9"
RATE_PER_SECOND = 0.05        # Veo 3.1 Lite, 720p
DEFAULT_CAP = 20.00           # dollars; below the $21.08 prepay on purpose
POLL_SECONDS = 10
MAX_POLL = 360                # an hour before a shot is called stuck
RETRIES = 2


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key and KEYFILE.exists():
        key = KEYFILE.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit(
            "No API key. Put it in .veo_key or set GEMINI_API_KEY.")
    return key


def estimate_cost(shots: list[dict]) -> float:
    return sum(s["gen_dur"] for s in shots
               if s.get("kind") == "gen") * RATE_PER_SECOND


def pending(shots: list[dict], status: dict) -> list[dict]:
    return [s for s in shots
            if s.get("kind") == "gen"
            and status.get(s["shot_id"], {}).get("state") != "done"]


def record(status_path: Path, shot_id: str, **fields) -> None:
    """Atomic status write - a killed run must not corrupt the ledger."""
    cur = {}
    if status_path.exists():
        cur = json.loads(status_path.read_text(encoding="utf-8"))
    cur[shot_id] = fields
    tmp = status_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    tmp.replace(status_path)


def generate_one(client, shot: dict, out_dir: Path) -> Path:
    """Submit one shot, poll to completion, download. Raises on failure."""
    from google.genai import types

    op = client.models.generate_videos(
        model=MODEL,
        prompt=shot["prompt"],
        config=types.GenerateVideosConfig(
            aspect_ratio=ASPECT,
            resolution=RESOLUTION,
            duration_seconds=shot["gen_dur"],
            number_of_videos=1,
        ),
    )
    for _ in range(MAX_POLL):
        if op.done:
            break
        time.sleep(POLL_SECONDS)
        op = client.operations.get(op)
    else:
        raise TimeoutError(f"{shot['shot_id']} still running after "
                           f"{MAX_POLL * POLL_SECONDS}s")

    if getattr(op, "error", None):
        raise RuntimeError(f"{shot['shot_id']}: {op.error}")

    vids = op.response.generated_videos
    if not vids:
        raise RuntimeError(f"{shot['shot_id']}: no video returned")

    dest = out_dir / f"{shot['shot_id']}.mp4"
    client.files.download(file=vids[0].video)
    vids[0].video.save(str(dest))
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"{shot['shot_id']}: empty download")
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cap", type=float, default=DEFAULT_CAP,
                    help="hard dollar ceiling; submission stops at it")
    ap.add_argument("--only", nargs="*", default=None,
                    help="generate only these shot_ids")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    status = (json.loads(STATUS.read_text(encoding="utf-8"))
              if STATUS.exists() else {})
    todo = pending(shots, status)
    if args.only:
        todo = [s for s in todo if s["shot_id"] in set(args.only)]

    print(f"{len(todo)} shots pending  "
          f"est ${estimate_cost(todo):.2f}  cap ${args.cap:.2f}")
    if args.dry_run:
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    from google import genai
    client = genai.Client(api_key=load_key())

    spent = 0.0
    for i, shot in enumerate(todo, 1):
        cost = shot["gen_dur"] * RATE_PER_SECOND
        if spent + cost > args.cap:
            print(f"STOP: cap ${args.cap:.2f} reached "
                  f"(spent ${spent:.2f}); {len(todo) - i + 1} shots left")
            break
        for attempt in range(RETRIES + 1):
            try:
                dest = generate_one(client, shot, OUTDIR)
                spent += cost
                record(STATUS, shot["shot_id"], state="done",
                       path=str(dest.relative_to(ROOT)), cost=cost)
                print(f"[{i}/{len(todo)}] {shot['shot_id']} "
                      f"{shot['gen_dur']}s  ${spent:.2f}")
                break
            except Exception as exc:            # noqa: BLE001
                if attempt == RETRIES:
                    record(STATUS, shot["shot_id"], state="failed",
                           error=str(exc)[:300])
                    print(f"[{i}/{len(todo)}] {shot['shot_id']} FAILED: "
                          f"{str(exc)[:120]}")
                else:
                    time.sleep(5 * (attempt + 1))
    print(f"spent ${spent:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_flow_gen.py -v`
Expected: PASS, 7 tests

- [ ] **Step 6: Verify the dry run reports the right budget**

```bash
python pipeline/flow_gen.py --dry-run
```
Expected: `117 shots pending  est $33.20  cap $20.00`

- [ ] **Step 7: Commit**

```bash
git add pipeline/flow_gen.py tests/test_flow_gen.py
git commit -m "feat(v12): resumable Veo worker with a hard spend cap"
```

---

### Task 7: Three-shot proof

The first money spent. **$0.80.**

**Files:**
- Create: `work/v12_proof/` (output only, not committed)

- [ ] **Step 1: Store the API key**

```bash
python -c "
from pathlib import Path
Path('.veo_key').write_text(input('paste the AQ. key: ').strip(), encoding='utf-8')
print('stored')
"
echo ".veo_key" >> .gitignore
```

- [ ] **Step 2: Pick the three shots**

One 4s beat, one 6s beat, and one beat from the film's longest segment:

```bash
python -c "
import json
s=[x for x in json.load(open('manifest/flow_shots.json',encoding='utf-8'))
   if x['kind']=='gen']
four=next(x for x in s if x['gen_dur']==4)
six=next(x for x in s if x['gen_dur']==6)
longest=max(s, key=lambda x: x['beat_of'])
print(four['shot_id'], six['shot_id'], longest['shot_id'])
"
```

- [ ] **Step 3: Generate them, capped at $2**

```bash
python pipeline/flow_gen.py --cap 2.00 --only <id1> <id2> <id3>
```
Expected: three `done` lines, total under $1.00.

- [ ] **Step 4: Verify what actually came back**

```bash
for f in library/veo/*.mp4; do
  echo -n "$f  "
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate,nb_frames \
    -of csv=p=0 "$f"
done
```
Expected: `1280,720,24/1,<frames>` for each. **If the frame rate is not 24, stop and re-plan the assembly conform** — the whole 24fps delivery decision rests on Veo being natively 24.

- [ ] **Step 5: Cut them against the real audio at their real timecodes**

```bash
python -c "
import json, subprocess, sys
from pathlib import Path
shots = {s['shot_id']: s for s in json.load(open('manifest/flow_shots.json', encoding='utf-8'))}
ids = sys.argv[1:]
Path('work/v12_proof').mkdir(parents=True, exist_ok=True)
for sid in ids:
    s = shots[sid]
    subprocess.run(['ffmpeg','-y','-v','error',
        '-i', f'library/veo/{sid}.mp4',
        '-ss', str(s['start']), '-t', str(s['end']-s['start']),
        '-i', 'final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav',
        '-map','0:v','-map','1:a','-frames:v', str(s['frames']),
        '-vf','scale=1920:1080:flags=lanczos','-r','24',
        '-c:v','libx264','-crf','18','-preset','fast','-c:a','aac','-shortest',
        f'work/v12_proof/{sid}.mp4'], check=True)
    print(sid, s['start'], '->', s['end'], s['frames'], 'frames')
" <id1> <id2> <id3>
```

- [ ] **Step 6: OWNER REVIEW GATE — STOP HERE**

Send the three clips. The owner decides whether generated picture solves this film before another dollar is spent. **Do not proceed to a full pass without an explicit yes.**

---

### Task 8: QC gates

**Files:**
- Create: `pipeline/flow_qc.py`
- Test: `tests/test_flow_qc.py`
- Writes: `manifest/flow_qc.json`

**Interfaces:**
- Consumes: `library/veo/<shot_id>.mp4`, `manifest/flow_shots.json`
- Produces:
  - `def probe(path: Path) -> dict` — width, height, fps, frames, duration
  - `def gate_format(shot: dict, meta: dict) -> str | None`
  - `def gate_black(path: Path) -> str | None`
  - `def gate_static(path: Path) -> str | None`
  - `def dhash(img) -> int` — 17×16, 256-bit
  - `def gate_duplicate(hashes: dict[str, int], shot_id: str, h: int) -> str | None`
  - `def qc_all() -> dict` — `{shot_id: [reasons]}`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_flow_qc.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from flow_qc import (  # noqa: E402
    DUPE_BITS, gate_duplicate, gate_format, hamming,
)


def test_gate_format_accepts_a_correct_clip():
    shot = {"shot_id": "s000a", "frames": 120, "gen_dur": 6}
    meta = {"width": 1280, "height": 720, "fps": 24.0, "frames": 144}
    assert gate_format(shot, meta) is None


def test_gate_format_rejects_a_clip_shorter_than_its_allocation():
    """A short clip is an error. It is never padded and never looped."""
    shot = {"shot_id": "s000a", "frames": 200, "gen_dur": 6}
    meta = {"width": 1280, "height": 720, "fps": 24.0, "frames": 144}
    assert "short" in gate_format(shot, meta)


def test_gate_format_rejects_wrong_resolution():
    shot = {"shot_id": "s000a", "frames": 100, "gen_dur": 6}
    meta = {"width": 640, "height": 360, "fps": 24.0, "frames": 144}
    assert "resolution" in gate_format(shot, meta)


def test_gate_format_rejects_wrong_frame_rate():
    shot = {"shot_id": "s000a", "frames": 100, "gen_dur": 6}
    meta = {"width": 1280, "height": 720, "fps": 30.0, "frames": 180}
    assert "fps" in gate_format(shot, meta)


def test_hamming_counts_differing_bits():
    assert hamming(0b1010, 0b1010) == 0
    assert hamming(0b1010, 0b1011) == 1
    assert hamming(0b0000, 0b1111) == 4


def test_gate_duplicate_flags_a_near_identical_shot():
    """256-bit dHash. 64-bit has no usable separation on this material:
    the closest distinct same-interview pair is 9 bits while cross-interview
    pairs go as low as 7."""
    existing = {"s000a": 0}
    assert gate_duplicate(existing, "s001a", 0) is not None


def test_gate_duplicate_passes_a_distinct_shot():
    existing = {"s000a": 0}
    far = (1 << (DUPE_BITS + 5)) - 1
    assert gate_duplicate(existing, "s001a", far) is None


def test_gate_duplicate_never_compares_a_shot_to_itself():
    existing = {"s000a": 12345}
    assert gate_duplicate(existing, "s000a", 12345) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_flow_qc.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow_qc'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Gate every generated clip before it is allowed onto the timeline.

Generation removes two whole defect classes - there is no Pexels watermark in
a generated frame and no stranger wandering into shot - but it adds its own.
Veo invents signage and gibberish lettering despite being told not to, and it
will happily produce a person who reads as a stand-in for the subject.

Thresholds here are calibrated, not guessed. Three times in one session an
intuition-picked threshold silently destroyed real data: a flat-frame filter
at luma std < 14 rejected every usable frame in the film, because the Rogan
studio is a red curtain. Pick the metric that separates the populations, then
put the threshold in the gap.

The 17x16 dHash is one of those. A 64-bit 9x8 dHash has NO usable separation
on this material - the closest genuinely distinct same-interview pair is 9
bits apart while cross-interview pairs go as low as 7. At 256 bits they
separate: same-set from 17, cross-set from 59.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/flow_shots.json"
VEO = ROOT / "library/veo"
OUT = ROOT / "manifest/flow_qc.json"

EXPECT_W, EXPECT_H, EXPECT_FPS = 1280, 720, 24.0
# Measured over 877 same-set and 600 cross-set pairs by work/_hash_calib.py.
DUPE_BITS = 24
# freezedetect at -60dB fires on a slow Ken Burns; measure pixel delta. A card
# on flat dark ground needs ~34% push to register, a photograph needs 12%.
STATIC_DELTA = 0.8
BLACK_LUMA = 6.0


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    # ffprobe returns "70," with a trailing comma for some files, so an
    # isdigit() test reports 0 frames for a good piece. Parse the integer.
    raw = str(st.get("nb_frames", "0"))
    digits = "".join(c for c in raw if c.isdigit()) or "0"
    return {"width": st["width"], "height": st["height"],
            "fps": float(num) / float(den), "frames": int(digits)}


def gate_format(shot: dict, meta: dict) -> str | None:
    if (meta["width"], meta["height"]) != (EXPECT_W, EXPECT_H):
        return f"resolution {meta['width']}x{meta['height']}"
    if abs(meta["fps"] - EXPECT_FPS) > 0.05:
        return f"fps {meta['fps']:.2f}"
    if meta["frames"] < shot["frames"]:
        return (f"short: {meta['frames']} frames for a "
                f"{shot['frames']}-frame slot")
    return None


def _frames(path: Path, n: int = 6) -> list[np.ndarray]:
    """`n` frames spread evenly across the clip, as greyscale arrays.

    Sampled by seeking to computed timestamps rather than with an fps filter:
    a clip is 4-8 seconds, so an fps rate low enough to yield n frames rounds
    badly and can return one frame or none. Cached per clip, because a gap in
    a PNG sequence makes ffmpeg's image2 demuxer stop dead.
    """
    work = ROOT / "work/flow_qc" / path.stem
    work.mkdir(parents=True, exist_ok=True)
    meta = probe(path)
    dur = meta["frames"] / meta["fps"] if meta["fps"] else 0.0
    out = []
    for i in range(n):
        # Inset from both ends; the last frame of a generated clip is often
        # a fade and reads as black.
        t = dur * (i + 0.5) / n
        png = work / f"f{i:02d}.png"
        if not png.exists():
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}",
                 "-i", str(path), "-frames:v", "1", str(png)], check=True)
        if png.exists():
            out.append(np.asarray(Image.open(png).convert("L"),
                                  dtype=np.float64))
    return out


def gate_black(path: Path) -> str | None:
    fs = _frames(path)
    if fs and max(f.mean() for f in fs) < BLACK_LUMA:
        return "black"
    return None


def gate_static(path: Path) -> str | None:
    fs = _frames(path)
    if len(fs) < 2:
        return None
    deltas = [float(np.abs(b - a).mean()) for a, b in zip(fs, fs[1:])]
    if max(deltas) < STATIC_DELTA:
        return f"static (max delta {max(deltas):.2f})"
    return None


def dhash(img: np.ndarray) -> int:
    """17x16 -> 256 bits."""
    small = np.asarray(
        Image.fromarray(img.astype(np.uint8)).resize((17, 16), Image.LANCZOS),
        dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    out = 0
    for b in bits:
        out = (out << 1) | int(b)
    return out


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def gate_duplicate(hashes: dict[str, int], shot_id: str,
                   h: int) -> str | None:
    for other, oh in hashes.items():
        if other == shot_id:
            continue
        d = hamming(h, oh)
        if d < DUPE_BITS:
            return f"duplicate of {other} ({d} bits)"
    return None


def qc_all() -> dict:
    shots = {s["shot_id"]: s
             for s in json.loads(SHOTS.read_text(encoding="utf-8"))
             if s["kind"] == "gen"}
    results: dict[str, list[str]] = {}
    hashes: dict[str, int] = {}
    for sid, shot in shots.items():
        path = VEO / f"{sid}.mp4"
        if not path.exists():
            continue
        reasons = []
        meta = probe(path)
        for r in (gate_format(shot, meta), gate_black(path),
                  gate_static(path)):
            if r:
                reasons.append(r)
        fs = _frames(path, 1)
        if fs:
            h = dhash(fs[0])
            dup = gate_duplicate(hashes, sid, h)
            if dup:
                reasons.append(dup)
            hashes[sid] = h
        results[sid] = reasons
    return results


def main() -> None:
    res = qc_all()
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    bad = {k: v for k, v in res.items() if v}
    print(f"{len(res)} clips checked, {len(bad)} flagged")
    for k, v in sorted(bad.items()):
        print(f"  {k}: {'; '.join(v)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flow_qc.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Run QC over the proof clips**

```bash
python pipeline/flow_qc.py
```
Expected: `3 clips checked, 0 flagged`

- [ ] **Step 6: Commit**

```bash
git add pipeline/flow_qc.py tests/test_flow_qc.py
git commit -m "feat(v12): QC gates for generated clips"
```

---

### Task 9: Contact sheets for the eyes-on pass

Machine gates cannot tell who is in frame. Every previous build passed its machine gates and still failed review — the five-person pass found three factual failures and twenty-odd rule breaches on a machine-clean render.

**Files:**
- Create: `pipeline/flow_sheets.py`
- Writes: `work/flow_sheets/chapter_<n>.jpg`

**Interfaces:**
- Consumes: `manifest/flow_shots.json`, `library/veo/*.mp4`
- Produces: `def build_sheets(frozen_render: Path | None = None) -> list[Path]`

- [ ] **Step 1: Write the module**

```python
#!/usr/bin/env python3
"""Contact sheets for the human identity pass, one per chapter.

The machine gate cannot tell who is in frame. On a render that was clean by
every automatic measure, a five-person eyes-on pass still found a photograph
of ulcerative colitis captioned as Crohn's, an invented Monday-to-Friday
training split, and a card contradicting a bite fifty-five seconds earlier.

Two construction details, both learned the hard way:

Sheets pad unused grid cells with BLACK, not green. xstack fills with flat
green, and a previous pass reported "two pure green frames" that were almost
certainly padding rather than decoded video.

Sheets are cut from a FROZEN file. Three of five reviewers once read sheets
taken from a render being overwritten underneath them; one caught it when an
ffmpeg read failed with `moov atom not found` mid-review.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/flow_shots.json"
VEO = ROOT / "library/veo"
OUT = ROOT / "work/flow_sheets"

COLS, THUMB_W = 6, 320


def build_sheets(frozen_render: Path | None = None) -> list[Path]:
    shots = [s for s in json.loads(SHOTS.read_text(encoding="utf-8"))
             if s["kind"] == "gen"]
    OUT.mkdir(parents=True, exist_ok=True)
    tiles_dir = OUT / "tiles"
    tiles_dir.mkdir(exist_ok=True)

    made: list[Path] = []
    per_sheet = COLS * 5
    for page in range(0, len(shots), per_sheet):
        group = shots[page:page + per_sheet]
        tiles = []
        for s in group:
            src = (frozen_render if frozen_render
                   else VEO / f"{s['shot_id']}.mp4")
            if not Path(src).exists():
                continue
            tile = tiles_dir / f"{s['shot_id']}.png"
            ss = (s["start"] + s["end"]) / 2 if frozen_render else \
                (s["end"] - s["start"]) / 2
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.3f}",
                 "-i", str(src), "-frames:v", "1",
                 "-vf", (f"scale={THUMB_W}:-2,"
                         f"drawtext=text='{s['shot_id']}':x=6:y=6:"
                         f"fontsize=18:fontcolor=white:box=1:boxcolor=black"),
                 str(tile)], check=True)
            tiles.append(tile)
        if not tiles:
            continue
        sheet = OUT / f"chapter_{page // per_sheet:02d}.jpg"
        inputs = []
        for t in tiles:
            inputs += ["-i", str(t)]
        rows = (len(tiles) + COLS - 1) // COLS
        layout = "|".join(
            f"{(i % COLS)}_{(i // COLS)}" for i in range(len(tiles)))
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", *inputs,
             "-filter_complex",
             f"xstack=inputs={len(tiles)}:layout={layout}:fill=black",
             "-q:v", "3", str(sheet)], check=True)
        made.append(sheet)
        print(f"{sheet.name}  {len(tiles)} tiles  {rows} rows")
    return made


if __name__ == "__main__":
    build_sheets()
```

- [ ] **Step 2: Verify against the proof clips**

```bash
python pipeline/flow_sheets.py
ls work/flow_sheets/
```
Expected: at least one `chapter_00.jpg` containing the generated proof tiles, each labelled with its shot id.

- [ ] **Step 3: Commit**

```bash
git add pipeline/flow_sheets.py
git commit -m "feat(v12): contact sheets for the eyes-on identity pass"
```

---

### Task 10: Assemble

**Files:**
- Create: `pipeline/flow_assemble.py`
- Test: `tests/test_flow_assemble.py`
- Writes: `final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V12.mp4`

**Interfaces:**
- Consumes: `manifest/flow_shots.json`, `library/veo/*.mp4`, `manifest/bite_windows.json`
- Produces:
  - `def piece_path(shot: dict) -> Path`
  - `def render_piece(shot: dict) -> Path`
  - `def verify_pieces(shots: list[dict]) -> list[str]`
  - `def concat_and_mux(pieces: list[Path], out: Path) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_flow_assemble.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_assemble import TAIL_FRAMES, TOTAL_FRAMES, piece_path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_total_frames_covers_the_whole_audio():
    assert TOTAL_FRAMES == 17727
    assert TAIL_FRAMES == 60


def test_shot_frames_plus_tail_equal_the_total():
    shots = json.loads(
        (ROOT / "manifest/flow_shots.json").read_text(encoding="utf-8"))
    assert sum(s["frames"] for s in shots) + TAIL_FRAMES == TOTAL_FRAMES


def test_piece_path_is_keyed_on_content_not_position():
    """Pieces were once cached by positional shot name, so swapping a clip
    served the old render forever. Key on an asset fingerprint."""
    a = piece_path({"shot_id": "s000a", "prompt": "one", "frames": 100,
                    "kind": "gen"})
    b = piece_path({"shot_id": "s000a", "prompt": "two", "frames": 100,
                    "kind": "gen"})
    assert a != b


def test_piece_path_is_stable_for_identical_content():
    shot = {"shot_id": "s000a", "prompt": "one", "frames": 100, "kind": "gen"}
    assert piece_path(dict(shot)) == piece_path(dict(shot))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_flow_assemble.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow_assemble'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Cut the picture against the locked audio, frame-exactly.

Every shot owns an integer frame count. The counts sum to exactly the audio's
frame count. Each rendered piece is copy-trimmed to its count with
`-frames:v N -c copy`, and a piece that comes up short is an ERROR - it is
never padded, never frozen and never looped.

That rule exists because rounding across 130 shots once accumulated 3.8
seconds of drift, and the first fix padded the gap with a frozen frame,
producing an 18-second stall in the middle of the film.

Pieces are cached on a fingerprint of their content, not on the shot name.
Shot names are positional: swap a clip and the old render is served forever.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/flow_shots.json"
VEO = ROOT / "library/veo"
SRC = ROOT / "dossier/mrbeast/sources"
PIECES = ROOT / "work/v12_pieces"
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V12.mp4"

FPS = 24
OUT_W, OUT_H = 1920, 1080
TOTAL_FRAMES = 17727          # round(738.606 * 24)
TAIL_FRAMES = 60              # 2.499s of silence, faded to black
# ffmpeg will not accept "#111" as a colour. Six hex digits or it errors.
TAIL_COLOUR = "0x000000"


def fingerprint(shot: dict) -> str:
    payload = json.dumps(
        {k: shot.get(k) for k in ("shot_id", "prompt", "frames", "kind",
                                  "source", "start", "end")},
        sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def piece_path(shot: dict) -> Path:
    return PIECES / f"{shot['shot_id']}_{fingerprint(shot)}.mp4"


def render_piece(shot: dict) -> Path:
    dest = piece_path(shot)
    if dest.exists():
        return dest
    PIECES.mkdir(parents=True, exist_ok=True)
    if shot["kind"] == "gen":
        src, ss = VEO / f"{shot['shot_id']}.mp4", 0.0
    else:
        src, ss = SRC / f"{shot['source']}.mp4", shot.get("src_t0", 0.0)
    if not src.exists():
        raise SystemExit(f"{shot['shot_id']}: missing source {src}")

    tmp = dest.with_suffix(".tmp.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(src),
         "-frames:v", str(shot["frames"]),
         "-vf", f"scale={OUT_W}:{OUT_H}:flags=lanczos,fps={FPS}",
         "-an", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-threads", "2", str(tmp)], check=True)
    tmp.replace(dest)
    return dest


def verify_pieces(shots: list[dict]) -> list[str]:
    """Every piece must have exactly the frames it was allocated."""
    bad = []
    for s in shots:
        p = piece_path(s)
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-count_frames", "-show_entries", "stream=nb_read_frames",
             "-of", "csv=p=0", str(p)],
            capture_output=True, text=True).stdout
        digits = "".join(c for c in out if c.isdigit()) or "0"
        got = int(digits)
        if got != s["frames"]:
            bad.append(f"{s['shot_id']}: {got} frames, wanted {s['frames']}")
    return bad


def concat_and_mux(pieces: list[Path], out: Path) -> None:
    lst = PIECES / "concat.txt"
    lst.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8")
    body = PIECES / "body.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(body)], check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(body), "-i", str(AUDIO),
         "-filter_complex",
         f"[0:v]tpad=stop_mode=add:stop_duration={TAIL_FRAMES / FPS}:"
         f"color={TAIL_COLOUR}[v]",
         "-map", "[v]", "-map", "1:a",
         "-frames:v", str(TOTAL_FRAMES),
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", str(out)], check=True)


def main() -> None:
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    for i, s in enumerate(shots, 1):
        render_piece(s)
        if i % 10 == 0:
            print(f"  {i}/{len(shots)} pieces")
    bad = verify_pieces(shots)
    if bad:
        raise SystemExit("frame-count failures:\n  " + "\n  ".join(bad))
    concat_and_mux([piece_path(s) for s in shots], OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flow_assemble.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest tests/ -v`
Expected: PASS — all pre-existing tests plus the new ones.

- [ ] **Step 6: Commit**

```bash
git add pipeline/flow_assemble.py tests/test_flow_assemble.py
git commit -m "feat(v12): frame-exact assembly against the locked audio"
```

---

### Task 11: Full pass

Only after the owner has approved both the prompt list (Task 5) and the three-shot proof (Task 7).

- [ ] **Step 1: Confirm the balance covers the run**

The prepay was $21.08 and buys 421 billed seconds; a full pass needs 664s ($33.20). Check the current balance at https://aistudio.google.com/ and top up if needed, or run in two halves with the cap.

- [ ] **Step 2: Generate in the background**

```bash
python pipeline/flow_gen.py --cap 20.00 > work/flow_gen.log 2>&1 &
```

Watch: `tail -f work/flow_gen.log`. The worker is resumable — re-run the same command to continue after a cap stop or a kill.

- [ ] **Step 3: QC everything**

```bash
python pipeline/flow_qc.py
```
Investigate every flagged clip. A flagged clip is regenerated, never shipped.

- [ ] **Step 4: Assemble**

```bash
python pipeline/flow_assemble.py
```

- [ ] **Step 5: Freeze, then cut sheets from the frozen file**

```bash
cp final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V12.mp4 work/v12_frozen.mp4
python -c "
import sys; sys.path.insert(0,'pipeline')
from pathlib import Path
from flow_sheets import build_sheets
build_sheets(Path('work/v12_frozen.mp4'))
"
```

**Do not rebuild while the review is running.**

- [ ] **Step 6: OWNER REVIEW GATE**

Hand over the sheets and the render. Every previous build was machine-clean and still failed here.

- [ ] **Step 7: Commit the manifests**

```bash
git add manifest/flow_shots.json manifest/flow_gen_status.json manifest/flow_qc.json
git commit -m "feat(v12): first full generated picture pass"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| §2 locked inputs | Global Constraints; Task 4 reads the EDL |
| §3 composition, 17/8 sync split | Task 4 (`sync_capable`, tested) |
| §4 shot splitting ≤6s | Task 2 |
| §5 backend, key handling, spend cap | Task 6 |
| §6 components | Tasks 2, 3, 4, 6, 8, 10 |
| §7 rules 2, 3, 4 | Task 8 (dedupe), Task 10 (no pad/loop), Task 2 (≤6s) |
| §7 rule 9 rewritten | Task 5 authoring rules; Task 9 eyes-on |
| §8 style tail + reference stills | Task 5 |
| §9 QC gates | Tasks 8, 9 |
| §10 error handling | Task 6 (atomic status, explicit failure), Task 10 (short = error) |
| §11 test plan | Task 7 |
| §12 24fps, 720p→1080p, silent tail | Task 2 (`FPS`), Task 10 (scale, `TAIL_FRAMES`) |

**Gap found and closed:** §8 requires 1–3 fixed reference stills passed to every generation. Task 6's `generate_one` does not pass them, because the installed SDK's field name for reference images is unverified. Task 6 Step 1 introspects `GenerateVideosConfig`; **if a reference-image field exists, add it to `generate_one` before Task 7.** If it does not exist on Lite, the style tail carries consistency alone and the spec should be amended to say so.

**Placeholder scan:** clean. Every code step contains runnable code; every verification step names the command and its expected output.

**Type consistency:** `Beat` fields (`idx`, `start`, `end`, `frames`, `gen_dur`) match their use in `flow_plan.build_shots`. `shot_id` format `s{seg_i:03d}{letter}` is consistent across Tasks 4, 5, 6, 8, 10. `gate_*` functions all return `str | None`. `piece_path` takes a shot dict in both Task 10's tests and implementation.

**Known deviation:** Task 4's test asserts 117 generated shots and 664 billed seconds; the spec's §4 table quotes 102 shots/582s for the 49 narration segments alone. Both are correct — the plan's figure includes the lead-in and the 14 orphan-bite shots.
