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

Two defects in the source data are handled explicitly here rather than
papered over:

1. The document supplies a FLOW PROMPT for only 7 of the 8 orphan bites.
   i=67 (7r3ORKgNUjw, "You look like a different human being...") has none.
   The naive fix -- take whichever document block overlaps a segment the
   most -- would silently hand that bite a neighbouring narration block's
   prompt, putting the wrong picture on screen with nothing failing. Instead
   _prompt_for() requires a block to cover most of the shorter of the two
   spans before it may supply a prompt at all, and returns "" otherwise. The
   resulting gap is pinned in KNOWN_MISSING_PROMPTS so it cannot regress and
   so the next task (which authors the missing prompt) knows exactly where
   to look.

2. edl_full.json's `segs` list has exactly one gap: seg i=6 (a bite, 44.498
   -> 54.098) is followed by seg i=7 (a narration, 58.098 -> ...), a bare
   4.0s hole that is edl["title_break"] -- a music-only hold placed
   deliberately before the diagnosis lands (HANDOFF.md), not a segment of
   its own, and not a stretch of some neighbouring bite's real footage
   either -- the whole point of the hold is that the film goes quiet and
   the subject's face is *not* on screen. FLOW_DOC.md carries a FLOW PROMPT
   for it (a held wide of a deserted baseball diamond), so it is its own
   generated shot: build_shots() walks the timeline segment by segment and
   emits this shot the moment it notices seg i+1's start doesn't match seg
   i's own end, rather than assuming `segs` has no holes.

