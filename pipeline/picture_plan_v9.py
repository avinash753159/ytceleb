#!/usr/bin/env python3
"""V9 shot plan: every narration segment draws from footage found for THAT line.

WHAT CHANGED FROM V8
--------------------
V8 grouped stock by subject - "athlete", "tired", "gym_room", "walk2" - and
the plan picked a bucket per segment. A bucket is only as specific as its
name, so "tired" ended up under four different sentences that had nothing in
common beyond mood, and the owner's slide notes say "use stock footage again"
against shot after shot because what was there did not belong to the words.

Here every narration segment has its OWN group, `s<segment>`, filled by
fetch_broll7.py from searches written against that segment's exact line. The
plan below is therefore mostly mechanical: it splits each segment into slots
of at most SHOT_MAX seconds and points them all at that segment's own group.
The interesting decisions are the overrides.

WHAT IS NOT STOCK
-----------------
* Bites in KEEP_SYNC keep ("sync",) - his lips match the words. Untouched.
* Other bites still draw a verified present-day window: his voice, his face,
  a different moment. That is allowed; a bite over a cutaway is not.
* The eight bites with no clean frame (Airrack's video, the two Rogan
  stretches with a web page burned in behind him) go to their own stock group.
* Segments 2, 7, 14, 15, 16 are the mechanism of the disease and stay on the
  licensed medical stills. Stock video of an inflamed bowel is a cartoon or a
  different illness.
* The documents, cards and the flash frame carry over from V8 unchanged.

SHOT_MAX is 6.0 because HANDOFF rule 4 caps a shot at ~6s, and the split is
computed from the EDL rather than guessed, so no slot can violate it.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

# Everything that is not stock carries over from V8 exactly as it was.
from picture_plan_v8 import (CLIN, CLIPS, DOCS, FLASH,             # noqa: E402
                             KEEP_SYNC, PARALLAX, STILLS)

EDL = json.loads((ROOT / "manifest/edl_full.json").read_text(encoding="utf-8"))
SHOT_MAX = 6.0
MIN_SYNC = 1.6           # below this a sync cut reads as a glitch, not a face

# How much clean, verified, text-free window each bite actually has. The plan
# must not ask for more sync than exists - see the comment in build().
SYNC_AVAIL: dict[int, float] = {}
for _r in json.loads((ROOT / "manifest/bite_windows.json")
                     .read_text(encoding="utf-8")):
    _clean = [w for w in _r["runs"]
              if w.get("verified_jimmy") and not w.get("has_text")]
    SYNC_AVAIL[_r["i"]] = max([w.get("usable") or 0.0 for w in _clean],
                              default=0.0)

PLAN: dict = {}


def seg(i, slots, why):
    PLAN[i] = (slots, why)


# Bites where no clean Jimmy-only frame exists. Six are Airrack's video, where
# twelve windows were frame-checked and not one is Jimmy alone; 18 and 20 are
# the Rogan stretch with the Crohn's & Colitis Foundation site on the monitor
# behind him, which no crop removes. These are illustrated.
NO_CLEAN_FRAME = {18, 20, 34, 36, 53, 55, 67, 69}

# The mechanism of the disease, on licensed stills and real documents rather
# than stock. ONE ENTRY PER SLOT, ALL DISTINCT - rule 2 forbids drawing any
# asset twice, and cycling a short list with modulo broke the build:
#   Reuse: clin:histology already used at 004_2_0, asked again for 005_2_1
#
# These five segments need 13 slots between them and there are only seven
# medical images in the library, so the remainder are the primary documents -
# the NIDDK pages, the Crohn's & Colitis Foundation page, the 3D explainer -
# which belong under this narration anyway. menshealth_ba (190lb to 139lb)
# sits under segment 16 because that is the line about losing fifty pounds.
#
# crohns_real is NOT here: it is the flash frame at segment 48.
# A ("clin", ...) slot does NOT take an equal share: rule 13 pins clinical
# imagery to CLIN_HOLD seconds and gives it share 0, so the rest of the span
# is divided among the OTHER slots only. Counting slots as dur/6 ignored that
# and segment 15 came out at 2.2 + 7.30 + 7.30:
#   RuntimeError: span 15 slot 1 is 7.30s - rule 4 caps a shot at 6.0s
# Segment 15 therefore needs four assets, not three.
MEDICAL = {
    2:  [("clin", "histology"), ("still", "mech_left")],
    7:  [("still", "tract"), ("doc", "drvaidji_3d")],
    14: [("still", "mech_right"), ("still", "intestine"),
         ("doc", "niddk_def")],
    15: [("clin", "resected"), ("doc", "ccf_page"), ("doc", "niddk_treat"),
         ("doc", "niddk_diet")],
    # The third slot is stock, not a still: there is no eighth medical image
    # left, and "he was eating and none of it was absorbed" is carried
    # perfectly well by the plate of food found for segment 13.
    16: [("still", "villi"), ("doc", "menshealth_ba"), ("broll", "s16")],
}
CLIN_HOLD = 2.2          # rule 13, enforced in the builder at line ~792

# Hand-set, carried from V8 and from the owner's slide notes.
HAND = {
    -1: ([(1, ("doc", "nypost_before"))],
         "OWNER slide 1: do not lead on a talking head - open on the photo"),
    48: ([(1, ("flash", "crohns_real"))],
         "the card, one flash frame"),
}


def _n_slots(dur: float) -> int:
    return max(1, math.ceil(dur / SHOT_MAX))


def build() -> None:
    for s in EDL["segs"]:
        i, kind = s["i"], s["kind"]
        dur = s["end"] - s["start"]
        n = _n_slots(dur)
        grp = f"s{i}"

        if i in HAND:
            slots, why = HAND[i]
            seg(i, slots, why)
            continue

        if i in MEDICAL:
            picks = MEDICAL[i]
            # Clinical slots are pinned and take no share, so the flexible
            # slots divide what is LEFT after them - check that, not dur/6.
            n_clin = sum(1 for p in picks if p[0] == "clin")
            flex = len(picks) - n_clin
            per = (dur - n_clin * CLIN_HOLD) / flex if flex else 0.0
            if per > SHOT_MAX + 0.02:
                raise AssertionError(
                    f"segment {i}: {flex} flexible slots share "
                    f"{dur - n_clin * CLIN_HOLD:.2f}s = {per:.2f}s each, over "
                    f"the {SHOT_MAX}s cap. Add another asset to MEDICAL[{i}].")
            slots = [(1, p) for p in picks]
            seg(i, slots, "the mechanism, on licensed stills and documents")
            continue

        if kind == "bite":
            if i in KEEP_SYNC:
                # His lips on his words - but sized to the window that ACTUALLY
                # survived the identity and burned-in-text passes, not to a
                # flat 6s. Asking for 6s of sync on segment 44, whose longest
                # clean window is 5.56s, failed the build outright:
                #   Exhausted: seg 44 asked for 6.00s of sync and no verified
                #   clean window is long enough.
                # 44, 60 and 71 are all short (5.56s, 5.48s, 2.20s).
                avail = SYNC_AVAIL.get(i, 0.0)
                take = min(dur, SHOT_MAX, avail) if avail > 0 else 0.0
                if take < MIN_SYNC:
                    slots = [(1, ("broll", grp)) for _ in range(n)]
                    seg(i, slots,
                        f"KEEP_SYNC but only {avail:.2f}s of clean window "
                        f"exists - illustrated rather than faked")
                    continue
                slots = [("fix", take, ("sync",))]
                rest = dur - take
                # Overflow after the sync window is MORE OF HIM, not stock
                # from a neighbouring sentence. Segments 8, 12, 38, 49 and 62
                # are all long bites, and borrowing put styled pancakes under
                # "190 pounds down to 139" and a stranger at a desk under his
                # contract with Eric.
                for _ in range(_n_slots(rest) if rest > 0.4 else 0):
                    slots.append((1, ("jimmy", {})))
                seg(i, slots, "sync: the real man saying the real words")
            elif i in NO_CLEAN_FRAME:
                slots = [(1, ("broll", grp)) for _ in range(n)]
                seg(i, slots, "no clean Jimmy-only frame exists - illustrated")
            else:
                # ALL slots are him, not just the first. The overflow used to
                # borrow a neighbouring sentence's stock, and the review of
                # the finished cut showed exactly what that produces: styled
                # pancakes and dessert plating under "190 pounds down to 139,
                # I lost all the muscle I had", an unnamed woman at a desk
                # under his contract with Eric, and a tired stranger on a sofa
                # under his gym progress. His own face is always defensible
                # under his own voice, and the pool has 95 verified windows
                # against the 17 currently drawn.
                slots = [(1, ("jimmy", {})) for _ in range(n)]
                seg(i, slots, "his voice, so his face - all slots")
            continue

        slots = [(1, ("broll", grp)) for _ in range(n)]
        seg(i, slots,
            "narration - footage searched against this line, group " + grp)

    # Two spans exist in the builder but NOT in the EDL segment list, so the
    # loop above never reaches them and they must be set explicitly. Missing
    # the first one failed the build outright:
    #   KeyError: 'no plan for span -1 (0.00-2.00)'
    seg(6.5, [(1, ("broll", "s6.5"))], "title break, 4s, music only")
    for i, (slots, why) in HAND.items():
        if i not in PLAN:
            seg(i, slots, why)


build()

# Fall back to a neighbouring group if a segment's own group came up empty
# after screening, so a thin group degrades instead of failing the build.
FALLBACK = {
    "s-1": ["s72", "s65"], "s3": ["s5", "s13"], "s6.5": ["s5", "s66"],
    "s9": ["s10", "s25"], "s11": ["s18", "s64"], "s17": ["s39", "s41"],
    "s19": ["s61", "s45"], "s23": ["s13"], "s24": ["s57"], "s31": ["s29", "s58"],
    "s33": ["s43"], "s37": ["s41", "s47"], "s45": ["s61"], "s50": ["s64"],
    "s52": ["s56", "s29"], "s58": ["s29", "s31"], "s61": ["s45"],
    "s68": ["s63"], "s73": ["s72", "s65"],
    # Narration groups that came up short after screening. Named explicitly so
    # they borrow from the nearest SENTENCE rather than from whichever group
    # happens to be largest - falling through to "any" is the bucket behaviour
    # this rebuild exists to remove.
    #   s21 the drip: every top-up came back a kitchen faucet or a leaf
    #   s39 the calendar: every top-up was a desk planner, not a wall calendar
    #   s66 the derelict field: two usable, third borrows the live diamond
    "s21": ["s20"], "s39": ["s17", "s41"], "s66": ["s6.5", "s5"],
    # Segment 16's third slot is stock by design - see MEDICAL[16].
    "s16": ["s13", "s23"],
    # Bite segments have no group of their own: their picture is his face, and
    # stock only fills a slot left over when the bite runs longer than one
    # shot. Each points at the nearest sentence by subject, never at a bucket.
    "s1": ["s18", "s57"], "s6": ["s5", "s66"], "s8": ["s13", "s23"],
    "s12": ["s11", "s18"], "s22": ["s23", "s13"], "s26": ["s10", "s25"],
    "s28": ["s10", "s11"], "s32": ["s40", "s51"], "s38": ["s39", "s34"],
    "s42": ["s41", "s27"], "s44": ["s45", "s27"], "s46": ["s55", "s53"],
    "s49": ["s50", "s63"], "s59": ["s29", "s25"], "s60": ["s57", "s18"],
    "s62": ["s64", "s18"], "s67": ["s63", "s68"], "s71": ["s72", "s65"],
}
