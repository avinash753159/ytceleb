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
RETRIES = 2

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
    """Atomic status write -- a killed run must not corrupt the ledger."""
    cur = {}
    if status_path.exists():
        cur = json.loads(status_path.read_text(encoding="utf-8"))
    cur[shot_id] = fields
    tmp = status_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    tmp.replace(status_path)


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


def generate_one(client, shot: dict, out_dir: Path) -> Path:
    """Submit one shot, poll to completion, download. Raises on failure."""
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

    vids = op.response.generated_videos
    if not vids:
        raise RuntimeError(f"{shot['shot_id']}: no video returned")

    dest = out_dir / f"{shot['shot_id']}.mp4"
    client.files.download(file=vids[0].video)
    vids[0].video.save(str(dest))
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"{shot['shot_id']}: empty download")
    return dest


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

    spent = 0.0
    for i, shot in enumerate(todo, 1):
        cost = shot["gen_dur"] * RATE_PER_SECOND
        if spent + cost > args.cap:
            print(f"STOP: cap ${args.cap:.2f} reached "
                  f"(spent ${spent:.2f}); {len(todo) - i + 1} shots left")
            break
        seed = seed_for(shot["shot_id"])
        for attempt in range(RETRIES + 1):
            try:
                dest = generate_one(client, shot, OUTDIR)
                spent += cost
                record(STATUS, shot["shot_id"], state="done",
                       path=str(dest.relative_to(ROOT)), cost=cost,
                       seed=seed)
                print(f"[{i}/{len(todo)}] {shot['shot_id']} "
                      f"{shot['gen_dur']}s  ${spent:.2f}")
                break
            except Exception as exc:            # noqa: BLE001
                if attempt == RETRIES:
                    record(STATUS, shot["shot_id"], state="failed",
                           error=str(exc)[:300], seed=seed)
                    print(f"[{i}/{len(todo)}] {shot['shot_id']} FAILED: "
                          f"{str(exc)[:120]}")
                else:
                    time.sleep(5 * (attempt + 1))
    print(f"spent ${spent:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
