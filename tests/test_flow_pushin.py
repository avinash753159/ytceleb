import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_pushin import (  # noqa: E402
    EASES,
    _assert_frames_complete,
    ease_cosine,
    ease_smoothstep,
    frame_count,
    layer_scale,
    layer_travel,
)

ALL_EASES = [ease_smoothstep, ease_cosine]


# ------------------------------------------------------------------ easing

@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_easing_starts_at_zero_ends_at_one(ease_fn):
    assert ease_fn(0.0) == pytest.approx(0.0, abs=1e-9)
    assert ease_fn(1.0) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_easing_is_monotonic(ease_fn):
    xs = [i / 200 for i in range(201)]
    ys = [ease_fn(x) for x in xs]
    assert all(b >= a - 1e-12 for a, b in zip(ys, ys[1:]))


@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_easing_derivative_near_zero_at_both_ends(ease_fn):
    # "Eased" means zero velocity at the ends - a push that starts/stops at
    # constant speed reads as a cut, not a camera move.
    h = 1e-4
    d_start = (ease_fn(h) - ease_fn(0.0)) / h
    d_end = (ease_fn(1.0) - ease_fn(1.0 - h)) / h
    assert abs(d_start) < 0.01
    assert abs(d_end) < 0.01


def test_unknown_ease_name_not_registered():
    assert "linear" not in EASES
    assert set(EASES) == {"smoothstep", "cosine"}


# ------------------------------------------------------------ layer ramps

def test_nearest_layer_travels_further_than_farthest():
    far = layer_travel(0.0, 1.06, 1.22, layer_gain=0.55)
    near = layer_travel(1.0, 1.06, 1.22, layer_gain=0.55)
    assert near > far


def test_zero_gain_collapses_to_flat_zoom():
    travels = [layer_travel(d, 1.06, 1.22, layer_gain=0.0)
               for d in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert all(t == pytest.approx(travels[0]) for t in travels)


def test_more_gain_separates_layers_more():
    spread_low = (layer_travel(1.0, 1.06, 1.22, 0.2)
                  - layer_travel(0.0, 1.06, 1.22, 0.2))
    spread_high = (layer_travel(1.0, 1.06, 1.22, 0.8)
                   - layer_travel(0.0, 1.06, 1.22, 0.8))
    assert spread_high > spread_low


# ------------------------------------------------------------ frame counts

@pytest.mark.parametrize("seconds,expected", [
    (2.0, 48),
    (4.58, 110),
    (9.95, 239),
    (6.0, 144),
    (1.0, 24),
    (0.5, 12),
])
def test_frame_count_arithmetic(seconds, expected):
    assert frame_count(seconds) == expected == round(seconds * 24)


# -------------------------------------------------------------- no edges

def test_scale_never_drops_below_one_across_layers_and_time():
    start_scale = 1.06
    for depth in (0.0, 0.33, 0.5, 0.66, 1.0):
        for i in range(51):
            t = i / 50
            for ease_fn in ALL_EASES:
                s = layer_scale(depth, t, start_scale, 1.22, 0.55, ease_fn)
                assert s >= 1.0


def test_scale_starts_at_exactly_start_scale():
    for depth in (0.0, 0.5, 1.0):
        s = layer_scale(depth, 0.0, 1.06, 1.22, 0.55, ease_smoothstep)
        assert s == pytest.approx(1.06)


# ---------------------------------------------------------- frame integrity

def test_missing_frame_raises_file_not_found(tmp_path):
    n = 10
    for i in range(n):
        if i == 5:
            continue  # deliberate gap
        (tmp_path / f"{i:06d}.png").write_bytes(b"fake-png-bytes")
    with pytest.raises(FileNotFoundError):
        _assert_frames_complete(tmp_path, n)


def test_complete_sequence_does_not_raise(tmp_path):
    n = 6
    for i in range(n):
        (tmp_path / f"{i:06d}.png").write_bytes(b"fake-png-bytes")
    _assert_frames_complete(tmp_path, n)  # must not raise