Frame allocation is global, not per unit. Phase 1 below walks the whole
timeline once and records every shot's *span* (lead-in, title break, each
EDL segment's beats or single sync cut) in chronological order, without
assigning any of them frames yet. Phase 2 hands all of those span widths to
flow_split.allocate_frames() in a single call against the one true target,
round(edl["end"] * FPS), and derives every shot's final start/end from its
cumulative position in the resulting frame sequence. Rounding each unit's
own width independently and summing -- the obvious alternative -- drifts
away from the rounded total (measured: 17,669 frames against a target of
17,667, from 74 units each rounding a few hundredths of a frame off in
either direction with no reason to cancel); it is the exact "accumulated
drift" flow_split.py's own docstring describes for a single segment's beats,
one level up, and it once cost this project an 18-second frozen frame to
paper over. Allocating once, globally, makes both exactness and contiguity
hold by construction instead of by luck -- at the cost of nudging every
shot boundary by at worst a frame or two away from its pure-seconds value
(so `gen_dur` is derived from each shot's *final* start/end, not from
flow_split.Beat's pre-allocation estimate, since a boundary that moves by a
couple of frames can occasionally cross a legal-duration line).
"""

from __future__ import annotations

import json
from pathlib import Path

from flow_split import FPS, allocate_frames, gen_duration, split_segment

ROOT = Path(__file__).resolve().parents[1]
EDL = ROOT / "manifest/edl_full.json"
BLOCKS = ROOT / "manifest/flow_doc_blocks.json"
BITES = ROOT / "manifest/bite_windows.json"
OUT = ROOT / "manifest/flow_shots.json"

GEN_KINDS = {"narr", "beat", "card"}

# A document block may lend its prompt to a segment only when the two
# genuinely describe the same moment. The document's timestamps are
# hand-typed and drift against the EDL by a few tenths of a second (see
# flow_doc.py), so a bare "greatest overlap wins" rule -- the brief's
# original approach -- will always find *some* block for every segment,
# including ones the document never actually wrote a prompt for. Requiring
# the overlap to cover most of the shorter span tells a real match (measured
# overlap ratio >= 0.999 for every one of the 7 orphan bites that do have a
# prompt, and >= 0.9 for every narration/beat/card segment) apart from the
# spurious sliver i=67 would otherwise inherit (its nearest neighbour
# overlaps by 0.00012 of its span -- three orders of magnitude below this
# line).
MIN_OVERLAP_FRACTION = 0.6

# The document has no FLOW PROMPT for this bite at all -- not a parsing
# bug, a gap in FLOW_DOC.md itself. Pinned here so a future re-run of this
# module can't silently start borrowing a neighbour's prompt again, and so
# the task that authors the missing prompt knows exactly where to look.
KNOWN_MISSING_PROMPTS = {67}


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
    """The document block that substantially coincides with [start, end).

    "Substantially" means the overlap covers at least MIN_OVERLAP_FRACTION
    of whichever span (the block's or the segment's) is shorter. A block
    that merely brushes a segment's edge -- the drift described above --
    never qualifies; when nothing does, this returns "" rather than
    borrowing the nearest neighbour's prompt.
    """
    seg_span = end - start
    best, best_ratio = "", 0.0
    for b in blocks:
        if not b["prompt"]:
            continue
        ov = min(end, b["end"]) - max(start, b["start"])
        if ov <= 0:
            continue
        shorter = min(seg_span, b["end"] - b["start"])
        if shorter <= 0:
            continue
        ratio = ov / shorter
        if ratio >= MIN_OVERLAP_FRACTION and ratio > best_ratio:
            best, best_ratio = b["prompt"], ratio
    return best


def build_shots() -> list[dict]:
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    blocks = json.loads(BLOCKS.read_text(encoding="utf-8"))
    bites = {b["i"]: b for b in json.loads(BITES.read_text(encoding="utf-8"))}

    # ---- Phase 1: the ordered list of spans. No frames assigned yet. ----
    units: list[dict] = []

    def gen_unit(seg_i: int, seg_id: str, start: float, end: float,
                 prompt: str, narration: str) -> None:
        beats = split_segment(start, end)
        for b in beats:
            units.append({
                "seg_i": seg_i, "seg_id": seg_id, "kind": "gen",
                "raw_start": b.start, "raw_end": b.end,
                "beat_idx": b.idx, "beat_of": len(beats),
                "prompt": prompt, "narration": narration, "source": "",
            })

    # The lead-in: 0 -> first segment, music only, generated.
    lead_end = edl["segs"][0]["start"]
    gen_unit(-1, "lead_in", 0.0, lead_end, _prompt_for(blocks, 0.0, lead_end), "")

    prev_end = lead_end
    for seg in edl["segs"]:
        i, kind = seg["i"], seg["kind"]

        # A segment-driven loop skips any stretch that isn't a segment. The
        # 4s title-break hold between i=6 and i=7 is exactly that stretch:
        # emit it the moment this segment's start doesn't pick up where the
        # previous one left off, rather than assuming `segs` has no holes.
        if seg["start"] > prev_end:
            gap_start, gap_end = prev_end, seg["start"]
            gen_unit(-2, "title_break", gap_start, gap_end,
                     _prompt_for(blocks, gap_start, gap_end), "")

        bite = bites.get(i)
        is_sync = kind == "bite" and bite is not None and sync_capable(bite)
        if is_sync:
            run = best_run(bite)
            units.append({
                "seg_i": i, "seg_id": seg["seg_id"], "kind": "sync",
                "raw_start": seg["start"], "raw_end": seg["end"],
                "beat_idx": 0, "beat_of": 1, "prompt": "",
                "narration": seg["text"], "source": seg["source"],
                # Where in the interview to cut from. Without this the
                # assembler renders every sync shot from t=0 of the source.
                "src_t0": run["t0"], "src_run_key": run["key"],
            })
        else:
            # Every remaining segment (narr/beat/card, or a bite that
            # didn't qualify for sync) is generated picture.
            prompt = _prompt_for(blocks, seg["start"], seg["end"])
            gen_unit(i, seg["seg_id"], seg["start"], seg["end"], prompt,
                     seg["text"])

        prev_end = seg["end"]

    # ---- Phase 2: allocate every frame in one call, then derive times. ----
    want = round(edl["end"] * FPS)
    weights = [u["raw_end"] - u["raw_start"] for u in units]
    frames = allocate_frames(want, weights)

    shots: list[dict] = []
    cum = 0
    for u, f in zip(units, frames):
        start, cum = cum / FPS, cum + f
        end = cum / FPS
        if u["seg_i"] == -1:
            shot_id = "s_lead"
        elif u["seg_i"] == -2:
            shot_id = "s_break"
        elif u["kind"] == "sync":
            shot_id = f"s{u['seg_i']:03d}s"
        else:
            shot_id = f"s{u['seg_i']:03d}{chr(97 + u['beat_idx'])}"

        shot = {
            "shot_id": shot_id, "seg_i": u["seg_i"], "seg_id": u["seg_id"],
            "kind": u["kind"], "start": start, "end": end, "frames": f,
            "gen_dur": 0 if u["kind"] == "sync" else gen_duration(end - start),
            "beat_idx": u["beat_idx"], "beat_of": u["beat_of"],
            "prompt": u["prompt"], "narration": u["narration"],
            "source": u["source"], "status": "pending",
        }
        if u["kind"] == "sync":
            shot["src_t0"] = u["src_t0"]
            shot["src_run_key"] = u["src_run_key"]
        shots.append(shot)

    total = sum(s["frames"] for s in shots)
    if total != want:
        raise SystemExit(f"frame budget {total} != {want}; refusing to pad")
    return shots


def main() -> None:
    shots = build_shots()
    OUT.write_text(json.dumps(shots, indent=1), encoding="utf-8")
    gen = [s for s in shots if s["kind"] == "gen"]
    billed = sum(s["gen_dur"] for s in gen)
    missing = sorted({s["seg_i"] for s in gen if not s["prompt"].strip()})
    print(f"{len(shots)} shots  {len(gen)} generated  "
          f"{len(shots) - len(gen)} sync  "
          f"{sum(s['frames'] for s in shots)} frames  "
          f"{billed}s billed  ${billed * 0.05:.2f}  "
          f"missing prompts at seg_i={missing}")


if __name__ == "__main__":
    main()
