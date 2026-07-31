#!/usr/bin/env python3
"""Read the shot-prompt document into structured blocks.

The document is the film's picture script: a vendored markdown file with one
heading per segment of the locked audio, each carrying the words spoken over
it and (usually) a FLOW PROMPT to paste into the generator. 25 of those
segments are bites -- the subject's own recorded voice -- and each names the
real-footage source it should be synced to instead of generated. A handful
of bites have no clean window in that source footage; those carry a FLOW
PROMPT of their own immediately after the USE THE REAL FOOTAGE line, so the
two markers are independent booleans on a block, not a choice between them.
Which of those two paths a later task actually takes is decided elsewhere,
against a different file -- this module only reports what the document says.

Every DocBlock's `kind` is one of six values: lead_in, narration, bite,
beat, title_break, card. That set is dictated by manifest/edl_full.json,
the authoritative timeline this parser's output is joined against later --
in particular `card` exists as its own kind (not folded into title_break)
because the EDL carries a distinct "card" segment kind and this document's
one CARD heading is that same segment.

The document's own timestamps are NOT authoritative. They exist to write
the prompts against something, but they are hand-typed and drift: this is
parsed only for ordering blocks and cross-checking them against the real
timeline. Every duration used downstream comes from manifest/edl_full.json.

The source text uses an en-dash (–) between a heading's two timestamps
and an em-dash (—) inside the heading between its kind and description,
plus curly quotes around bite lines. It is valid UTF-8; always open it with
encoding="utf-8" or these render as replacement characters.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "dossier/mrbeast/FLOW_DOC.md"
OUT = ROOT / "manifest/flow_doc_blocks.json"

# Headings look like "**BITE — HIS OWN VOICE — Joe Rogan Experience \#1788**
# 0:11.89–0:13.99": a bold label, then two timestamps joined by a dash.
# Every heading in the real document separates its timestamps with an
# en-dash, but a plain hyphen and an em-dash are accepted too since neither
# is load-bearing and a future edit of the doc is likelier to introduce an
# ASCII "-" than to remove one of these.
DASHES = "–—-"
HEAD = re.compile(
    r"^\*\*(?P<label>[A-Z][^*\n]*?)\*\*[ \t]+"
    r"(?P<t0>\d+(?::\d+)?(?:\.\d+)?)\s*[" + DASHES + r"]\s*"
    r"(?P<t1>\d+(?::\d+)?(?:\.\d+)?)[ \t]*$",
    re.MULTILINE)

# "*FLOW PROMPT: ... 24fps*" -- a single italic run. Non-greedy up to the
# next "*" is safe because no prompt in the document contains a literal
# asterisk.
PROMPT = re.compile(r"\*FLOW PROMPT:\s*(?P<body>.+?)\*", re.DOTALL)

# "**USE THE REAL FOOTAGE.** Airrack, around 0:00 — ..." -- the marker plus
# whatever reasoning follows it on the same line.
REAL = re.compile(r"\*\*USE THE REAL FOOTAGE\.\*\*(?P<rest>[^\n]*)")

# Lines belonging to the reference-image scaffolding every block carries
# (an empty markdown table plus a caption), not to the block's own text.
REF_TABLE_ROW = re.compile(r"^\|.*$", re.MULTILINE)
REF_CAPTION = re.compile(r"^references only.*$", re.MULTILINE)

# The document's own chapter headings ("## **4 — THE PACT**") sit between
# one block's body and the next block's heading, so they land inside
# whichever block happens to run up against them -- once concatenated
# straight onto the end of real spoken narration with no separator. Strip
# any markdown ATX heading line, not just the specific "##" the document
# happens to use, since ######-level headings are the same hazard.
CHAPTER_HEADING = re.compile(r"^#{1,6}\s.*$", re.MULTILINE)

# Prefix match against a heading's label, longest/most-specific first where
# one prefix could shadow another. Two heading kinds the brief didn't know
# about turned up in the real document. CARD keeps its own "card" kind
# because manifest/edl_full.json -- the authoritative timeline this parser
# exists to be joined against -- has a distinct "card" segment kind
# (seg_id c048, start 491.706) that the document's one CARD heading matches
# to within 4ms; folding it into title_break would make no DocBlock ever
# reconcile against that EDL segment. TAIL ("TAIL — music only") has no
# competing authority: it falls entirely after the EDL's last segment
# (end 736.107) and corresponds to no real segment, so it is folded into
# beat, the closest of the six kinds to its music-only/no-narration shape.
KINDS = (
    ("LEAD-IN", "lead_in"),
    ("TITLE BREAK", "title_break"),
    ("CARD", "card"),
    ("NARRATION", "narration"),
    ("BITE", "bite"),
    ("BEAT", "beat"),
    ("TAIL", "beat"),
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
    raise ValueError(f"unrecognised heading kind: {label!r}")


def _clean_text(body: str) -> str:
    body = PROMPT.sub("", body)
    body = REAL.sub("", body)
    body = REF_TABLE_ROW.sub("", body)
    body = REF_CAPTION.sub("", body)
    body = CHAPTER_HEADING.sub("", body)
    return " ".join(body.split())


def parse_doc(markdown: str) -> list[DocBlock]:
    heads = list(HEAD.finditer(markdown))
    blocks: list[DocBlock] = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(markdown)
        body = markdown[h.end():end]
        pm = PROMPT.search(body)
        rm = REAL.search(body)
        label = " ".join(h.group("label").split()).replace("\\#", "#")
        blocks.append(DocBlock(
            kind=_kind_of(h.group("label")),
            start=parse_timestamp(h.group("t0")),
            end=parse_timestamp(h.group("t1")),
            text=_clean_text(body),
            prompt=" ".join(pm.group("body").split()) if pm else "",
            real_footage=bool(rm),
            source_label=label,
        ))
    return blocks


def main() -> None:
    blocks = parse_doc(DOC.read_text(encoding="utf-8"))
    OUT.write_text(
        json.dumps([asdict(b) for b in blocks], indent=1, ensure_ascii=False),
        encoding="utf-8")
    prompts = sum(1 for b in blocks if b.prompt)
    real = sum(1 for b in blocks if b.real_footage)
    both = sum(1 for b in blocks if b.prompt and b.real_footage)
    print(f"{len(blocks)} blocks  {prompts} prompts  {real} real-footage  "
          f"{both} bites needing generated picture")


if __name__ == "__main__":
    main()
