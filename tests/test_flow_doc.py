import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_doc import DocBlock, parse_doc, parse_timestamp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# En-dash (–) between timestamps, em-dash (—) inside headings, and
# curly quotes around the bite line -- matching dossier/mrbeast/FLOW_DOC.md's
# actual punctuation rather than plain ASCII.
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

# An orphan bite: no clean real-footage window exists, so it carries BOTH a
# USE THE REAL FOOTAGE marker AND its own FLOW PROMPT immediately after,
# with no intervening heading. Modelled on the real Airrack bite at
# 5:47.62-5:53.57.
ORPHAN_SAMPLE = """**BITE — HIS OWN VOICE — Airrack — My 600 Day Transformation**   5:47.62–5:53.57

“I signed a legally binding contract with MrBeast…”

**USE THE REAL FOOTAGE.** Airrack, around 0:00 — AIRRACK'S VOICE, and no Jimmy-only frame exists in his video. Illustrate instead.

*FLOW PROMPT: A legal contract lying on a desk in hard raking light…*
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


def test_orphan_bite_has_both_real_footage_and_a_prompt():
    """A bite with no usable footage still needs generated picture: both
    fields must be independently true, they are not mutually exclusive."""
    b = parse_doc(ORPHAN_SAMPLE)[0]
    assert b.kind == "bite"
    assert b.real_footage is True
    assert b.prompt != ""
    assert "legal contract" in b.prompt


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


def test_real_document_has_twentyfive_real_footage_bites():
    """The document names 25 USE THE REAL FOOTAGE occurrences; every one of
    them sits inside a BITE block, so exactly 25 blocks are real_footage."""
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    blocks = parse_doc(doc)
    assert sum(1 for b in blocks if b.real_footage) == 25
    assert all(b.kind == "bite" for b in blocks if b.real_footage)


def test_real_document_kind_is_always_a_known_value():
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    blocks = parse_doc(doc)
    allowed = {"lead_in", "narration", "bite", "beat", "title_break", "card"}
    for b in blocks:
        assert b.kind in allowed, f"unknown kind {b.kind!r} at {b.start}"


def test_narration_text_never_absorbs_a_chapter_heading():
    """A chapter title concatenated onto spoken narration corrupts the
    dialogue, not just the block list."""
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    for b in parse_doc(doc):
        assert "##" not in b.text, (b.kind, b.start, b.text[:120])
        assert "THE PACT" not in b.text, (b.kind, b.start)


def test_card_heading_is_parsed_as_card_and_matches_the_edl():
    import json
    doc = (ROOT / "dossier/mrbeast/FLOW_DOC.md").read_text(encoding="utf-8")
    cards = [b for b in parse_doc(doc) if b.kind == "card"]
    assert len(cards) == 1, cards
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(encoding="utf-8"))
    seg = next(s for s in edl["segs"] if s["kind"] == "card")
    assert abs(cards[0].start - seg["start"]) < 0.05
