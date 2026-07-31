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

    Every boundary is now quantized independently from the EDL's own time
    (frame_at(t) = round(t * FPS)), not accumulated through a shared frame
    pool, so the true error against 58.098 is at most half a frame
    (~0.021s) and 0.05 is a real constraint again.
    """
    tb = [s for s in shots if 54.0 < s["start"] < 54.2 and s["kind"] == "gen"]
    assert len(tb) == 1, tb
    assert abs(tb[0]["end"] - 58.098) < 0.05
    assert tb[0]["prompt"].strip()


def test_no_boundary_drifts_more_than_half_a_frame(shots):
    """Drift on a sync boundary is 50ms of wrong picture under his own
    voice. Quantised boundaries cannot drift; distributed ones can."""
    by_i = {s["i"]: s for s in
            json.loads((ROOT / "manifest/edl_full.json").read_text(
                encoding="utf-8"))["segs"]}
    half = 0.5 / FPS + 1e-9
    for s in shots:
        seg = by_i.get(s["seg_i"])
        if seg is None:
            continue
        if s["beat_idx"] == 0:
            assert abs(s["start"] - seg["start"]) <= half, (s["shot_id"], "start")
        if s["beat_idx"] == s["beat_of"] - 1:
            assert abs(s["end"] - seg["end"]) <= half, (s["shot_id"], "end")


def test_frames_telescope_to_the_exact_total_without_reconciliation(shots):
    """The property that actually makes the grand total exact: every
    unit's own frame count equals frame_at(its end) - frame_at(its start),
    with no pool and no reconciliation step to paper over a shortfall."""
    from flow_plan import _frame_at

    units: dict[int, list[dict]] = {}
    for s in shots:
        units.setdefault(s["seg_i"], []).append(s)

    for seg_i, group in units.items():
        group.sort(key=lambda s: s["beat_idx"])
        unit_start, unit_end = group[0]["start"], group[-1]["end"]
        assert sum(s["frames"] for s in group) == (
            _frame_at(unit_end) - _frame_at(unit_start)), seg_i


def test_frames_sum_to_the_picture_budget(shots):
    assert sum(s["frames"] for s in shots) == PICTURE_FRAMES


def test_shots_are_contiguous_with_no_gaps_or_overlaps(shots):
    for a, b in zip(shots, shots[1:]):
        assert a["end"] == pytest.approx(b["start"], abs=1e-6)


def test_timeline_starts_at_zero_and_ends_at_the_edl_end(shots):
    # Every boundary is quantized independently, frame_at(t) = round(t *
    # FPS) (flow_plan._frame_at); the last shot's end is
    # frame_at(edl["end"]) / FPS, not edl["end"] itself, so it can land up
    # to half a frame short of/past it (measured: 736.125 vs 736.107,
    # 18ms). A non-integer number of frames is not an option, so the
    # tolerance is half a frame -- the real guarantee -- not a whole one.
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(
        encoding="utf-8"))
    assert shots[0]["start"] == pytest.approx(0.0)
    assert shots[-1]["end"] == pytest.approx(edl["end"], abs=0.5 / FPS + 1e-9)


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


def test_no_two_beats_of_a_segment_share_a_prompt(shots):
    """Sibling beats inheriting the segment prompt generate three
    near-identical shots in a row. Each beat must carry its own picture."""
    from collections import defaultdict
    seen = defaultdict(list)
    for s in shots:
        if s["kind"] == "gen" and s["beat_of"] > 1:
            seen[(s["seg_i"], s["prompt"])].append(s["shot_id"])
    dupes = {k[0]: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"segments with repeated prompts: {dupes}"


def test_every_authored_prompt_reached_the_manifest(shots):
    """Catches an authored key that matches no shot at all (a typo landing
    nowhere real, e.g. a stray character or a shot_id from a since-changed
    segment). Does NOT catch a typo that lands on a SIBLING's real
    shot_id -- that key exists, so `unused` stays empty, and the equality
    check below is tautological (by_id[sid]["prompt"] was populated from
    this same authored dict, so it trivially equals what the file says
    regardless of which beat was supposed to receive it). See
    test_every_multi_beat_shot_has_an_authored_prompt for that case."""
    import json as _json
    authored = _json.loads(
        (ROOT / "manifest/flow_beat_prompts.json").read_text(encoding="utf-8"))
    by_id = {s["shot_id"]: s for s in shots}
    unused = [k for k in authored if k not in by_id]
    assert not unused, f"authored prompts for unknown shot_ids: {unused}"
    for sid, text in authored.items():
        assert by_id[sid]["prompt"] == text, sid


def test_every_multi_beat_shot_has_an_authored_prompt(shots):
    """A typo landing on a SIBLING's shot_id steals that shot's prompt and
    leaves the intended beat on the segment fallback. The stolen key is a
    real id, so the reached-the-manifest check passes and the equality
    assertion is tautological. Only this direction catches it."""
    authored = json.loads(
        (ROOT / "manifest/flow_beat_prompts.json").read_text(encoding="utf-8"))
    orphaned = [s["shot_id"] for s in shots
                if s["kind"] == "gen" and s["beat_of"] > 1
                and s["shot_id"] not in authored]
    assert not orphaned, f"beats with no authored prompt: {orphaned}"


def test_shot_ids_are_unique(shots):
    ids = [s["shot_id"] for s in shots]
    assert len(ids) == len(set(ids))


def test_gen_dur_covers_every_generated_shot(shots):
    for s in shots:
        if s["kind"] == "gen":
            assert s["gen_dur"] >= s["end"] - s["start"], s["shot_id"]


def test_billed_seconds_are_bounded_and_legal(shots):
    # Not a golden value: 658 (93 shots @ 6s + 25 @ 4s) is what the current
    # manifest bills, but it has moved three times already as the boundary
    # construction changed underneath it and is not something this test
    # should re-pin. What must actually hold: no shot is billed a duration
    # Veo doesn't support, every shot's billed duration covers its own
    # span (tested separately below), and the total can't run away -- a
    # ceiling catches over-splitting without freezing today's exact count.
    gen = [s for s in shots if s["kind"] == "gen"]
    assert set(s["gen_dur"] for s in gen) <= {4, 6, 8}
    billed = sum(s["gen_dur"] for s in gen)
    assert billed <= 700


def test_sync_shots_carry_their_source_id(shots):
    for s in shots:
        if s["kind"] == "sync":
            assert s["source"], s["shot_id"]


def test_sync_shots_cut_from_the_bite_in_point_not_the_scan_window(shots):
    """bite_windows.py widens its search by 1.5s and nudges edges by 0.25s,
    so run["t0"] sits ~1.25s BEFORE the words. Cutting there puts a second
    of wrong picture under his own voice."""
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(encoding="utf-8"))
    by_i = {s["i"]: s for s in edl["segs"]}
    for s in shots:
        if s["kind"] == "sync":
            assert s["src_t0"] == pytest.approx(by_i[s["seg_i"]]["src_t0"]), s["shot_id"]


def test_sync_shots_report_how_much_of_the_shot_is_verified(shots):
    """usable is capped at MAX_SHOT and best_run can only fall back to it
    when no run covers the true in-point, so a shot can legitimately play
    longer than its verified window. That shortfall must be visible on the
    shot, not just discoverable by watching the render."""
    short = []
    for s in shots:
        if s["kind"] != "sync":
            continue
        assert s["verified_ratio"] > 0, s["shot_id"]
        assert s["verified_through"] > 0, s["shot_id"]
        if s["verified_ratio"] < 1.0:
            short.append((s["shot_id"], round(s["verified_ratio"], 3)))
    # Not an assertion on the count -- the data problem is real and not
    # this task's to fix -- but recorded so it isn't only found by eye.
    print(f"\n{len(short)} sync shots under-verified: {short}")


def test_best_run_prefers_the_run_that_contains_the_bite_in_point():
    """Reproduces i=32 (colin_why_he_started) verbatim: a short run at
    754.71 that actually covers src_t0=755.96, and a longer run at 760.68
    (saturated at usable=6.0, the MAX_SHOT cap -- this dataset's common
    case, not a synthetic edge value) that starts after the words already
    began. The old "longest usable wins" rule picked 760.68 and discarded
    the one run that covers the in-point; that was the bug."""
    from flow_plan import best_run
    bite = {"sync_possible": True, "src_t0": 755.96, "runs": [
        {"key": "a@754.71", "t0": 754.71, "run_end": 758.72, "usable": 4.01,
         "verified_jimmy": True, "has_text": False},
        {"key": "a@760.68", "t0": 760.68, "run_end": 769.15, "usable": 6.0,
         "verified_jimmy": True, "has_text": False},
    ]}
    assert best_run(bite)["key"] == "a@754.71"


def test_best_run_breaks_a_saturated_tie_by_usable_then_list_order():
    """Two runs both capped at usable=6.0 and neither containing src_t0 --
    the common real shape (16 of 26 verified runs in bite_windows.json sit
    at exactly 6.0). With no run to prefer by containment, the longest-
    usable fallback is a tie, and Python's max() returns the first maximal
    element -- documented here as the actual, not incidental, behaviour."""
    from flow_plan import best_run
    bite = {"sync_possible": True, "src_t0": 100.0, "runs": [
        {"key": "first@6.0", "t0": 110.0, "run_end": 116.0, "usable": 6.0,
         "verified_jimmy": True, "has_text": False},
        {"key": "second@6.0", "t0": 120.0, "run_end": 126.0, "usable": 6.0,
         "verified_jimmy": True, "has_text": False},
    ]}
    assert best_run(bite)["key"] == "first@6.0"


def test_best_run_falls_back_to_longest_usable_when_nothing_contains_src_t0():
    from flow_plan import best_run
    bite = {"sync_possible": True, "src_t0": 500.0, "runs": [
        {"key": "a@1", "t0": 1.0, "run_end": 3.8, "usable": 2.8,
         "verified_jimmy": True, "has_text": False},
        {"key": "a@9", "t0": 9.0, "run_end": 14.1, "usable": 5.1,
         "verified_jimmy": True, "has_text": False},
        {"key": "a@4", "t0": 4.0, "run_end": 13.9, "usable": 9.9,
         "verified_jimmy": True, "has_text": True},
    ]}
    assert best_run(bite)["key"] == "a@9"


def test_best_run_returns_none_when_nothing_is_verified():
    from flow_plan import best_run
    assert best_run({"sync_possible": True, "runs": [
        {"key": "a@1", "t0": 1.0, "usable": 9.0,
         "verified_jimmy": False, "has_text": False}]}) is None
