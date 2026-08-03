#!/usr/bin/env python3
"""Stock footage for the rewritten shot list, one group per EDL segment.

WHY THIS IS KEYED BY SEGMENT AND NOT BY THEME
---------------------------------------------
broll3-6 are grouped by subject ("eq_barbell", "iv", "walk2") and the plan
then picks a group per shot. That is how a clip about nothing in particular
ends up under a specific sentence: the group is only as specific as its name.

Here the group IS the segment, so every clip was searched for against the
words actually being spoken at that moment. Segment 0 does not draw from a
"scale" bucket; it draws from clips found by searching for a film set at
night, because that is what the line says.

MEDICAL SEGMENTS ARE NOT HERE. 2, 7, 14, 15 and 16 are carried by the
licensed stills already in dossier/mrbeast/medical/ and wired into
picture_plan_v8.STILLS. Stock video of "inflamed intestine" is either a
cartoon or somebody's animation of a different disease.

RULE 9 IS RELAXED, NOT GONE. fetch_broll6 recorded the owner's decision that
anonymous people may perform the activity. Still barred: any identifiable
creator, any child cast as young Jimmy, and any burned-in logo or overlay
text. The eyes-on pass after this is what enforces it - this script only
gathers candidates.

Nothing here is cleared for use. Run pipeline/screen_broll7.py next.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
DEST = ROOT / "library/broll7"
KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

MIN_DUR, MAX_DUR = 5, 45
PER_SEG = 5          # candidates to keep per segment before screening
WORKERS = 8

# segment -> search phrases, in preference order. Derived from the prompt for
# that segment, phrased the way stock video is actually tagged.
WANT: dict = {
 -1: ["single light bulb swinging dark room", "work light dark warehouse",
      "dust particles in light beam dark"],
 0:  ["film set night lighting crew", "movie production set lights",
      "film crew camera crane night", "large studio production lights"],
 # "objects on a table in a dark room" returned decorative art still-lifes
 # - a white rose on a plinth, pumpkins on boxes - which played under "a body
 # that kept taking things away from a kid" as a homeware advert. Name the
 # objects instead of the arrangement.
 3:  ["baseball glove on wooden table", "old baseball equipment still",
      "worn leather baseball mitt close up", "baseball and bat on table"],
 # Every "empty running track" result had runners on it, and two were aerials
 # of an American football field - which cut directly against the baseball
 # stadium in the next shot. Ask for the surface, not the venue.
 4:  ["running track lane markings close up", "athletics track surface empty",
      "red running track texture", "stadium track lanes no people"],
 5:  ["baseball field empty diamond", "baseball glove dirt ground",
      "baseball bat home plate", "little league field evening"],
 6.5: ["empty baseball diamond dusk", "baseball field sunset empty",
       "abandoned sports field evening"],
 9:  ["stadium floodlights turning off", "stadium lights night",
      "computer monitor glow dark room"],
 10: ["dark bedroom computer monitor glow", "empty desk chair night room",
      "teenage bedroom desk night", "microphone desk dark room"],
 11: ["dark hallway closed door light", "corridor light under door night",
      "empty hallway dim house"],
 13: ["plate of food on table overhead", "meal on table untouched",
      "dinner plate close up table"],
 17: ["wall calendar close up", "calendar pages turning",
      "burning paper embers dark"],
 18: ["unmade empty bed dark room", "bedroom curtains drawn daylight",
      "empty bed morning light room"],
 # "many small lights in the dark" returned starfields so dark that the
 # finished cut had 11.4 SECONDS of near-black (mean luminance 3/255) under
 # "hundreds of thousands of Americans live with this. There is no cure."
 # blackdetect caught it; the contact sheet did not, because a dark frame in
 # a grid just looks like a dark shot. Ask for lit crowds, not for space.
 19: ["aerial city lights at night", "crowd of people from above night",
      "city window lights dusk", "packed stadium crowd from above"],
 20: ["hospital iv drip stand room", "infusion clinic chair empty",
      "hospital room empty bed iv"],
 21: ["iv drip chamber close up", "intravenous drip falling drop",
      "hospital iv bag close up"],
 23: ["plain meal on plate overhead", "simple healthy meal table",
      "meal prep containers table"],
 24: ["glass of water bedside table", "water glass condensation close up",
      "glass of water dark room"],
 25: ["camera equipment studio gear", "video production equipment room",
      "studio lights cameras setup", "hard drives monitors desk"],
 27: ["video editing timeline screen", "editing software monitor night",
      "person editing video dark room"],
 29: ["industrial machinery gears factory", "conveyor belt factory running",
      "heavy machine factory dark"],
 30: ["clock mechanism macro gears", "mechanical watch escapement close up",
      "clock gears turning macro"],
 31: ["giant gears turning machinery", "clockwork mechanism close up",
      "industrial gears silhouette"],
 # The line is "it was a second person and a rule". The old query returned a
 # lone man in a bare room and empty cubicles - solitude, which is the
 # OPPOSITE of the sentence. Two of something, always.
 33: ["two chairs facing each other", "two people talking across a table",
      "two people shaking hands table", "pair of chairs facing"],
 34: ["signing contract document pen", "hand signing paper close up",
      "contract signature desk"],
 35: ["legal document close up text", "paper document macro text",
      "contract paper close up"],
 36: ["tattoo needle machine close up", "tattoo artist needle macro",
      "tattoo machine working close up"],
 37: ["paper pinned notice board", "documents on wall corridor",
      "hand pinning paper board"],
 39: ["calendar days marked crossed", "wall calendar close up marking",
      "hand marking calendar"],
 40: ["empty gym squat rack", "empty gym weights dark",
      "barbell rack gym empty"],
 41: ["redacted document black lines", "confidential document paper",
      "document pages close up"],
 43: ["single chair empty room", "empty room chair light",
      "chairs in empty hall"],
 45: ["data visualisation grid screen", "abstract glowing squares screen",
      "digital grid animation dark"],
 47: ["blank sheet of paper desk", "handwriting on paper close up",
      "notebook blank page macro"],
 50: ["time lapse seasons window", "time lapse day to night window",
      "seasons changing landscape time lapse"],
 51: ["barbell on gym floor", "barbell plates chalk close up",
      "gym floor weights still"],
 52: ["heavy stone block moving", "pushing heavy object floor",
      "large rock dark ground"],
 53: ["barbell lifting close up plates", "weight plates macro gym",
      "barbell bar knurling close up"],
 54: ["equations on blackboard", "writing formula chalkboard",
      "mathematics blackboard close up"],
 55: ["tape measure close up macro", "measuring tape pulled out",
      "tape measure body measurement"],
 56: ["hydraulic press machine", "industrial press concrete wall",
      "hydraulic cylinder machinery"],
 57: ["phone face down table", "coffee cup table dim room",
      "still table objects dark room"],
 58: ["interlocking gears close up", "gears meshing machinery macro",
      "machine gears turning dark"],
 61: ["grid of lights going dark", "screen pixels fading black",
      "digital squares abstract dark"],
 63: ["running shoes by door", "shoes entryway home", "trainers on floor room"],
 64: ["dark bedroom before sunrise", "curtain light dark bedroom",
      "bedroom window dawn light"],
 65: ["light beam darkness", "shaft of light dark room",
      "sunlight through darkness dust"],
 66: ["abandoned baseball field overgrown", "derelict sports field weeds",
      "rusted fence overgrown field"],
 68: ["running shoes doorway morning", "front door opening light",
      "shoes by entrance home light"],
 69: ["pill bottle glass water counter", "medication bottle close up",
      "taking pills with water"],
 70: ["water flowing over stones", "water eroding rock macro",
      "stream over smooth stones"],
 72: ["single lamp dark empty space", "lamp glowing dark room wide",
      "light in large dark room"],
 73: ["hand switching off lamp", "turning off light dark room",
      "lamp switch off night"],
}


def api(url: str) -> dict:
    r = urllib.request.Request(url, headers={"Authorization": KEY,
                                             "User-Agent": UA})
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def pick_file(v: dict):
    files = [f for f in (v.get("video_files") or [])
             if (f.get("width") or 0) >= 1280
             and (f.get("width") or 0) >= (f.get("height") or 1)]
    if not files:
        return None
    return sorted(files, key=lambda x: -(x.get("width") or 0))[0]


def download(job):
    seg, v, f = job
    dst = DEST / f"s{str(seg).replace('.', '_').replace('-', 'm')}_{v['id']}.mp4"
    try:
        rq = urllib.request.Request(f["link"], headers={"User-Agent": UA})
        with urllib.request.urlopen(rq, timeout=300) as r:
            dst.write_bytes(r.read())
    except Exception as e:                                       # noqa: BLE001
        return None, f"{v['id']}: {type(e).__name__}"
    return {
        "file": f"library/broll7/{dst.name}", "segment": seg,
        "pexels_id": v["id"], "url": v.get("url"),
        "photographer": (v.get("user") or {}).get("name"),
        "duration": v.get("duration"), "width": f.get("width"),
        "height": f.get("height"),
        "license": "Pexels licence - credited in description"}, None


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    from fetched_ids import known_ids
    seen = known_ids()
    print(f"[skip] {len(seen)} ids already downloaded project-wide", flush=True)

    # Optional segment filter: `fetch_broll7.py 61 63 68` refetches just those.
    # Without it every segment is fetched again, which on a second run means
    # five MORE clips for segments that are already supplied.
    want = WANT
    if len(sys.argv) > 1:
        picked = {float(a) if "." in a else int(a) for a in sys.argv[1:]}
        want = {k: v for k, v in WANT.items() if k in picked}
        print(f"[filter] {len(want)} of {len(WANT)} segments: "
              f"{sorted(want, key=float)}", flush=True)

    jobs = []
    for seg, queries in want.items():
        picked = 0
        for q in queries:
            if picked >= PER_SEG:
                break
            try:
                d = api("https://api.pexels.com/videos/search?"
                        + urllib.parse.urlencode(
                            {"query": q, "per_page": 15,
                             "orientation": "landscape", "size": "medium"}))
            except Exception as e:                               # noqa: BLE001
                print(f"[warn] seg {seg} '{q}': {e}")
                continue
            for v in d.get("videos", []):
                if picked >= PER_SEG:
                    break
                if v["id"] in seen:
                    continue
                if not (MIN_DUR <= (v.get("duration") or 0) <= MAX_DUR):
                    continue
                f = pick_file(v)
                if not f:
                    continue
                seen.add(v["id"])
                jobs.append((seg, v, f))
                picked += 1
        print(f"[seg {seg:>5}] queued {picked}", flush=True)

    print(f"\n[download] {len(jobs)} clips on {WORKERS} workers", flush=True)
    cred, fails = [], []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(download, j): j for j in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            rec, err = fut.result()
            if err:
                fails.append(err)
            else:
                cred.append(rec)
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    # MERGE, never overwrite. Writing this file fresh on each run destroyed
    # the attribution for every clip fetched in an earlier round - by the end
    # only 4 of 189 clips in the cut had a photographer on record, and Pexels
    # attribution is a licence condition. See repair_broll7_credits.py.
    cpath = DEST / "CREDITS.json"
    merged = {}
    if cpath.exists():
        try:
            for r in json.loads(cpath.read_text(encoding="utf-8")):
                merged[r["file"]] = r
        except json.JSONDecodeError:
            pass
    for r in cred:
        merged[r["file"]] = r
    cpath.write_text(json.dumps(list(merged.values()), indent=2),
                     encoding="utf-8")
    print(f"\n[OK] {len(cred)} clips -> {DEST}")
    if fails:
        print(f"[fail] {len(fails)}: {fails[:5]}")
    print("     NOTHING IS CLEARED. Run pipeline/screen_broll7.py next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
