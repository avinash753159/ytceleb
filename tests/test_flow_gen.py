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
    load_key,
    pending,
    record,
    run,
)

# Round 4: the only fields the Developer API tier this project's key runs
# under actually accepts. Every other field this pipeline once set on
# GenerateVideosConfig (seed, generate_audio, negative_prompt,
# person_generation) is Enterprise/Vertex-only and raises client-side.
ALLOWED_CONFIG_FIELDS = {
    "number_of_videos", "duration_seconds", "aspect_ratio", "resolution",
}


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


# ---------------------------------------------------------- config shape ---
#
# Round 4: seed, generate_audio, negative_prompt and person_generation were
# ALL rejected client-side by the Developer API tier this project's key runs
# under -- discovered two live runs at a time (round 3: seed; round 4:
# generate_audio) after the same root cause (reading GenerateVideosConfig's
# full field list without checking the tier). build_config now sends only
# the accepted fields; seed_for() was deleted since nothing calls it once
# it's no longer recorded as ledger provenance either.

def test_build_config_sends_only_developer_api_fields():
    """seed, generate_audio, negative_prompt, person_generation, fps and
    others are Vertex/Enterprise-only; the Developer API raises ValueError
    client-side before the request is sent. This is an explicit allow-list
    assertion so re-adding a rejected field fails in the suite, not on a
    live (if free) call."""
    cfg = build_config(mk("s000a"))
    sent = {k for k, v in cfg.model_dump().items() if v is not None}
    assert sent == ALLOWED_CONFIG_FIELDS, sent


def test_build_config_uses_the_locked_format():
    cfg = build_config(mk("a", gen_dur=8))
    assert cfg.aspect_ratio == "16:9"
    assert cfg.resolution == "720p"
    assert cfg.duration_seconds == 8
    assert cfg.number_of_videos == 1


def test_model_and_negative_prompt_constants():
    assert MODEL == "veo-3.1-lite-generate-preview"
    # NEGATIVE_PROMPT is no longer sent to the API (round 4) -- it is kept
    # as the documented "what we're excluding" text for a later QC step.
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
    """The other half of charge-at-submission: `charge` fires once per
    *accepted* submission attempt (generate_videos() returned without
    raising), so a shot whose first attempt was accepted but then failed
    during polling, before succeeding on a second attempt, must show two
    charges, not one."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def make_op():
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeOpBadShape()    # accepted, but poll access fails
        return FakeOpOK([FakeVideo()])  # second submission succeeds

    client = FakeClient(make_op)
    shot = mk("s_retry", gen_dur=6)
    charges = []

    def charge():
        charges.append(shot["gen_dur"] * RATE_PER_SECOND)

    dest = generate_one(client, shot, tmp_path, charge=charge)

    assert client.generate_calls == 2
    assert len(charges) == 2
    assert dest.exists()


def test_client_side_raise_before_acceptance_charges_nothing(
        tmp_path, monkeypatch):
    """Round 3, defect 2: reproduces the first live run's actual failure --
    `generate_videos()` itself raises (the real one raised
    `ValueError: seed parameter is only supported in Gemini Enterprise
    Agent Platform mode, not in Gemini Developer API mode`, a purely
    client-side validation error). Nothing was ever sent to Google, so
    `charge` must never fire and `spent` must stay at $0.00."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)

    class ExplodingModels:
        def __init__(self):
            self.calls = 0

        def generate_videos(self, **kwargs):
            self.calls += 1
            raise ValueError(
                "seed parameter is only supported in Gemini Enterprise "
                "Agent Platform mode, not in Gemini Developer API mode.")

    class ExplodingClient:
        def __init__(self):
            self.models = ExplodingModels()
            self.operations = FakeOperations()
            self.files = FakeFiles()

    client = ExplodingClient()
    shot = mk("s_boom", gen_dur=6)
    status_path = tmp_path / "status.json"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    run([shot], status_path, client, cap=100.0, out_dir=out_dir)

    # every submission attempt raised before acceptance -- none billed
    assert client.models.calls == flow_gen.SUBMIT_RETRIES + 1
    status = json.loads(status_path.read_text(encoding="utf-8"))
    entry = status["s_boom"]
    assert entry["state"] == "failed"
    assert entry["charged"] == 0.0
    assert entry["submissions"] == 0
    assert "seed parameter" in entry["error"]


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


# -------------------------------------------- fix round 2: cap-stop mid-shot

