import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pytest  # noqa: E402

import flow_gen  # noqa: E402
from flow_gen import (  # noqa: E402
    MODEL,
    NEGATIVE_PROMPT,
    RATE_PER_SECOND,
    ROOT,
    SHOTS,
    build_config,
    estimate_cost,
    generate_one,
    pending,
    record,
    run,
    seed_for,
)


def mk(shot_id, gen_dur=6, kind="gen", prompt="a prompt, no text, no logos"):
    return {"shot_id": shot_id, "gen_dur": gen_dur, "kind": kind, "prompt": prompt}


# ------------------------------------------------------- fake API client ---
#
# None of these ever touch the network. They simulate the two ways the
# review found the previous version could burn real money without the
# ledger noticing: a systemically wrong response shape (every submission
# "succeeds" at Google, every local parse fails) and a download-only
# failure (generation succeeded and was billed once; only retrieval failed).

class FakeVideo:
    """Stand-in for a generated_videos[0].video handle."""

    def __init__(self, save_effects=None):
        # One exception (or None) per call to .save(), consumed in order.
        self._effects = list(save_effects or [])
        self.save_calls = 0

    def save(self, path):
        self.save_calls += 1
        if self._effects:
            effect = self._effects.pop(0)
            if effect is not None:
                raise effect
        Path(path).write_bytes(b"fake-mp4-bytes")


class FakeGeneratedVideo:
    """generated_videos[i] carries the downloadable handle on `.video`,
    mirroring the real SDK's shape (`generated_videos[0].video`)."""

    def __init__(self, video):
        self.video = video


class FakeResponse:
    def __init__(self, videos):
        self.generated_videos = [FakeGeneratedVideo(v) for v in videos]


class FakeOpOK:
    """A completed operation with a correctly-shaped response."""

    def __init__(self, videos):
        self.done = True
        self.error = None
        self.response = FakeResponse(videos)


class FakeOpBadShape:
    """Simulates a wrongly-named SDK attribute: no `.done` at all, so the
    very first thing submission polling touches raises AttributeError --
    exactly the failure mode the review traced to a cap-defeating runaway.
    """


class FakeModels:
    def __init__(self, make_op):
        self.calls = 0
        self._make_op = make_op

    def generate_videos(self, **kwargs):
        self.calls += 1
        return self._make_op()


class FakeOperations:
    def get(self, op):
        return op


class FakeFiles:
    def download(self, file):
        pass  # the real SDK mutates `file` in place; nothing to do here


class FakeClient:
    def __init__(self, make_op):
        self.models = FakeModels(make_op)
        self.operations = FakeOperations()
        self.files = FakeFiles()

    @property
    def generate_calls(self):
        return self.models.calls


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


# --------------------------------------------------- charge at submission ---
# Fix round 1: the ledger must count what Google charges for, not what the
# local client managed to parse. These simulate the two failure shapes the
# review traced and assert the cap/circuit-breaker fixes actually hold.

def test_cap_stops_before_any_submission_is_made(tmp_path):
    """With the cap set below one shot's cost, zero calls to
    generate_videos should happen at all -- the cap must stop submission,
    not merely stop counting it as spent afterwards."""
    client = FakeClient(lambda: FakeOpOK([FakeVideo()]))
    shots = [mk("a", gen_dur=8)]        # cost = $0.40
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    code = run(shots, tmp_path / "status.json", client, cap=0.10,
               out_dir=out_dir)

    assert client.generate_calls == 0
    assert code == 0


