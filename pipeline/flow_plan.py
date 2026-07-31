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

Every segment boundary is quantized independently from the EDL's own
authoritative time -- `frame_at(t) = round(t * FPS)` -- rather than
accumulated from a running position. Two earlier approaches were tried and
rejected for this:

- Rounding each of the 74 segments' own *duration* independently and
  summing drifts 2 frames away from round(edl["end"] * FPS) (measured:
  17,669 vs 17,667) -- the accumulated-rounding failure flow_split.py's own
  docstring describes for a single segment's beats, one level up.
- Pooling all 17,667 frames and allocating them globally with
  flow_split.allocate_frames() fixes that total exactly, but the
  largest-remainder top-up can land its slack on *any* span in the pool,
  including a sync bite's boundary -- measured drift up to 1.35 frames
  (56ms) on `s006s`/`s008s`. A generated cutaway landing a frame early is
  invisible; a sync cut landing 56ms off the subject's own recorded voice
  is the exact defect the previous cut of this film was rejected for.

Quantizing each boundary independently fixes both at once: max error
against the true time is half a frame (~0.021s) and never compounds
(`test_no_boundary_drifts_more_than_half_a_frame`), and the grand total is
exactly 17,667 with no reconciliation step, because per-segment frame
counts telescope across a contiguous timeline --
`sum(round(seg.end*FPS) - round(seg.start*FPS)) == round(736.107*FPS) - 0`
(`test_frames_telescope_to_the_exact_total_without_reconciliation`). A
generated unit's beats then divide *that* unit's already-quantized frame
count among themselves with `allocate_frames(unit_frames, [1.0] * n)` -- a
purely local allocation whose slack can only ever land on that unit's own
interior beat boundaries, never on a segment boundary shared with a
neighbour (and never on a sync boundary, since sync bites are never split).
`gen_dur` is derived from each beat's *final* quantized start/end via
flow_split.gen_duration, not estimated beforehand, since a boundary that
moves by half a frame can occasionally cross a legal-duration line.

