#!/usr/bin/env python3
"""Generate a shot as a still image, then animate it with a depth push-in.

This is the film's default medium and the reason a 12-minute picture layer
fits the budget at all: a generated still costs about $0.04 against roughly
$0.30 for the same beat as generated video, so the cheap path is ~7.5x less
per shot. Video is reserved for the shots in manifest/video_shots.json, where
motion carries meaning a single frame cannot.

Two stages, cached separately, because they fail for different reasons and
cost different amounts:

  1. library/stills/<shot_id>.png   - the generated image. Costs money.
  2. library/stillvid/<shot_id>.mp4 - the depth push-in. Costs only CPU.

Stage 2 can be re-run freely to retune the move without paying for the image
again, which matters because the push-in has no seed and a regenerated image
is a different picture, never a refined one.

The depth push-in produces real parallax only where the depth map has
structure. On a flat or macro composition it degrades to a plain eased zoom -
that is handled by flow_dibr, not here, and it is a limitation of the source
image rather than a fault to fix.

Like flow_gen, this records every outcome. A shot that fails is marked, never
silently skipped: an earlier module in this repo did `if not p.exists():
continue` and dropped 14 entries while reporting success.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

SHOTS = ROOT / "manifest/flow_shots.json"
VIDEO_SHOTS = ROOT / "manifest/video_shots.json"
STILLS = ROOT / "library/stills"
STILLVID = ROOT / "library/stillvid"
STATUS = ROOT / "manifest/flow_still_status.json"
KEYFILE = ROOT / ".veo_key"

# gemini-3.1-flash-lite-image is the cheapest model on this key that returns a
# usable 16:9 frame. Imagen 4 is closed to new users (404) and the SDK's
# generate_images path is deprecated, so this goes through generate_content.
MODEL = "gemini-3.1-flash-lite-image"
COST_PER_IMAGE = 0.04

# Push-in geometry. zoom must leave enough headroom for the depth warp or
# flow_dibr refuses the render rather than expose a frame edge - lateral drift
# was dropped for exactly that reason at strength 0.06.
STRENGTH = 0.06
ZOOM = 1.12
DRIFT = (0.0, 0.0)

DEFAULT_CAP = 5.00
RETRIES = 2


def load_key() -> str:
    """The project key file beats an ambient environment variable.

    An operator's shell can carry a stale key from an unrelated project, and
    on this machine it did - a revoked GOOGLE_API_KEY shadowed the working
    key for three runs.
    """
    if KEYFILE.exists():
        k = KEYFILE.read_text(encoding="utf-8").strip()
        if k:
            return k
    import os
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            return os.environ[var]
    raise SystemExit("No API key. Put it in .veo_key or set GEMINI_API_KEY.")


def record(shot_id: str, **fields) -> None:
    """Atomic status write; a killed run must not corrupt the ledger."""
    cur = {}
    if STATUS.exists():
        cur = json.loads(STATUS.read_text(encoding="utf-8"))
    cur[shot_id] = fields
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    for attempt in range(3):
        try:
            tmp.replace(STATUS)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.2)


GEN_STATUS = ROOT / "manifest/flow_gen_status.json"


def still_shots(include_video_without_clip: bool = False) -> list[dict]:
    """Every generated shot not assigned to video and not already made.

    Three exclusions, and the third one is load-bearing. A shot already
    generated as VIDEO must not be regenerated as a still: it would spend
    money to replace footage that already exists, and it would silently
    overwrite shots the owner has approved by eye. s002b - the gut turned
    raw, at 0:21 - is exactly such a shot.
    """
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    video = set()
    if VIDEO_SHOTS.exists():
        video = set(json.loads(VIDEO_SHOTS.read_text(encoding="utf-8"))["video"])
    done_as_video = set()
    if GEN_STATUS.exists():
        done_as_video = {k for k, v in
                         json.loads(GEN_STATUS.read_text(encoding="utf-8")).items()
                         if v.get("state") == "done"}
    veo_dir = ROOT / "library/veo"
    out = []
    for s in shots:
        sid = s["shot_id"]
        if s["kind"] != "gen":
            continue
        if sid in video:
            # A video shot is skipped unless we are filling the gap left by
            # Veo's periodic quota, and then only if it has no clip yet.
            if not include_video_without_clip:
                continue
            if (veo_dir / f"{sid}.mp4").exists():
                continue
        if (STILLVID / f"{sid}.mp4").exists():
            continue
        if sid in done_as_video and sid not in video:
            continue
        out.append(s)
    return out


def make_image(client, shot: dict) -> Path:
    """Generate the still. Raises if the model returns no image part."""
    dest = STILLS / f"{shot['shot_id']}.png"
    if dest.exists():
        return dest
    STILLS.mkdir(parents=True, exist_ok=True)
    r = client.models.generate_content(model=MODEL, contents=shot["prompt"])
    for cand in (r.candidates or []):
        for part in (cand.content.parts or []):
            blob = getattr(part, "inline_data", None)
            if blob and blob.data:
                dest.write_bytes(blob.data)
                return dest
    raise RuntimeError(f"{shot['shot_id']}: model returned no image")


def render_move(shot: dict) -> Path:
    """Animate the still. CPU only - no charge, safe to re-run."""
    import flow_dibr

    STILLVID.mkdir(parents=True, exist_ok=True)
    dest = STILLVID / f"{shot['shot_id']}.mp4"
    seconds = shot["end"] - shot["start"]
    flow_dibr.dolly_in(STILLS / f"{shot['shot_id']}.png", dest, seconds,
                       strength=STRENGTH, zoom=ZOOM, drift=DRIFT)
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cap", type=float, default=DEFAULT_CAP,
                    help="hard dollar ceiling; generation stops at it")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None,
                    help="process at most N shots this run (for batching)")
    ap.add_argument("--fallback", action="store_true",
                    help="also make stills for video shots that have no clip "
                         "yet, so the film is complete while Veo quota is out")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    todo = still_shots(include_video_without_clip=args.fallback)
    if args.only:
        todo = [s for s in todo if s["shot_id"] in set(args.only)]
    if args.limit:
        todo = todo[:args.limit]

    print(f"{len(todo)} stills pending  est ${len(todo) * COST_PER_IMAGE:.2f}  "
          f"cap ${args.cap:.2f}")
    if args.dry_run:
        return 0

    from google import genai
    client = genai.Client(api_key=load_key())
    spent = 0.0
    for i, shot in enumerate(todo, 1):
        sid = shot["shot_id"]
        already = (STILLS / f"{sid}.png").exists()
        if not already and spent + COST_PER_IMAGE > args.cap:
            print(f"STOP: cap ${args.cap:.2f} reached (spent ${spent:.2f}) "
                  f"at {sid}; {len(todo) - i + 1} left")
            break
        for attempt in range(RETRIES + 1):
            try:
                make_image(client, shot)
                if not already:
                    spent += COST_PER_IMAGE
                render_move(shot)
                record(sid, state="done", cost=0.0 if already else COST_PER_IMAGE)
                print(f"[{i}/{len(todo)}] {sid} "
                      f"{shot['end'] - shot['start']:.2f}s  ${spent:.2f}")
                break
            except Exception as exc:            # noqa: BLE001
                if attempt == RETRIES:
                    record(sid, state="failed", error=str(exc)[:300])
                    print(f"[{i}/{len(todo)}] {sid} FAILED: {str(exc)[:110]}")
                else:
                    time.sleep(3 * (attempt + 1))
    print(f"spent ${spent:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