def test_cap_stop_mid_shot_records_the_interrupted_shot(tmp_path, monkeypatch):
    """Reproduces the round-2 finding exactly: cost $0.30 (a 6s shot), cap
    $0.35. Attempt 1 is accepted (charge fires, $0.30) then fails inside
    submit_and_wait (bad response shape). Attempt 2's check_cap
    (0.30 + 0.30 > 0.35) correctly raises CapReached before a second billed
    call. The shot must not vanish: it needs a ledger entry recording the
    $0.30 already spent on it, WHY the prior attempt failed (round 3), and
    it must still be pending()."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    client = FakeClient(lambda: FakeOpBadShape())
    shot = mk("s_mid", gen_dur=6)          # cost = $0.30
    status_path = tmp_path / "status.json"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    code = run([shot], status_path, client, cap=0.35, out_dir=out_dir)

    assert code == 0
    assert status_path.exists(), "the interrupted shot must be recorded"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert "s_mid" in status
    entry = status["s_mid"]
    assert entry["state"] == "interrupted"      # not done, not failed
    assert entry["charged"] == pytest.approx(0.30)
    assert entry["submissions"] == 1
    assert "done" in entry["error"], (
        "round 3: the interrupted record must say why -- here, the "
        "AttributeError from the bad-shape fake op's missing `.done`")
    assert pending([shot], status) == [shot], (
        "an interrupted shot must still be retried once funding allows")


def test_cap_stop_names_the_interrupted_shot(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    client = FakeClient(lambda: FakeOpBadShape())
    shot = mk("s_named", gen_dur=6)
    status_path = tmp_path / "status.json"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    run([shot], status_path, client, cap=0.35, out_dir=out_dir)

    out = capsys.readouterr().out
    stop_lines = [ln for ln in out.splitlines() if ln.startswith("STOP:")]
    assert stop_lines, "expected a STOP line"
    assert "s_named" in stop_lines[0], (
        "the STOP line must name which shot was mid-flight")


def test_alternating_failures_are_bounded_by_max_total_failures(
        tmp_path, monkeypatch):
    """The consecutive-failure breaker resets on every success, so an
    alternating fail/succeed pattern never reaches a streak of
    CIRCUIT_BREAKER_STREAK and would otherwise be free to burn the whole
    run. MAX_TOTAL_FAILURES is the unconditional backstop: it must trip on
    total failure count regardless of streak."""
    monkeypatch.setattr(flow_gen.time, "sleep", lambda s: None)
    # The successful shots in this test record a `done` path relative to
    # ROOT; point ROOT at tmp_path so that works from an out-of-tree tmpdir.
    monkeypatch.setattr(flow_gen, "ROOT", tmp_path)

    # Each failing shot consumes SUBMIT_RETRIES+1=3 calls (all bad-shape);
    # each succeeding shot consumes exactly 1 (good on the first attempt).
    outcomes = []
    for _ in range(10):
        outcomes += [False, False, False, True]
    outcomes_iter = iter(outcomes)

    def make_op():
        return FakeOpOK([FakeVideo()]) if next(outcomes_iter) \
            else FakeOpBadShape()

    client = FakeClient(make_op)
    shots = [mk(f"s{i}", gen_dur=6) for i in range(40)]
    status_path = tmp_path / "status.json"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    code = run(shots, status_path, client, cap=100.0, out_dir=out_dir)

    assert code == 1
    status = json.loads(status_path.read_text(encoding="utf-8"))
    failed = [v for v in status.values() if v["state"] == "failed"]
    done = [v for v in status.values() if v["state"] == "done"]
    assert len(failed) == flow_gen.MAX_TOTAL_FAILURES
    assert len(done) == flow_gen.MAX_TOTAL_FAILURES - 1, (
        "successes interleave 1-for-1 between failures right up to the trip")


# -------------------------------------------------- fix round 5: key source

def test_load_key_prefers_the_project_file_over_the_environment(
        tmp_path, monkeypatch, capsys):
    """The exact regression: .veo_key present AND GOOGLE_API_KEY set to a
    different value (on the real machine: a stale, revoked key left in the
    shell from an unrelated project). The file must win -- three live runs
    authenticated with the dead environment credential while the correct
    key sat unused in .veo_key, because the original priority checked the
    environment first."""
    keyfile = tmp_path / ".veo_key"
    keyfile.write_text("AQ.the-real-project-key", encoding="utf-8")
    monkeypatch.setattr(flow_gen, "KEYFILE", keyfile)
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSySTALEfromANunrelatedPROJECTxx")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert load_key() == "AQ.the-real-project-key"
    assert "key source: .veo_key" in capsys.readouterr().out


def test_load_key_falls_back_to_gemini_api_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(flow_gen, "KEYFILE", tmp_path / "no-such-file")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.from-gemini-env")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert load_key() == "AQ.from-gemini-env"
    assert "key source: GEMINI_API_KEY" in capsys.readouterr().out


def test_load_key_falls_back_to_google_api_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(flow_gen, "KEYFILE", tmp_path / "no-such-file")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "AQ.from-google-env")

    assert load_key() == "AQ.from-google-env"
    assert "key source: GOOGLE_API_KEY" in capsys.readouterr().out


def test_load_key_raises_when_nothing_is_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(flow_gen, "KEYFILE", tmp_path / "no-such-file")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(SystemExit, match=r"\.veo_key"):
        load_key()


def test_load_key_warns_but_does_not_raise_on_an_unfamiliar_shape(
        tmp_path, monkeypatch, capsys):
    """A shape check that blocks would be worse than the problem it
    catches -- key formats change. This must warn, not raise."""
    keyfile = tmp_path / ".veo_key"
    keyfile.write_text("not-a-recognisable-key-shape", encoding="utf-8")
    monkeypatch.setattr(flow_gen, "KEYFILE", keyfile)

    key = load_key()          # must not raise

    assert key == "not-a-recognisable-key-shape"
    assert "WARNING" in capsys.readouterr().out
