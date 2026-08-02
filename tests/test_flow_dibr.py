"""Tests for the DIBR parallax renderer.

Every test here runs without the depth model and without a render: the
camera maths, the hole fill and the frame contract are all pure functions of
numpy arrays, so they are cheap to check and they are where the two defects
the owner reported actually live.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_dibr import (  # noqa: E402
    EASES,
    OVERFILL,
    _assert_frames_complete,
    _fill_disparity_holes,
    backward_maps,
    check_drift_fits,
    ease_cosine,
    ease_smoothstep,
    frame_count,
    radial_gain,
    warp,
)

ALL_EASES = [ease_smoothstep, ease_cosine]


# ------------------------------------------------------------------ easing

@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_easing_starts_at_zero_ends_at_one(ease_fn):
    assert ease_fn(0.0) == pytest.approx(0.0, abs=1e-9)
    assert ease_fn(1.0) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_easing_is_monotonic(ease_fn):
    ys = [ease_fn(i / 200) for i in range(201)]
    assert all(b >= a - 1e-12 for a, b in zip(ys, ys[1:]))


@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_easing_derivative_near_zero_at_both_ends(ease_fn):
    # A move that starts or stops at constant speed reads as a cut with a
    # zoom stapled on, not as a camera.
    h = 1e-4
    assert abs((ease_fn(h) - ease_fn(0.0)) / h) < 0.01
    assert abs((ease_fn(1.0) - ease_fn(1.0 - h)) / h) < 0.01


def test_only_eased_curves_are_registered():
    assert "linear" not in EASES
    assert set(EASES) == {"smoothstep", "cosine"}


# --------------------------------------------------------- displacement law

def test_near_depth_is_magnified_more_than_far_depth():
    near = radial_gain(0.9, dz=1.0, strength=0.06)
    far = radial_gain(0.1, dz=1.0, strength=0.06)
    assert float(near) > float(far)


def test_gain_is_strictly_increasing_in_depth():
    gains = [float(radial_gain(d, dz=1.0, strength=0.06))
             for d in np.linspace(0.0, 1.0, 21)]
    assert all(b > a for a, b in zip(gains, gains[1:]))


def test_zero_strength_is_a_flat_zoom_for_every_depth():
    gains = [float(radial_gain(d, dz=1.0, strength=0.0, zoom=1.1))
             for d in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert all(g == pytest.approx(1.1) for g in gains)


def test_near_pixel_displaced_strictly_further_than_far_pixel():
    """Same column, different depth: the near row must travel further.

    A vertical depth ramp keeps the horizontal radius identical between the
    two sample points, so any difference in horizontal displacement is due
    to depth alone. This is the property band-splitting only got at three
    discrete values and DIBR gets at every pixel.
    """
    h, w = 64, 96
    depth = np.tile(np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None],
                    (1, w))
    mx, _ = backward_maps(depth, dz=1.0, strength=0.06)
    xx = np.arange(w, dtype=np.float32)[None, :]
    disp = np.abs(mx - xx)

    col = 4  # well off-axis; displacement is radial so it is zero at centre
    rows = [0, 15, 31, 47, 63]
    vals = [float(disp[r, col]) for r in rows]
    assert all(b > a for a, b in zip(vals, vals[1:])), vals
    assert vals[-1] > vals[0]


def test_warp_with_zero_strength_is_identity():
    rng = np.random.default_rng(7)
    rgb = rng.integers(0, 255, (48, 64, 3), dtype=np.uint8)
    depth = np.tile(np.linspace(0.0, 1.0, 48, dtype=np.float32)[:, None],
                    (1, 64))
    out = warp(rgb, depth, dz=1.0, strength=0.0, zoom=1.0)
    assert out.shape == rgb.shape
    assert np.abs(out.astype(int) - rgb.astype(int)).max() <= 1


def test_warp_actually_moves_pixels_when_strength_is_nonzero():
    rng = np.random.default_rng(11)
    rgb = rng.integers(0, 255, (48, 64, 3), dtype=np.uint8)
    depth = np.tile(np.linspace(0.0, 1.0, 48, dtype=np.float32)[:, None],
                    (1, 64))
    out = warp(rgb, depth, dz=1.0, strength=0.10, zoom=1.0)
    assert np.abs(out.astype(int) - rgb.astype(int)).mean() > 1.0


def test_maps_are_float32_and_subpixel():
    """Sub-pixel coordinates are the fix for the reported judder.

    If any map value were rounded to a whole pixel the move would advance in
    integer jumps - exactly the shake the band version had.
    """
    depth = np.tile(np.linspace(0.0, 1.0, 40, dtype=np.float32)[:, None],
                    (1, 60))
    mx, my = backward_maps(depth, dz=0.37, strength=0.06, zoom=1.03)
    assert mx.dtype == np.float32 and my.dtype == np.float32
    frac = np.abs(mx - np.rint(mx))
    assert frac.max() > 0.05, "map is integral - resampling would judder"


# ----------------------------------------------------------------- jitter
#
# This is the test that would have caught the shipped bug: the old renderer
# rounded its crop box to whole pixels every frame, so displacement advanced
# in staircase steps instead of a smooth curve.

def _displacement_series(n_frames, ease_fn, strength=0.06, zoom=1.10):
    h, w = 32, 48
    depth = np.full((h, w), 0.75, np.float32)
    xx = np.arange(w, dtype=np.float32)[None, :]
    out = []
    for i in range(n_frames):
        t = i / (n_frames - 1)
        e = ease_fn(t)
        mx, _ = backward_maps(depth, dz=e, strength=strength,
                              zoom=OVERFILL * (1.0 + (zoom - 1.0) * e))
        out.append(float((mx - xx)[16, 2]))
    return out


@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_displacement_has_no_per_frame_jitter(ease_fn):
    """No frame may deviate from the average of its neighbours.

    On a smooth curve the second difference is O(1/n^2) and vanishing; a
    single rounded coordinate anywhere would spike it to ~1 pixel.
    """
    n = 144  # a 6s shot at 24fps
    xs = _displacement_series(n, ease_fn)
    worst = max(abs(xs[i] - 0.5 * (xs[i - 1] + xs[i + 1]))
                for i in range(1, n - 1))
    assert worst < 0.01, f"per-frame jitter of {worst:.4f}px"


@pytest.mark.parametrize("ease_fn", ALL_EASES)
def test_displacement_is_monotonic_and_never_stalls(ease_fn):
    n = 144
    xs = _displacement_series(n, ease_fn)
    deltas = [b - a for a, b in zip(xs, xs[1:])]
    assert all(d >= -1e-6 for d in deltas), "displacement reversed mid-move"
    # A staircase would show as runs of exactly-zero delta between jumps.
    assert sum(1 for d in deltas if abs(d) < 1e-9) < 4


def test_rounded_displacement_would_fail_the_jitter_test():
    """Sanity check on the test itself: the defect it targets is detectable.

    Rounding the same series to whole pixels - what the band version did -
    must blow the tolerance the smooth series passes.
    """
    xs = [round(x) for x in _displacement_series(144, ease_smoothstep)]
    worst = max(abs(xs[i] - 0.5 * (xs[i - 1] + xs[i + 1]))
                for i in range(1, 143))
    assert worst >= 0.01


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


# --------------------------------------------------------------- hole fill

def test_hole_fill_leaves_no_unresolved_cells():
    dst = np.full((40, 60), 0.8, np.float32)
    dst[10:20, 5:8] = 0.2          # background actually present
    holes = np.zeros((40, 60), bool)
    holes[10:20, 8:14] = True      # disocclusion beside it
    dst[holes] = -1.0
    filled, residual = _fill_disparity_holes(dst, holes)
    assert (filled >= 0).all()
    assert filled.max() < 1e3, "sentinel leaked into the disparity field"
    assert residual.sum() == 0


def test_hole_fill_prefers_background_disparity():
    """A revealed gap must show what is BEHIND, not the near surface.

    Filling with the nearest neighbour would drag the foreground into the
    gap and read as a smeared duplicate of the subject.
    """
    dst = np.full((30, 40), 0.9, np.float32)   # near everywhere
    dst[:, 10] = 0.1                            # a strip of background
    holes = np.zeros((30, 40), bool)
    holes[:, 11:14] = True
    dst[holes] = -1.0
    filled, _ = _fill_disparity_holes(dst, holes)
    assert filled[15, 11] == pytest.approx(0.1)
    assert filled[15, 13] == pytest.approx(0.1)


def test_hole_fill_survives_a_gap_wider_than_the_first_kernel():
    dst = np.full((240, 320), 0.5, np.float32)
    holes = np.zeros((240, 320), bool)
    holes[60:180, 60:180] = True   # 120px wide, far past the 7px pass
    dst[holes] = -1.0
    filled, residual = _fill_disparity_holes(dst, holes)
    assert (filled >= 0).all()
    assert filled.max() < 1e3
    assert residual.sum() == 0


def test_isolated_sampling_gaps_take_the_NEAREST_surface():
    """Magnification leaves a lattice of empty cells that is not occlusion.

    Filling those with background disparity - which is right for a real
    disocclusion - drags a quarter of the depth field toward the far plane
    and measurably flattens the parallax. They must take the near value.
    """
    dst = np.full((40, 40), 0.9, np.float32)   # a near surface
    dst[:, 0] = 0.1                             # a far strip at the edge
    holes = np.zeros((40, 40), bool)
    holes[10, 20] = holes[12, 24] = holes[30, 8] = True   # isolated cells
    dst[holes] = -1.0
    filled, residual = _fill_disparity_holes(dst, holes)
    assert filled[10, 20] == pytest.approx(0.9)
    assert filled[12, 24] == pytest.approx(0.9)
    assert residual.sum() == 0


def test_a_wide_band_is_still_treated_as_disocclusion_not_a_gap():
    """The near/far discriminator must not swallow real disocclusions."""
    dst = np.full((30, 40), 0.9, np.float32)
    dst[:, 10] = 0.1
    holes = np.zeros((30, 40), bool)
    holes[:, 11:14] = True      # 3px band - too wide to be a sampling gap
    dst[holes] = -1.0
    filled, _ = _fill_disparity_holes(dst, holes)
    assert filled[15, 12] == pytest.approx(0.1)


def test_hole_fill_is_a_noop_when_there_are_no_holes():
    dst = np.full((16, 16), 0.4, np.float32)
    filled, residual = _fill_disparity_holes(dst, np.zeros((16, 16), bool))
    assert np.array_equal(filled, dst)
    assert residual.sum() == 0


# --------------------------------------------------------------- edge guard

def test_drift_within_the_zoom_margin_is_accepted():
    check_drift_fits(1.30, (0.5, 0.0), 0.06, ease_smoothstep)


def test_drift_that_would_expose_an_edge_is_rejected():
    with pytest.raises(ValueError, match="exposed edge"):
        check_drift_fits(1.01, (8.0, 0.0), 0.06, ease_smoothstep)


def test_zero_drift_always_fits():
    check_drift_fits(1.0, (0.0, 0.0), 0.5, ease_smoothstep)


# ---------------------------------------------------------- frame integrity

def test_missing_frame_raises_rather_than_encoding_short(tmp_path):
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
    _assert_frames_complete(tmp_path, n)


def test_shape_mismatch_between_picture_and_depth_is_rejected():
    rgb = np.zeros((32, 32, 3), np.uint8)
    with pytest.raises(ValueError, match="same size"):
        warp(rgb, np.zeros((16, 16), np.float32), dz=1.0)
