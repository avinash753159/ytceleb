#!/usr/bin/env python3
"""Generate the picture layer with Veo, in the background, resumably.

Runs as a detached worker: it submits a shot, polls its long-running
operation, downloads the mp4, and records the result before moving on. Kill
it and restart it and it resumes -- status is written atomically after every
shot, so a killed run never loses more than the shot in flight.

The spend cap STOPS SUBMISSION rather than warning. Funding is a $21.08
prepay against a $32.90 full pass (118 gen shots, 658 billed seconds at
$0.05/s), so an unattended runaway would exhaust the balance before anyone
looked. The default cap of $20.00 is deliberately below the prepay.

THE LEDGER MUST COUNT WHAT GOOGLE CHARGES FOR, NOT WHAT THE LOCAL CLIENT
MANAGED TO PARSE. `client.models.generate_videos(...)` returns after Google
has accepted and queued the job -- generation runs and is billed server-side
regardless of what this process does with the returned operation. So
`spent` is charged the moment a submission is made (see `on_submit` in
`generate_one`), not after a clean download -- otherwise a single wrongly
named response attribute turns into a silent, cap-defeating runaway: every
submission "succeeds" at Google, every local parse of the result fails, the
ledger never moves, and the cap that tests `spent + cost > cap` never trips
because `spent` never left $0.00. A first version of this module worked
exactly that way; round 1 of review caught it before any money moved.

Submission and retrieval retry independently for the same reason. A
submission failure means resubmitting -- a new, separately billed job -- so
it is retried a bounded number of times (SUBMIT_RETRIES) with the ledger
charged on every attempt. A retrieval failure (the download/save step)
operates on an operation that has already been generated and billed once;
retrying it again calls no further billed API and is bounded separately
(DOWNLOAD_RETRIES).

CIRCUIT_BREAKER_STREAK exists because a bug in either phase is
structurally indistinguishable, in a single shot, from ordinary bad luck --
the only way to tell them apart is whether it keeps happening. Three
consecutive shot failures in a row halts the whole run rather than grinding
through the other ~115 shots. The worst case is arithmetic, not a guess:
CIRCUIT_BREAKER_STREAK (3) x (SUBMIT_RETRIES (2) + 1) = 9 submissions before
the breaker trips, and at this film's largest gen shot (6s, $0.30/attempt)
that is $2.70 -- three shots, not the balance.

That breaker only catches CONSECUTIVE failures. An alternating fail/succeed
pattern never reaches a streak of 3 and would otherwise be free to burn the
whole run one submission at a time, so MAX_TOTAL_FAILURES is a second,
unconditional bound: this many failures anywhere in the run, streak or no
streak, halts it. Neither breaker is the real backstop against a slow bleed
of intermittent failures across all 118 shots, though -- `--cap` is. The
breakers exist to catch a fast, obvious systemic bug in a handful of dollars;
the cap is what still holds if the bug is subtle enough to hide inside an
occasional failure per shot for the whole run.

A shot that a cap-stop interrupts mid-attempt (already billed once, but
the retry that would have finished it was refused by the cap) is recorded
with state="interrupted", not "done" (nothing was delivered) and not
"failed" (that implies nothing was owed) -- carrying the amount already
charged and the submission count, so the ledger shows money spent on a
shot with no output, and `pending()` still retries it once funding allows.

Every prompt in manifest/flow_shots.json already ends with "no text, no
logos", but generated video invents signage anyway -- a known Veo failure
mode that has already cost whole batches of earlier footage withdrawn over
legible brand marks. NEGATIVE_PROMPT is passed on every call as a second
line of defense the model prompt can't be relied on alone to provide.

generate_audio is forced off: the film's audio track is locked and already
approved, so any audio Veo generates is pure waste and a leakage risk if a
frame of it ever survives into the final mux.

Each shot gets a seed derived deterministically from its shot_id (see
seed_for) and the seed is written into the status ledger alongside the
output path. That makes a rerun reproduce the same picture by default, and
turns a deliberate reroll (asking for a different result) into an explicit,
visible act rather than something that happens by accident on retry.

person_generation is set to "allow_adult" -- the installed SDK
(google-genai 2.14.0)'s own field description names exactly two accepted
values, "dont_allow" and "allow_adult", and this is a live-action human
documentary. fps is left unset: the model's fidelity to a requested fps has
not been verified, and Task 7 checks 24fps empirically against the actual
output rather than trusting a request parameter.

The API key goes in `api_key=` (an SDK-level API key), never as an OAuth
bearer token. Passing this AQ.-format key as a bearer returns
API_KEY_SERVICE_BLOCKED, which reads exactly like a revoked key and cost an
hour of debugging on this project already.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/flow_shots.json"
STATUS = ROOT / "manifest/flow_gen_status.json"
OUTDIR = ROOT / "library/veo"
KEYFILE = ROOT / ".veo_key"

MODEL = "veo-3.1-lite-generate-preview"
RESOLUTION = "720p"
ASPECT = "16:9"
RATE_PER_SECOND = 0.05        # Veo 3.1 Lite, 720p
DEFAULT_CAP = 20.00           # dollars; below the $21.08 prepay on purpose
POLL_SECONDS = 10
MAX_POLL = 360                # an hour before a shot is called stuck

# Submission and retrieval retry independently -- see module docstring.
# Resubmitting is a new billed job; re-downloading is not.
SUBMIT_RETRIES = 2
DOWNLOAD_RETRIES = 2

# Halt the whole run after this many consecutive SHOT failures (not
# submission attempts). Exists so a wrong response-shape assumption --
# e.g. a renamed SDK attribute -- burns at most a few shots' worth of the
# balance instead of grinding through all 118. Do not raise this without
# also re-verifying the SDK response shape against a live call.
# Worst case: CIRCUIT_BREAKER_STREAK x (SUBMIT_RETRIES + 1) = 9 submissions
# before this trips, $2.70 at the film's 6s max shot cost -- see docstring.
CIRCUIT_BREAKER_STREAK = 3

# A second, unconditional bound: this many shot failures ANYWHERE in the
# run -- streak or no streak -- halts it. Exists because the streak breaker
# above can be starved by an alternating fail/succeed pattern, which would
# otherwise be free to burn the whole run one submission at a time. Neither
# breaker is the true backstop against a slow bleed of intermittent
# failures across the whole 118-shot run -- `--cap` is; see docstring.
MAX_TOTAL_FAILURES = 8

# Status-file rename retry: on Windows, antivirus or a backup indexer can
# transiently hold the destination open, turning a routine `Path.replace`
# into a PermissionError (WinError 32). A paid, successful generation whose
# ledger write is lost this way gets resubmitted -- and re-billed -- next
# run, so this is retried a few times before giving up loudly.
RECORD_RETRIES = 3
RECORD_RETRY_SLEEP = 0.2      # seconds

# Every prompt already says "no text, no logos", but Veo invents signage
# anyway; this is the belt to that belt-and-suspenders. See module docstring.
NEGATIVE_PROMPT = (
    "text, letters, words, subtitles, captions, watermark, logo, brand "
    "name, signage, on-screen graphics, timestamp, numbers"
)

# The installed SDK's GenerateVideosConfig.person_generation field
# description lists exactly two supported values: "dont_allow" and
# "allow_adult". This is a live-action adult documentary, so "allow_adult".
PERSON_GENERATION = "allow_adult"


class CapReached(Exception):
    """Raised by an `on_submit` callback to stop before a submission that
    would exceed the cap. Never retried -- it must propagate straight out
    of generate_one, not be mistaken for a transient submission failure."""


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key and KEYFILE.exists():
        key = KEYFILE.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit(
            "No API key. Put it in .veo_key or set GEMINI_API_KEY.")
    return key


def estimate_cost(shots: list[dict]) -> float:
    return sum(s["gen_dur"] for s in shots
               if s.get("kind") == "gen") * RATE_PER_SECOND


def pending(shots: list[dict], status: dict) -> list[dict]:
    return [s for s in shots
            if s.get("kind") == "gen"
            and status.get(s["shot_id"], {}).get("state") != "done"]


def record(status_path: Path, shot_id: str, **fields) -> None:
    """Atomic status write -- a killed run must not corrupt the ledger.

    The rename is retried a few times (RECORD_RETRIES) before giving up: see
    module docstring for why a swallowed PermissionError here is worse than
    a loud crash. If every attempt fails, this raises rather than returning,
    naming the shot and the fields that were about to be recorded.
    """
    cur = {}
    if status_path.exists():
        cur = json.loads(status_path.read_text(encoding="utf-8"))
    cur[shot_id] = fields
    tmp = status_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=1), encoding="utf-8")

    last_exc: Exception | None = None
    for attempt in range(RECORD_RETRIES):
        try:
            tmp.replace(status_path)
            return
        except (PermissionError, OSError) as exc:
            last_exc = exc
            if attempt < RECORD_RETRIES - 1:
                time.sleep(RECORD_RETRY_SLEEP)
    raise RuntimeError(
        f"could not record status for {shot_id!r} (fields={fields}) "
        f"after {RECORD_RETRIES} attempts -- a paid result may be "
        f"unrecorded and will be resubmitted next run: {last_exc}"
    ) from last_exc


def seed_for(shot_id: str) -> int:
    """Deterministic per-shot seed, derived from the shot id.

    A stable hash rather than random.seed()/hash() -- the latter is salted
    per-process in CPython (PYTHONHASHSEED), so it would produce a different
    "deterministic" seed on every run, defeating the point. sha256 is stable
    across processes, machines and Python versions. Truncated to 32 bits: a
    plain, small, well within any int64 seed field's range.
    """
    digest = hashlib.sha256(shot_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def build_config(shot: dict):
    """Build the GenerateVideosConfig for one shot.

    Split out from generate_one so the config shape -- audio off, negative
    prompt, per-shot seed, locked format -- can be tested without touching
    the network.
    """
    from google.genai import types

    return types.GenerateVideosConfig(
        aspect_ratio=ASPECT,
        resolution=RESOLUTION,
        duration_seconds=shot["gen_dur"],
        number_of_videos=1,
        generate_audio=False,
        negative_prompt=NEGATIVE_PROMPT,
        seed=seed_for(shot["shot_id"]),
        person_generation=PERSON_GENERATION,
    )


def submit_and_wait(client, shot: dict):
    """Submit one shot and poll until the operation is done.

    Every call to this function is a new, separately billed generation job:
    Google bills on acceptance, before this function's poll loop even starts.
    A caller that retries a failure here must know it is paying again.
    """
    op = client.models.generate_videos(
        model=MODEL,
        prompt=shot["prompt"],
        config=build_config(shot),
    )
    for _ in range(MAX_POLL):
        if op.done:
            break
        time.sleep(POLL_SECONDS)
        op = client.operations.get(op)
    else:
        raise TimeoutError(f"{shot['shot_id']} still running after "
                           f"{MAX_POLL * POLL_SECONDS}s")

    if getattr(op, "error", None):
        raise RuntimeError(f"{shot['shot_id']}: {op.error}")
    return op


def download_result(client, op, shot: dict, out_dir: Path) -> Path:
    """Download and save an already-completed operation.

    Operates only on `op`, never resubmits. Safe to retry on its own: a
    retry here calls no additional billed API.
    """
    vids = op.response.generated_videos
    if not vids:
        raise RuntimeError(f"{shot['shot_id']}: no video returned")

    dest = out_dir / f"{shot['shot_id']}.mp4"
    client.files.download(file=vids[0].video)
    vids[0].video.save(str(dest))
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"{shot['shot_id']}: empty download")
    return dest


def generate_one(client, shot: dict, out_dir: Path, on_submit=None) -> Path:
    """Submit one shot, poll to completion, download. Raises on failure.

    Submission and retrieval retry independently -- see module docstring.
    `on_submit`, if given, is called immediately before every submission
    attempt (including retries), so a caller tracking spend can charge the
    ledger at the moment of commitment rather than the moment of success. A
    shot that needed two submissions before one succeeded must be charged
    twice. If `on_submit` raises (e.g. CapReached), that propagates straight
    out -- it is not a submission failure to be retried.
    """
    op = None
    last_exc: Exception | None = None
    for attempt in range(SUBMIT_RETRIES + 1):
        if on_submit is not None:
            on_submit()
        try:
            op = submit_and_wait(client, shot)
            break
        except Exception as exc:                # noqa: BLE001
            last_exc = exc
            op = None
            if attempt < SUBMIT_RETRIES:
                time.sleep(5 * (attempt + 1))
    if op is None:
        raise last_exc

    last_exc = None
    for attempt in range(DOWNLOAD_RETRIES + 1):
        try:
            return download_result(client, op, shot, out_dir)
        except Exception as exc:                # noqa: BLE001
            last_exc = exc
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(5 * (attempt + 1))
    raise last_exc


def run(todo: list[dict], status_path: Path, client, cap: float,
        out_dir: Path) -> int:
    """Drive the shot loop: charge at submission, retry download without
    resubmitting, halt after CIRCUIT_BREAKER_STREAK consecutive shot
    failures or MAX_TOTAL_FAILURES failures overall. Returns a process exit
    code (0 clean/cap-stopped, 1 a breaker tripped).
    """
    total = len(todo)
    spent = 0.0
    consecutive_failures = 0
    total_failures = 0

    for i, shot in enumerate(todo, 1):
        cost = shot["gen_dur"] * RATE_PER_SECOND
        charged = 0.0
        submissions = 0

        def on_submit(cost=cost):
            nonlocal spent, charged, submissions
            if spent + cost > cap:
                raise CapReached(
                    f"cap ${cap:.2f} reached (spent ${spent:.2f})")
            spent += cost
            charged += cost
            submissions += 1

        try:
            dest = generate_one(client, shot, out_dir, on_submit=on_submit)
        except CapReached as exc:
            # The cap can interrupt a shot mid-attempt: an earlier retry
            # within this same shot may already have been billed (charged
            # > 0) before this attempt was refused. That money is real and
            # must be visible -- not "done" (nothing delivered), not
            # "failed" (that implies nothing was owed).
            record(status_path, shot["shot_id"], state="interrupted",
                   charged=charged, submissions=submissions,
                   seed=seed_for(shot["shot_id"]))
            print(f"STOP: {exc} at {shot['shot_id']} "
                  f"(charged ${charged:.2f} for it); "
                  f"{total - i + 1} shots left")
            print(f"spent ${spent:.2f}")
            return 0
        except Exception as exc:                # noqa: BLE001
            consecutive_failures += 1
            total_failures += 1
            record(status_path, shot["shot_id"], state="failed",
                   error=str(exc)[:300], seed=seed_for(shot["shot_id"]),
                   charged=charged, submissions=submissions)
            print(f"[{i}/{total}] {shot['shot_id']} FAILED: "
                  f"{str(exc)[:120]}  (charged ${charged:.2f})")
            if consecutive_failures >= CIRCUIT_BREAKER_STREAK:
                print(f"STOP: {CIRCUIT_BREAKER_STREAK} consecutive shot "
                      f"failures -- halting before the rest of the backlog "
                      f"burns on what looks like a systemic bug, not bad "
                      f"luck.")
                print(f"spent ${spent:.2f}")
                return 1
            if total_failures >= MAX_TOTAL_FAILURES:
                print(f"STOP: {MAX_TOTAL_FAILURES} total shot failures -- "
                      f"an alternating fail/succeed pattern can starve the "
                      f"consecutive-failure breaker, so this bound is "
                      f"unconditional.")
                print(f"spent ${spent:.2f}")
                return 1
            continue
        else:
            consecutive_failures = 0
            record(status_path, shot["shot_id"], state="done",
                   path=str(dest.relative_to(ROOT)), cost=charged,
                   seed=seed_for(shot["shot_id"]))
            print(f"[{i}/{total}] {shot['shot_id']} "
                  f"{shot['gen_dur']}s  ${spent:.2f}")

    print(f"spent ${spent:.2f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cap", type=float, default=DEFAULT_CAP,
                    help="hard dollar ceiling; submission stops at it")
    ap.add_argument("--only", nargs="*", default=None,
                    help="generate only these shot_ids")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    status = (json.loads(STATUS.read_text(encoding="utf-8"))
              if STATUS.exists() else {})
    todo = pending(shots, status)
    if args.only:
        todo = [s for s in todo if s["shot_id"] in set(args.only)]

    print(f"{len(todo)} shots pending  "
          f"est ${estimate_cost(todo):.2f}  cap ${args.cap:.2f}")
    if args.dry_run:
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    from google import genai
    client = genai.Client(api_key=load_key())

    return run(todo, STATUS, client, args.cap, OUTDIR)


if __name__ == "__main__":
    raise SystemExit(main())
