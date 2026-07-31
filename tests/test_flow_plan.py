import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_plan import build_shots, sync_capable, KNOWN_MISSING_PROMPTS  # noqa: E402
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


def test_one_hundred_eighteen_shots_are_generated(shots):
    assert sum(1 for s in shots if s["kind"] == "gen") == 118


def test_the_title_break_is_its_own_generated_shot(shots):
    """A 4s music-only hold before the diagnosis. It is not a segment, so a
    segment-driven loop skips it and leaves a hole in the timeline.

    The tolerance is wider than one frame (0.1s, not 0.05s): global
    largest-remainder allocation (flow_split.allocate_frames, called once
    across all 135 spans) does not guarantee every *intermediate* cut lands
    within a frame of its pure-seconds value, only that the final total is
    exact -- measured drift here is 0.056s, more than the 0.018s drift at
    the very end of the film, because the units earlier in the sequence
    happened to carry more of the largest-remainder top-up.
    """
    tb = [s for s in shots if 54.0 < s["start"] < 54.2 and s["kind"] == "gen"]
    assert len(tb) == 1, tb
    assert abs(tb[0]["end"] - 58.098) < 0.1
    assert tb[0]["prompt"].strip()


def test_frames_sum_to_the_picture_budget(shots):
    assert sum(s["frames"] for s in shots) == PICTURE_FRAMES


def test_shots_are_contiguous_with_no_gaps_or_overlaps(shots):
    for a, b in zip(shots, shots[1:]):
        assert a["end"] == pytest.approx(b["start"], abs=1e-6)


def test_timeline_starts_at_zero_and_ends_at_the_edl_end(shots):
    # Frames are allocated once, globally, across all 135 spans (see
    # flow_plan.build_shots); the last shot's end is the cumulative frame
    # position, not the EDL's own literal float, so it can land up to a
    # frame short of/past edl["end"] (measured: 736.125 vs 736.107, 18ms).
    # A non-integer number of frames is not an option, so the tolerance is
    # one frame rather than the timestamp's own precision.
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(
        encoding="utf-8"))
    assert shots[0]["start"] == pytest.approx(0.0)
    assert shots[-1]["end"] == pytest.approx(edl["end"], abs=1 / FPS)


def test_no_generated_shot_exceeds_six_seconds(shots):
    for s in shots:
        if s["kind"] == "gen":
            assert s["end"] - s["start"] <= 6.0 + 1e-9, s["shot_id"]


def test_only_the_known_document_gap_lacks_a_prompt(shots):
    """The document promises eight orphan-bite prompts and supplies seven.
    A missing prompt must stay visibly missing, never silently borrowed
    from a neighbouring block."""
    missing = sorted({s["seg_i"] for s in shots
                      if s["kind"] == "gen" and not s["prompt"].strip()})
    assert missing == sorted(KNOWN_MISSING_PROMPTS), missing


def test_shot_ids_are_unique(shots):
    ids = [s["shot_id"] for s in shots]
    assert len(ids) == len(set(ids))


def test_gen_dur_covers_every_generated_shot(shots):
    for s in shots:
        if s["kind"] == "gen":
            assert s["gen_dur"] >= s["end"] - s["start"], s["shot_id"]


def test_billed_seconds_match_the_budget(shots):
    # 660, not the 662 arrived at by adding the title break's raw 4s to the
    # pre-allocation total: global allocation (ruling 2) nudges one shot's
    # final duration across the 4s/6s legal-duration line versus its
    # pure-seconds estimate, which is the "changes boundaries by a frame or
    # two, which is correct and expected" effect applied to gen_dur rather
    # than to a start/end timestamp. See flow_plan.py's module docstring.
    billed = sum(s["gen_dur"] for s in shots if s["kind"] == "gen")
    assert billed == 660


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