def test_systemic_response_shape_bug_halts_within_the_circuit_breaker(
        tmp_path, monkeypatch, capsys):
    """A fake client whose generate_videos "succeeds" (Google would bill
    for it) but whose op has no `.done` -- simulating a response shape the
    code guessed wrong. Real money would be committed on every one of these
    calls. The run must halt after CIRCUIT_BREAKER_STREAK consecutive shot
    failures, not grind through the whole backlog, and the printed spend
    must reflect the submissions actually made, never $0.00."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    client = FakeClient(lambda: FakeOpBadShape())
    shots = [mk(f"s{i}", gen_dur=6) for i in range(118)]
    status_path = tmp_path / "status.json"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    code = run(shots, status_path, client, cap=100.0, out_dir=out_dir)

    assert code == 1
    status = json.loads(status_path.read_text(encoding="utf-8"))
    # stopped within 3 shots, not all 118
    assert len(status) == flow_gen.CIRCUIT_BREAKER_STREAK
    assert all(v["state"] == "failed" for v in status.values())

    submissions_per_shot = flow_gen.SUBMIT_RETRIES + 1
    assert client.generate_calls == (
        flow_gen.CIRCUIT_BREAKER_STREAK * submissions_per_shot)

    out = capsys.readouterr().out
    spent_line = [ln for ln in out.splitlines()
                  if ln.startswith("spent $")][-1]
    spent = float(spent_line.removeprefix("spent $"))
    expected = (flow_gen.CIRCUIT_BREAKER_STREAK * submissions_per_shot
                * 6 * RATE_PER_SECOND)
    assert spent == pytest.approx(expected)
    assert spent > 0, "spend must reflect real submissions, never $0.00"


def test_download_failure_retries_the_download_not_the_generation(
        tmp_path, monkeypatch):
    """Generation succeeds (one billable job); only the save() step fails
    once. The fix must retry the download alone against the operation it
    already has -- never call generate_videos a second time for content
    that was already produced and billed."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    video = FakeVideo(save_effects=[OSError("transient disk error"), None])
    client = FakeClient(lambda: FakeOpOK([video]))
    shot = mk("s_only", gen_dur=6)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    dest = generate_one(client, shot, out_dir)

    assert client.generate_calls == 1      # exactly one submission
    assert video.save_calls == 2           # download retried once, alone
    assert dest.exists()


def test_a_shot_needing_two_submissions_is_charged_twice(
        tmp_path, monkeypatch):
    """The other half of charge-at-submission: on_submit fires once per
    submission attempt, so a shot that failed once before succeeding must
    show two charges, not one."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def make_op():
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeOpBadShape()    # first submission looks broken
        return FakeOpOK([FakeVideo()])  # second submission succeeds

    client = FakeClient(make_op)
    shot = mk("s_retry", gen_dur=6)
    charges = []

    def on_submit():
        charges.append(shot["gen_dur"] * RATE_PER_SECOND)

    dest = generate_one(client, shot, tmp_path, on_submit=on_submit)

    assert client.generate_calls == 2
    assert len(charges) == 2
    assert dest.exists()


# ---------------------------------------------------- guarded record() ---

def test_record_recovers_from_a_transient_permission_error(
        tmp_path, monkeypatch):
    """Simulates Windows antivirus/backup-indexer transiently holding the
    destination file (WinError 32): the first rename fails, the second
    succeeds, and the entry must land rather than being lost."""
    calls = {"n": 0}
    real_replace = Path.replace

    def flaky_replace(self, target):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("WinError 32 simulated")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)
    p = tmp_path / "status.json"

    record(p, "s000a", state="done", path="x.mp4")

    got = json.loads(p.read_text(encoding="utf-8"))
    assert got["s000a"]["state"] == "done"
    assert calls["n"] == 2


def test_record_raises_loudly_if_replace_never_succeeds(
        tmp_path, monkeypatch):
    """A paid success must never go unrecorded silently: if every rename
    attempt fails, record() must raise, naming the shot, not swallow it."""
    def always_fail(self, target):
        raise PermissionError("WinError 32 simulated")

    monkeypatch.setattr(Path, "replace", always_fail)
    p = tmp_path / "status.json"

    with pytest.raises(RuntimeError, match="s000a"):
        record(p, "s000a", state="done")
