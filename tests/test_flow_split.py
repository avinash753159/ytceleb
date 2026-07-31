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


def test_allocate_frames_never_returns_zero_even_with_skewed_weights():
    """max(1, floor(x)) can overshoot the total; the correction must not
    claw frames back from a shot that was already clamped to the floor."""
    got = allocate_frames(10, [8.0, 0.1, 0.1, 0.1])
    assert sum(got) == 10
    assert all(f >= 1 for f in got), got


def test_allocate_frames_rejects_impossible_allocation():
    """Cannot allocate N frames to M shots if N < M (minimum 1 per shot)."""
    with pytest.raises(ValueError):
        allocate_frames(3, [1.0, 1.0, 1.0, 1.0])


def test_allocate_frames_survives_many_clamped_indices():
    """A rotation computed once cannot know an index ran out of capacity.
    This input drove a count to -1 under the round-robin correction."""
    got = allocate_frames(24, [2.9, 20.9] + [0.05] * 8)
    assert sum(got) == 24
    assert all(f >= 1 for f in got), got


def test_allocate_frames_is_never_negative_under_fuzz():
    """Fuzz test: capacity-aware correction cannot produce negative frames."""
    import random
    rng = random.Random(20260731)
    for _ in range(2000):
        n = rng.randint(1, 12)
        weights = [rng.choice([0.05, 0.1, 1.0, 3.0, 20.0]) for _ in range(n)]
        total = rng.randint(n, 200)
        got = allocate_frames(total, weights)
        assert sum(got) == total, (total, weights, got)
        assert all(f >= 1 for f in got), (total, weights, got)


def test_zero_length_segment_is_rejected():
    with pytest.raises(ValueError):
        split_segment(10.0, 10.0)
