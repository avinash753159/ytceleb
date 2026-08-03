"""Append the owner's slide-44 direction to the plan as an explicit policy.

His note: "all the images where you have his face, which is pretty much all of
them up until 172, you need to change it up to something that does make more
sense." And, asked directly which sync shots survive: keep sync only on the
lines that carry the film.

Expressing that as a transform rather than sixty hand edits keeps it readable
and reversible - the policy states what it does and why, and the segment-by-
segment plan above it stays the record of intent.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
q = ROOT / "pipeline/picture_plan_v8.py"
t = q.read_text(encoding="utf-8")

POLICY = '''

# ==================================================================
# OWNER DIRECTION, review deck slide 44
# ==================================================================
# "Again change it up for 91 and all the images where you have his face,
#  which is pretty much all of them up until 172, you need to change it up
#  to something that does make more sense."
#
# And, asked which of the 21 sync shots survive: keep sync only on the
# biggest moments. So the talking head is stripped out of everything from
# the illness chapter onward, except on the lines that carry the film.
#
# This runs as a transform over PLAN so the intent above stays readable and
# the change stays reversible. Segments 16 and below are NOT touched - the
# owner gave those individual notes and they are applied by hand above.

# The lines that carry the film. Everything else loses its sync shot.
KEEP_SYNC = {
    6,    # "I played baseball nonstop, and then when I got Crohn's I lost
          #  like 50 pounds"        - the origin
    8,    # "190 pounds down to 139 ... all in on YouTube" - the pivot
    12,   # the symptoms, in his own words
    38,   # "Today was day 310. Me and Eric signed a contract"
    42,   # "three things my entire world revolves around"
    44,   # "I'd probably upload more if I didn't work out" - the cost
    49,   # "work out for three months really consistently"
    60,   # "it's really killing me, to be honest" - hands over his face
    62,   # "45 minutes, 5 days a week ... the bigger problem is sleep"
    71,   # "It's just life." - the closing line
}
SWEEP_FROM = 17          # slide 44 sits in segment 16; 16 and below are hand-set

# What replaces a face shot, per chapter. Ordered by preference; the builder
# takes the first group with an unspent clip, so a thin group degrades to the
# next rather than failing the build.
_BY_CHAPTER = {
    "illness":    ["gut_pain", "eating", "meds", "clinic", "tired", "food"],
    "machine":    ["editing", "night_work", "desk", "clock", "tired"],
    "contract":   ["training", "eq_barbell", "gym_room", "eq_dumbbell",
                   "athlete"],
    "protocol":   ["training", "walk", "eq_machine", "eq_dumbbell", "walk2"],
    "limit":      ["gym_room", "eq_barbell", "tired", "training"],
    "fall":       ["tired", "bed", "night_work", "editing", "clock"],
    "resolution": ["walk", "athlete", "training", "bed", "meds", "tired"],
}
# segment index -> chapter, read off manifest/edl_full.json
_CHAPTER_OF = {}
try:
    import json as _json
    import pathlib as _pl
    _edl = _json.loads((_pl.Path(__file__).resolve().parents[1]
                        / "manifest/edl_full.json").read_text(encoding="utf-8"))
    for _s in _edl["segs"]:
        _CHAPTER_OF[_s["i"]] = _s.get("chapter", "")
except Exception:                                              # noqa: BLE001
    pass


def _face_free(seg_i, slots):
    """Swap the talking head out of one segment's slots."""
    chapter = _CHAPTER_OF.get(seg_i, "")
    groups = _BY_CHAPTER.get(chapter) or ["tired", "training", "walk"]
    out, k = [], 0
    for slot in slots:
        if slot[0] == "fix":
            cap, spec = slot[1], slot[2]
            head = ("fix", cap)
        else:
            cap, spec = None, slot[1]
            head = (slot[0],)
        kind = spec[0]
        drop = (kind in ("jimmy", "teen")
                or (kind == "sync" and seg_i not in KEEP_SYNC))
        if drop:
            spec = ("broll", groups[k % len(groups)])
            k += 1
            # a sync slot was sized to its window; as stock it is a normal slot
            if head[0] == "fix":
                head = (1,)
        out.append((*head, spec) if head[0] == "fix" else (head[0], spec))
    return out


for _i in list(PLAN):
    try:
        _n = int(float(_i))
    except (TypeError, ValueError):
        continue
    if _n < SWEEP_FROM:
        continue
    _slots, _why = PLAN[_i]
    _new = _face_free(_n, _slots)
    if _new != _slots:
        PLAN[_i] = (_new, _why + "  [OWNER slide 44: talking head removed]")
'''

if "OWNER DIRECTION, review deck slide 44" in t:
    print("policy already present")
else:
    t = t.rstrip() + POLICY
    q.write_text(t, encoding="utf-8")
    print("face-sweep policy appended to picture_plan_v8.py")
