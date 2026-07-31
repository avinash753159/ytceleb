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

`build_config` sends ONLY fields the Developer API tier this project's key
actually runs under will accept. This was extracted from the SDK source
after two live runs each independently discovered one more rejected field
the hard way (round 3: `seed`; round 4: `generate_audio`) -- both were
rejected client-side, before any request left the machine, so both cost
$0.00, but two paid-run-shaped diagnostics for what turned out to be the
same root cause (reading `GenerateVideosConfig`'s full field list without
checking which fields this API *tier* accepts) was one too many.

  REJECTED (raises ValueError client-side, Enterprise/Vertex-only): seed,
  generate_audio, negative_prompt, person_generation, fps, enhance_prompt,
  compression_quality, resize_mode, labels, mask, output_gcs_uri,
  pubsub_topic.

  ACCEPTED: aspect_ratio, duration_seconds, resolution, number_of_videos,
  last_frame, reference_images, http_options, webhook_config.

`reference_images` is accepted -- a look-book for visual consistency is
still possible in a later task; it is not blocked by any of this.

THE LEDGER MUST COUNT WHAT GOOGLE CHARGES FOR, NOT WHAT THE LOCAL CLIENT
MANAGED TO PARSE. `client.models.generate_videos(...)` returns after Google
has accepted and queued the job -- generation runs and is billed server-side
regardless of what this process does with the returned operation. So
`spent` is charged the moment `generate_videos()` returns successfully (see
`charge` in `submit_and_wait`) -- not before the call, and not after a
clean download.

Not before the call: an early version of this module charged before
`generate_videos()` was even invoked, so a purely client-side error --
raised by the SDK itself before any request left the machine -- was billed
for a request Google never saw. That is exactly what happened on this
project's first live run (see below): a client-side `ValueError` was
charged $0.40 for two submissions that cost nothing. Round 3 moved the
charge to immediately after `generate_videos()` returns, while keeping the
cap CHECK itself before the call (a would-exceed-cap check must still gate
whether the call happens at all -- only the increment moved).

Not after a clean download: a still earlier version charged only after
`generate_one` returned successfully end to end, so a single wrongly named
response attribute turned into a silent, cap-defeating runaway: every
submission "succeeds" at Google, every local parse of the result fails, the
ledger never moves, and the cap that tests `spent + cost > cap` never trips
because `spent` never left $0.00. Round 1 of review caught that before any
money moved.

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
Every non-"done" record -- "failed" and "interrupted" alike -- also carries
an `error` field with the underlying exception's type and message. The
first live run's cap-stop otherwise looked like a clean, boring stop; the
actual reason (see below) was only visible after a second, separate
diagnostic run. The ledger is supposed to make that unnecessary.

Every prompt in manifest/flow_shots.json already ends with "no text, no
logos, no recognisable faces", but generated video invents signage anyway --
a known Veo failure mode that has already cost whole batches of earlier
footage withdrawn over legible brand marks. `negative_prompt` was meant to
be a second, API-level line of defense, but it is Enterprise/Vertex-only
and the Developer API rejects it client-side. THAT ENFORCEMENT NOW LIVES
ENTIRELY IN THE PROMPT TEXT, backed up by post-hoc QC in a later task --
this is a real, live gap, not a cosmetic one: NEGATIVE_PROMPT is kept below
as a documented constant (the canonical "what we're excluding" text for
that QC step) precisely so nobody re-adds it to the API call thinking it
will help. It won't -- it will raise.

Two real, non-cosmetic losses fall out of the round-4 field cut, beyond the
negative-prompt one above:

  1. NO REPRODUCIBILITY. `seed` is rejected, so there is no way to pin a
     shot's output and no way to "nudge" a rejected result -- regenerating
     a shot produces a genuinely different picture every time. A shot that
     needs a redo can only be re-rolled, not reproduced or steered.
  2. NO FORCED-OFF AUDIO. `generate_audio` is also rejected, so this
     process cannot tell Veo to skip audio generation. The film's own
     audio track is locked and approved; whatever Veo's Developer-API
     default behaviour turns out to be for audio, it must be verified
     (and stripped at the mux if present) by whichever later task first
     handles the raw clips -- this module can no longer guarantee it away.

fps is left unset regardless -- it is also Enterprise-only, so this was
never a choice to make: the model's fidelity to a requested fps was never
going to be independently verified here anyway, and Task 7 checks 24fps
empirically against the actual output rather than trusting a request
parameter that the API would have rejected.