A sync shot's cut point is the bite's own recorded in-point,
edl_full.json's `seg["src_t0"]`, never `bite_windows.py`'s `run["t0"]`.
That scanner widens its search window by 1.5s on each side and then nudges
every candidate edge by 0.25s, so in the common case `run["t0"] ==
seg["src_t0"] - 1.25` by construction -- a fixed, structural offset, not
noise. `run["t0"]`/`run["key"]` are kept only as `src_run_key`, a record of
which scanned window a human verified as clean, not a cut point. Similarly,
`best_run()` prefers the run whose span *contains* `seg["src_t0"]` over
merely the longest verified one: `usable` is capped at MAX_SHOT (6.0) by
the scanner, so many runs tie at exactly 6.0 and "longest" mostly picks by
list order, sometimes discarding the one run that actually covers the
words in favour of a longer one that starts after them. Every sync shot
also carries `verified_through` (how far the chosen run's clean window
extends) and `verified_ratio` (what fraction of the shot's real-footage
span that window actually covers) so a shot whose window runs out before
the bite does -- a real camera cut mid-shot -- is visible in the manifest
rather than only discoverable by watching the render.
"""

from __future__ import annotations

import json
from pathlib import Path

from flow_split import FPS, allocate_frames, beat_count, gen_duration

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
    """The verified, text-free run that actually covers this bite's words.

    Verdicts are keyed by sid@t0, never by sheet index: verify_pool.py once
    hard-coded tile indices, so adding a source re-sorted the thumbnails and
    silently re-pointed every verdict at a different frame.

    Prefers the run whose [t0, run_end) span contains the bite's own
    src_t0 over the run with the largest `usable`: `usable` is capped at
    MAX_SHOT by the scanner, so a plain "longest wins" rule mostly breaks
    ties by list order among runs saturated at exactly 6.0, and can
    actively steer away from the one run that covers the actual in-point in
    favour of a longer run that starts after the words already began (see
    module docstring). Falls back to the longest verified run when none
    contains src_t0 -- a real data gap this function reports rather than
    hides; see `verified_ratio` on the shots this feeds.
    """
    if not bite.get("sync_possible"):
        return None
    ok = [r for r in bite.get("runs", [])
          if r.get("verified_jimmy") and not r.get("has_text")]
    if not ok:
        return None
    src_t0 = bite.get("src_t0")
    if src_t0 is not None:
        containing = [r for r in ok
                      if r.get("t0", 0.0) <= src_t0 <= r.get("run_end", 0.0)]
        if containing:
            return max(containing, key=lambda r: r.get("usable", 0.0))
    return max(ok, key=lambda r: r.get("usable", 0.0))


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


def _frame_at(t: float) -> int:
    """This instant's index on the film's 24fps grid."""
    return round(t * FPS)


def build_shots() -> list[dict]:
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    blocks = json.loads(BLOCKS.read_text(encoding="utf-8"))
    bites = {b["i"]: b for b in json.loads(BITES.read_text(encoding="utf-8"))}

    shots: list[dict] = []

    def gen_unit(seg_i: int, seg_id: str, start: float, end: float,
                 prompt: str, narration: str) -> None:
        """A generated unit: its own two boundaries are quantized once,
        and its beats split *that* integer frame count locally -- slack
        from the beat split can only ever land inside this unit, never on
        the segment boundary it shares with a neighbour.
        """
        f0, f1 = _frame_at(start), _frame_at(end)
        n = beat_count(end - start)
        beat_frames = allocate_frames(f1 - f0, [1.0] * n)
        cum = f0
        for idx, bf in enumerate(beat_frames):
            b_start, cum = cum / FPS, cum + bf
            b_end = cum / FPS
            if seg_i == -1:
                shot_id = "s_lead"
            elif seg_i == -2:
                shot_id = "s_break"
            else:
                shot_id = f"s{seg_i:03d}{chr(97 + idx)}"
            shots.append({
                "shot_id": shot_id, "seg_i": seg_i, "seg_id": seg_id,
                "kind": "gen", "start": b_start, "end": b_end,
                "frames": bf, "gen_dur": gen_duration(b_end - b_start),
                "beat_idx": idx, "beat_of": n, "prompt": prompt,
                "narration": narration, "source": "", "status": "pending",
            })

    # The lead-in: 0 -> first segment, music only, generated.
    lead_end = edl["segs"][0]["start"]
    gen_unit(-1, "lead_in", 0.0, lead_end, _prompt_for(blocks, 0.0, lead_end), "")

    prev_end = lead_end
    for seg in edl["segs"]:
        i, kind = seg["i"], seg["kind"]
        if kind not in GEN_KINDS and kind != "bite":
            # A segment kind this module doesn't know about must fail
            # loudly, not fall through to the generated branch below and
            # silently pick up a neighbour's prompt.
            raise ValueError(f"unrecognised segment kind {kind!r} (seg i={i})")

        # A segment-driven loop skips any stretch that isn't a segment. The
        # 4s title-break hold between i=6 and i=7 is exactly that stretch:
        # emit it the moment this segment's start doesn't pick up where the
        # previous one left off, rather than assuming `segs` has no holes.
        if seg["start"] > prev_end:
            gap_start, gap_end = prev_end, seg["start"]
            gen_unit(-2, "title_break", gap_start, gap_end,
                     _prompt_for(blocks, gap_start, gap_end), "")
        elif seg["start"] < prev_end - 1e-9:
            raise ValueError(
                f"seg i={i} starts at {seg['start']} before the previous "
                f"segment's end {prev_end}; segments must be ordered and "
                f"non-overlapping")

        bite = bites.get(i)
        is_sync = kind == "bite" and bite is not None and sync_capable(bite)
        if is_sync:
            # A sync boundary is the subject's own recorded voice starting
            # or stopping. It is quantized directly from the EDL and never
            # split or pooled with anything else, so no other shot's
            # rounding slack can ever land on it.
            run = best_run(bite)
            f0, f1 = _frame_at(seg["start"]), _frame_at(seg["end"])
            shot_start, shot_end = f0 / FPS, f1 / FPS

            # How much of the real footage this shot actually needs, and
            # how much of that the verified window covers -- so a run that
            # ends before the bite does (a real camera cut mid-shot) is
            # visible in the manifest instead of only found by watching
            # the render.
            req_start = seg["src_t0"]
            req_end = req_start + (shot_end - shot_start)
            covered = max(0.0, min(req_end, run["run_end"])
                          - max(req_start, run["t0"]))
            verified_ratio = covered / (req_end - req_start)

            shots.append({
                "shot_id": f"s{i:03d}s", "seg_i": i, "seg_id": seg["seg_id"],
                "kind": "sync", "start": shot_start, "end": shot_end,
                "frames": f1 - f0,
                "gen_dur": 0, "beat_idx": 0, "beat_of": 1,
                "prompt": "", "narration": seg["text"], "source": seg["source"],
                # The bite's own recorded in-point (EDL-authoritative).
                # NOT run["t0"] -- bite_windows.py's scan window is widened
                # by 1.5s and its edges nudged by 0.25s, so run["t0"] sits
                # ~1.25s before the words in the common case. run["key"] is
                # kept as provenance: which scanned window a human verified
                # clean, not where to cut from.
                "src_t0": seg["src_t0"], "src_run_key": run["key"],
                "verified_through": run["run_end"],
                "verified_ratio": verified_ratio,
                "status": "pending",
            })
        else:
            # Every remaining segment (narr/beat/card, or a bite that
            # didn't qualify for sync) is generated picture.
            prompt = _prompt_for(blocks, seg["start"], seg["end"])
            gen_unit(i, seg["seg_id"], seg["start"], seg["end"], prompt,
                     seg["text"])

        prev_end = seg["end"]

    # No reconciliation step: round(seg.end*FPS) - round(seg.start*FPS)
    # telescopes across a contiguous timeline, so this is a verification of
    # that fact, not a fix for a shortfall it could not otherwise close.
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
    missing = sorted({s["seg_i"] for s in gen if not s["prompt"].strip()})
    print(f"{len(shots)} shots  {len(gen)} generated  "
          f"{len(shots) - len(gen)} sync  "
          f"{sum(s['frames'] for s in shots)} frames  "
          f"{billed}s billed  ${billed * 0.05:.2f}  "
          f"missing prompts at seg_i={missing}")


if __name__ == "__main__":
    main()
