import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_assemble import (  # noqa: E402
    FPS,
    OUT_H,
    OUT_W,
    TAIL_FRAMES,
    TOTAL_FRAMES,
    _parse_frame_count,
    fingerprint,
    piece_path,
    render_piece,
    select_range,
)

ROOT = Path(__file__).resolve().parent.parent
SHOTS = json.loads(
    (ROOT / "manifest/flow_shots.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------- format ---

def test_locked_output_format():
    assert FPS == 24
    assert (OUT_W, OUT_H) == (1920, 1080)


# ---------------------------------------------------- frame arithmetic ---

def test_total_frames_covers_the_whole_audio():
    # 118 gen + 17 sync shots sum to exactly 17667 frames (Task 4 ruling 3);
    # the audio master runs ~2.48s longer than the last shot's picture, so
    # a 60-frame (2.5s) silent/faded tail is appended to reach it.
    assert TOTAL_FRAMES == 17727
    assert TAIL_FRAMES == 60


def test_shot_frames_plus_tail_equal_the_total():
    assert sum(s["frames"] for s in SHOTS) + TAIL_FRAMES == TOTAL_FRAMES


def test_select_range_whole_film_includes_the_tail():
    selected, from_frame, to_frame, tail_frames = select_range(
        SHOTS, 0.0, None)
    assert selected == SHOTS
    assert from_frame == 0
    assert to_frame == TOTAL_FRAMES
    assert tail_frames == TAIL_FRAMES


def test_select_range_partial_range_is_frame_exact_and_tailless():
    """The owner's actual first deliverable: 0..63.75s, the first 14
    shots. No tail -- the range ends mid-film, not at the audio's end."""
    selected, from_frame, to_frame, tail_frames = select_range(
        SHOTS, 0.0, 63.75)
    assert [s["shot_id"] for s in selected] == [
        "s_lead", "s000a", "s000b", "s001s", "s002a", "s002b", "s003a",
        "s003b", "s004a", "s005a", "s005b", "s006s", "s_break", "s007a",
    ]
    assert from_frame == 0
    assert to_frame == 1530                       # round(63.75 * 24)
    assert sum(s["frames"] for s in selected) == 1530
    assert tail_frames == 0


def test_select_range_a_mid_film_slice_not_starting_at_zero():
    # s001s starts at 11.875s and s006s ends at 54.08333...s -- both land
    # on shot boundaries in the real manifest, so this must not require
    # starting from 0 to be frame-exact.
    selected, from_frame, to_frame, tail_frames = select_range(
        SHOTS, 11.875, 54.083333333333336)
    assert selected[0]["shot_id"] == "s001s"
    assert selected[-1]["shot_id"] == "s006s"
    assert to_frame - from_frame == sum(s["frames"] for s in selected)
    assert tail_frames == 0


def test_select_range_rejects_a_boundary_that_splits_a_shot():
    with pytest.raises(ValueError, match="boundar"):
        select_range(SHOTS, 0.0, 63.5)             # inside s007a, not its end


def test_select_range_rejects_a_tail_overshoot_past_the_silent_pad():
    with pytest.raises(ValueError):
        select_range(SHOTS, 0.0, (TOTAL_FRAMES + 100) / FPS)


# --------------------------------------------------- ffprobe parsing ---

def test_parse_frame_count_handles_the_trailing_comma():
    # ffprobe -count_frames emits "70,\n" for some files -- a trailing
    # comma that makes str.isdigit() false on the raw line.
    assert _parse_frame_count("70,\n") == 70


def test_parse_frame_count_handles_a_bare_integer():
    assert _parse_frame_count("136\n") == 136


def test_parse_frame_count_raises_on_no_digits():
    with pytest.raises(ValueError):
        _parse_frame_count("N/A\n")


# --------------------------------------------------- fingerprint/cache ---

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


def test_piece_path_differs_when_frames_change():
    a = piece_path({"shot_id": "s000a", "prompt": "one", "frames": 100,
                     "kind": "gen"})
    b = piece_path({"shot_id": "s000a", "prompt": "one", "frames": 101,
                     "kind": "gen"})
    assert a != b


def test_piece_path_differs_when_a_sync_shot_source_cut_point_changes():
    """A sync shot's real content is which stretch of the source video it
    cuts -- src_t0 -- not the shot's name. If bite_windows re-derives a
    different in-point, the cache must not serve the old cut."""
    base = {"shot_id": "s001s", "kind": "sync", "frames": 51,
            "source": "cLRLEnPaJLM", "src_t0": 5265.4}
    moved = dict(base, src_t0=5266.0)
    assert piece_path(base) != piece_path(moved)


def test_fingerprint_is_a_short_hex_string():
    fp = fingerprint({"shot_id": "s000a", "prompt": "one", "frames": 100,
                       "kind": "gen"})
    assert len(fp) == 12
    int(fp, 16)                                    # does not raise


# ------------------------------------------------------ loud failures ---

def test_render_piece_raises_naming_the_shot_when_gen_clip_is_missing(
        tmp_path, monkeypatch):
    import flow_assemble
    monkeypatch.setattr(flow_assemble, "VEO", tmp_path / "no_such_dir")
    monkeypatch.setattr(flow_assemble, "PIECES", tmp_path / "pieces")
    shot = {"shot_id": "s999_missing", "kind": "gen", "prompt": "x",
            "frames": 10}
    with pytest.raises(SystemExit, match="s999_missing"):
        render_piece(shot, gen_status={"s999_missing": {"state": "done"}})


def test_render_piece_raises_naming_the_shot_when_gen_state_is_not_done(
        tmp_path, monkeypatch):
    import flow_assemble
    # File exists on disk, but the ledger never marked it "done" -- a
    # leftover/partial file from a killed run must not be trusted.
    veo = tmp_path / "veo"
    veo.mkdir()
    (veo / "s999_notdone.mp4").write_bytes(b"not really a video")
    monkeypatch.setattr(flow_assemble, "VEO", veo)
    monkeypatch.setattr(flow_assemble, "PIECES", tmp_path / "pieces")
    shot = {"shot_id": "s999_notdone", "kind": "gen", "prompt": "x",
            "frames": 10}
    with pytest.raises(SystemExit, match="s999_notdone"):
        render_piece(shot, gen_status={"s999_notdone": {"state": "failed"}})


def test_render_piece_raises_naming_the_shot_when_sync_source_is_missing(
        tmp_path, monkeypatch):
    import flow_assemble
    monkeypatch.setattr(flow_assemble, "SRC", tmp_path / "no_such_sources")
    monkeypatch.setattr(flow_assemble, "PIECES", tmp_path / "pieces")
    shot = {"shot_id": "s999_sync", "kind": "sync", "source": "nope",
            "src_t0": 1.0, "frames": 10}
    with pytest.raises(SystemExit, match="s999_sync"):
        render_piece(shot)