The API key goes in `api_key=` (an SDK-level API key), never as an OAuth
bearer token. Passing this AQ.-format key as a bearer returns
API_KEY_SERVICE_BLOCKED, which reads exactly like a revoked key and cost an
hour of debugging on this project already.

`load_key()` prefers `.veo_key` (a project-local, gitignored file) over
the ambient `GEMINI_API_KEY`/`GOOGLE_API_KEY` environment variables, and
this is deliberate, not incidental: a file checked into this project's
directory is an explicit statement of intent, while an environment
variable is ambient and may belong to something else entirely. It did,
here -- three live runs (round 5) all authenticated with a stale, revoked
`GOOGLE_API_KEY` left over in the operator's shell from an unrelated
project, silently shadowing the correct, working key that sat unused in
`.veo_key` the whole time, because the original priority order checked the
environment first. `load_key()` now prints which source it used (key
masked) every time it runs, specifically so this class of failure is never
silent again.
"""

from __future__ import annotations

import argparse
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

# NOT passed to GenerateVideosConfig -- `negative_prompt` is Enterprise/
# Vertex-only and the Developer API rejects it client-side (round 4; see
# module docstring). Kept as a documented constant only: it is the
# canonical "what we're excluding" text, for a later QC task to check
# generated footage against, since the API-level enforcement it was meant
# to provide isn't available and the only defense left is the prompt's own
# trailing "no text, no logos, no recognisable faces" plus that QC step.
# Do not pass this to GenerateVideosConfig -- it will raise ValueError.
NEGATIVE_PROMPT = (
    "text, letters, words, subtitles, captions, watermark, logo, brand "
    "name, signage, on-screen graphics, timestamp, numbers"
)


class CapReached(Exception):
    """Raised by a `check_cap` callback to stop before a submission that
    would exceed the cap. Never retried -- it must propagate straight out
    of generate_one, not be mistaken for a transient submission failure."""


def _mask_key(key: str) -> str:
    """First 8 / last 4 characters, for logging a key without leaking it."""
    if len(key) <= 12:
        return key[:2] + "..."
    return f"{key[:8]}...{key[-4:]}"


def load_key() -> str:
    """Resolve the API key -- .veo_key first, then the environment.

    See module docstring for why the file wins: it is an explicit,
    project-local statement of intent, while GEMINI_API_KEY/GOOGLE_API_KEY
    are ambient and may (and here, did) belong to an unrelated project
    still set in the operator's shell. Prints which source was used, key
    masked, every call -- this class of failure was invisible for three
    live runs precisely because nothing said where the credential came
    from.
    """
    if KEYFILE.exists():
        key = KEYFILE.read_text(encoding="utf-8").strip()
        source = ".veo_key"
    else:
        key = os.environ.get("GEMINI_API_KEY")
        source = "GEMINI_API_KEY"
        if not key:
            key = os.environ.get("GOOGLE_API_KEY")
            source = "GOOGLE_API_KEY"

    if not key:
        raise SystemExit(
            "No API key. Put it in .veo_key or set GEMINI_API_KEY.")

    print(f"key source: {source} ({_mask_key(key)})")

    # Shape sanity check only -- warn, never block. Key formats change
    # (the classic "AIzaSy..." 39-char key vs. the newer "AQ...." format);
    # a hard check here would be worse than the problem it catches.
    looks_like_a_key = (
        (key.startswith("AIzaSy") and len(key) == 39) or key.startswith("AQ.")
    )
    if not looks_like_a_key:
        print(f"WARNING: key from {source} doesn't look like a Gemini API "
              f"key (expected 'AIzaSy...' at 39 chars, or the newer "
              f"'AQ....' format) -- proceeding anyway.")

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


def build_config(shot: dict):
    """Build the GenerateVideosConfig for one shot.

    Sends ONLY fields the Developer API tier this project's key runs under
    accepts: aspect_ratio, resolution, duration_seconds, number_of_videos.
    Everything this pipeline once also set here -- seed, generate_audio,
    negative_prompt, person_generation -- is Enterprise/Vertex-only and
    raises a client-side ValueError on this tier. See module docstring for
    the full accepted/rejected lists and what losing each of these costs.
    Split out from generate_one so this shape can be tested (see
    test_build_config_sends_only_developer_api_fields) without touching
    the network.
    """
    from google.genai import types

    return types.GenerateVideosConfig(
        aspect_ratio=ASPECT,
        resolution=RESOLUTION,
        duration_seconds=shot["gen_dur"],
        number_of_videos=1,
    )


def submit_and_wait(client, shot: dict, charge=None):
    """Submit one shot and poll until the operation is done.

    Every call to this function is a new, separately billed generation job
    -- but only once `generate_videos()` actually returns. If it raises
    (bad config, a client-side validation error, a network error before
    anything was sent), Google never saw the request and `charge` is never
    called. The moment it returns without raising, the job is queued and
    billed server-side regardless of what happens next, so `charge` (if
    given) fires right here, before polling even starts -- a poll or
    download failure after this point is still billed, correctly.
    """
    op = client.models.generate_videos(
        model=MODEL,
        prompt=shot["prompt"],
        config=build_config(shot),
    )
    if charge is not None:
        charge()
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


def generate_one(client, shot: dict, out_dir: Path,
                  check_cap=None, charge=None) -> Path:
    """Submit one shot, poll to completion, download. Raises on failure.

    Submission and retrieval retry independently -- see module docstring.
    `check_cap`, if given, is called immediately before every submission
    attempt (including retries) and must raise (e.g. CapReached) to refuse
    the attempt -- it gates whether `generate_videos()` is even called.
    `charge`, if given, is passed through to `submit_and_wait` and fires
    only once `generate_videos()` has actually returned, i.e. only for
    attempts Google accepted and billed -- never for a client-side raise
    that kept the request from ever being sent.

    If `check_cap` raises CapReached while an earlier attempt in this same
    shot already failed, that failure is folded into the CapReached message
    (and chained as its `__cause__`) so a cap-stop mid-shot doesn't discard
    the reason the shot needed retrying in the first place.
    """
    op = None
    last_exc: Exception | None = None
    for attempt in range(SUBMIT_RETRIES + 1):
        if check_cap is not None:
            try:
                check_cap()
            except CapReached as cap_exc:
                if last_exc is not None:
                    raise CapReached(
                        f"{cap_exc} -- {shot['shot_id']}'s last submission "
                        f"attempt had failed with: {last_exc}"
                    ) from last_exc
                raise
        try:
            op = submit_and_wait(client, shot, charge=charge)
            break
        except Exception as exc:                # noqa: BLE001
            last_exc = exc
            op = None
            if attempt < SUBMIT_RETRIES:
                time.sleep(5 * (attempt + 1))
    if op is None:
        raise last_exc

    dl_last_exc: Exception | None = None
    for attempt in range(DOWNLOAD_RETRIES + 1):
        try:
            return download_result(client, op, shot, out_dir)
        except Exception as exc:                # noqa: BLE001
            dl_last_exc = exc
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(5 * (attempt + 1))
    raise dl_last_exc


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

        def check_cap(cost=cost):
            if spent + cost > cap:
                raise CapReached(
                    f"cap ${cap:.2f} reached (spent ${spent:.2f})")

        def charge(cost=cost):
            nonlocal spent, charged, submissions
            spent += cost
            charged += cost
            submissions += 1

        try:
            dest = generate_one(client, shot, out_dir,
                                 check_cap=check_cap, charge=charge)
        except CapReached as exc:
            # The cap can interrupt a shot mid-attempt: an earlier retry
            # within this same shot may already have been billed (charged
            # > 0) before this attempt was refused. That money is real and
            # must be visible -- not "done" (nothing delivered), not
            # "failed" (that implies nothing was owed). `exc`'s own message
            # already folds in the shot's last submission error, if any --
            # see generate_one -- so it's recorded here too, not just
            # printed and lost.
            record(status_path, shot["shot_id"], state="interrupted",
                   charged=charged, submissions=submissions,
                   error=str(exc)[:300])
            print(f"STOP: {exc} at {shot['shot_id']} "
                  f"(charged ${charged:.2f} for it); "
                  f"{total - i + 1} shots left")
            print(f"spent ${spent:.2f}")
            return 0
        except Exception as exc:                # noqa: BLE001
            consecutive_failures += 1
            total_failures += 1
            record(status_path, shot["shot_id"], state="failed",
                   error=str(exc)[:300],
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
                   path=str(dest.relative_to(ROOT)), cost=charged)
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
