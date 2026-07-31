import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

from flow_gen import (  # noqa: E402
    MODEL,
    NEGATIVE_PROMPT,
    RATE_PER_SECOND,
    ROOT,
    SHOTS,
    build_config,
    estimate_cost,
    pending,
    record,
    seed_for,
)


def mk(shot_id, gen_dur=6, kind="gen", prompt="a prompt, no text, no logos"):
    return {"shot_id": shot_id, "gen_dur": gen_dur, "kind": kind, "prompt": prompt}


# ---------------------------------------------------------------- budget ---

def test_estimate_cost_counts_only_generated_shots():
    shots = [mk("a", 6), mk("b", 4), mk("c", 0, kind="sync")]
    assert estimate_cost(shots) == pytest.approx(10 * RATE_PER_SECOND)


def test_estimate_cost_of_the_full_film():
    assert estimate_cost([mk(str(i), 6) for i in range(100)]) == pytest.approx(30.0)


def test_real_manifest_matches_the_known_budget():
    """Regression check: 118 gen shots, 658s, $32.90 -- the numbers this
    task's dry-run is required to print. If the manifest ever changes shape,
    this is the trip-wire before a live run bills the wrong amount."""
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    gen = [s for s in shots if s.get("kind") == "gen"]
    assert len(gen) == 118
    assert estimate_cost(shots) == pytest.approx(32.90)


# --------------------------------------------------------------- pending ---

def test_pending_skips_completed_shots():
    shots = [mk("a"), mk("b"), mk("c")]
    status = {"a": {"state": "done"}, "b": {"state": "failed"}}
    assert [s["shot_id"] for s in pending(shots, status)] == ["b", "c"]


def test_pending_skips_sync_shots():
    shots = [mk("a"), mk("b", kind="sync")]
    assert [s["shot_id"] for s in pending(shots, {})] == ["a"]


# ------------------------------------------------------------- recording ---

def test_record_is_atomic_and_readable(tmp_path):
    p = tmp_path / "status.json"
    record(p, "s000a", state="done", path="x.mp4")
    record(p, "s000b", state="failed", error="boom")
    got = json.loads(p.read_text(encoding="utf-8"))
    assert got["s000a"]["state"] == "done"
    assert got["s000b"]["error"] == "boom"


def test_record_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "status.json"
    record(p, "s000a", state="done")
    assert [f.name for f in tmp_path.iterdir()] == ["status.json"]


def test_record_preserves_earlier_entries(tmp_path):
    p = tmp_path / "status.json"
    for i in range(5):
        record(p, f"s{i:03d}", state="done")
    assert len(json.loads(p.read_text(encoding="utf-8"))) == 5


def test_record_never_silently_drops_a_failed_shot(tmp_path):
    """A previous module in this repo silently dropped 14 entries with
    `if not p.exists(): continue`. A failed shot must show up as `failed`,
    never vanish from the ledger."""
    p = tmp_path / "status.json"
    record(p, "s000a", state="failed", error="timeout")
    got = json.loads(p.read_text(encoding="utf-8"))
    assert got["s000a"]["state"] == "failed"


# -------------------------------------------------------------- seeding ---

def test_seed_is_deterministic_for_the_same_shot_id():
    assert seed_for("s042") == seed_for("s042")


def test_seed_differs_across_shot_ids():
    assert seed_for("s042") != seed_for("s043")


def test_seed_is_a_nonnegative_int():
    s = seed_for("s_lead")
    assert isinstance(s, int)
    assert s >= 0


# ---------------------------------------------------------- config shape ---

def test_build_config_disables_generated_audio():
    cfg = build_config(mk("a"))
    assert cfg.generate_audio is False


def test_build_config_carries_the_negative_prompt():
    cfg = build_config(mk("a"))
    assert cfg.negative_prompt == NEGATIVE_PROMPT


def test_build_config_seeds_from_the_shot_id():
    shot = mk("s042")
    cfg = build_config(shot)
    assert cfg.seed == seed_for("s042")


def test_build_config_uses_the_locked_format():
    cfg = build_config(mk("a", gen_dur=8))
    assert cfg.aspect_ratio == "16:9"
    assert cfg.resolution == "720p"
    assert cfg.duration_seconds == 8
    assert cfg.number_of_videos == 1


def test_build_config_does_not_set_fps():
    """Task 7 verifies 24fps output empirically; fps is only passed here if
    the model is confirmed to honour it, which has not been done."""
    cfg = build_config(mk("a"))
    assert cfg.fps is None


def test_model_and_negative_prompt_constants():
    assert MODEL == "veo-3.1-lite-generate-preview"
    assert NEGATIVE_PROMPT == (
        "text, letters, words, subtitles, captions, watermark, logo, "
        "brand name, signage, on-screen graphics, timestamp, numbers"
    )
