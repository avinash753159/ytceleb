#!/usr/bin/env python3
"""
plan_treatments.py - Phase 2 step 3: assign one visual treatment per beat.

manifest/plan.json is THE CONTRACT: everything downstream is a pure function
of it; nothing after this stage may invent a treatment.

Treatments: motion_broll | still_pushin | person_card | exercise_demo |
            infographic_list | stat_callout | split_compare

Hard rules (enforced by validate_plan, whatever produced the plan):
  R1 enumerated count -> infographic_list with exactly N items
  R2 named person other than the subject -> person_card
  R3 subject's body/size/weight/transformation -> still_pushin | split_compare
  R4 named exercise -> exercise_demo (fallback still/infographic, never
     an unrelated clip)
  R5 same treatment never more than 3 consecutive beats
  R6 beats tile the narration; every beat has exactly one treatment

Modes:
  --signals        write manifest/plan_signals.json (deterministic pre-pass
                   the planner LLM builds on)
  --from FILE      take LLM-authored assignments, validate, write plan.json
  (with ANTHROPIC_API_KEY / anthropic_key.txt present, --auto calls Claude)
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"

TREATMENTS = {"motion_broll", "still_pushin", "person_card", "exercise_demo",
              "infographic_list", "stat_callout", "split_compare"}

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8}
# things you can actually SHOW as an N-item list ("7 day routine" counts via
# the routine/split/plan special case; durations and rates are stats, not lists)
COUNTABLE = r"(sets?|moves?|exercises?|rules?|steps?|meals?|phases?|" \
            r"principles?|workouts?|circuits?|mistakes?|tips?|ways)"
DAY_LIST = r"days?[- ](?:routine|split|plan|breakdown|schedule)"

BODY_KEYS = re.compile(
    r"\b(shredded|lean(?:er)?|physique|pounds of muscle|body fat|abs|jacked|"
    r"ripped|transformation|transformed|bulked?|weighed|vascular|"
    r"camera[- ]ready)\b")
PEOPLE_PREFIX_STOP = {"for", "then", "and", "but", "with", "the", "his",
                      "her", "most", "here", "look", "now"}
NOT_PEOPLE = re.compile(
    r"deadpool|wolverine|lantern|blade|trinity|free guy|hollywood|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"romanian|bulgarian|greek|men'?s health")

EXERCISE_KEYS = [
    ("bench press", ["bench press", "incline press", "chest press",
                     "dumbbell press", "flye", "flyes"]),
    ("pushup", ["push-up", "push up", "pushup"]),
    ("dip", ["dips", " dip "]),
    ("pullup", ["pull-up", "pull up", "pulldown", "chin-up", "chin up"]),
    ("row", ["barbell row", "dumbbell row", "bent-over row", " rows", " row "]),
    ("deadlift", ["deadlift", "romanian", "trap bar", "rdl"]),
    ("squat", ["squat", "goblet"]),
    ("lunge", ["lunge"]),
    ("carry", ["farmer", "carries", "loaded carry", "suitcase carry"]),
    ("kettlebell", ["kettlebell", "swing"]),
    ("boxing", ["boxing", "pad work", "sparring"]),
    ("jump rope", ["jump rope", "skipping"]),
    ("sprint", ["sprint", "treadmill", "prowler", "sled", "battle rope"]),
    ("curl", ["curl", "bicep"]),
    ("overhead press", ["overhead press", "shoulder press", "lateral raise",
                        "rear delt"]),
    ("plank", ["plank", "hollow hold"]),
    ("stretch", ["foam roll", "stretch", "mobility"]),
]


def load_cfg():
    cfg = {}
    if (ROOT / "config.json").exists():
        cfg = json.loads((ROOT / "config.json").read_text())
    return cfg


def find_count(text):
    """(N, phrase) if the beat truly ENUMERATES N showable things.
    Ranges ('three to five sets') and rates ('6 days a week') are stats."""
    t = " " + text.lower() + " "

    def rangey(m):        # 'to 5 sets' / '3 to 5 ...' is a range, not a list
        return bool(re.search(r"to\s*$", t[:m.start()]))

    m = re.search(rf"\b(\d)[- ]?(?:{COUNTABLE}|{DAY_LIST})", t)
    if m and 2 <= int(m.group(1)) <= 8 and not rangey(m):
        return int(m.group(1)), m.group(0).strip()
    for w, v in NUM_WORDS.items():
        m = re.search(rf"\b{w}[- ](?:{COUNTABLE}|{DAY_LIST})", t)
        if m and 2 <= v <= 8 and not rangey(m):
            return v, m.group(0).strip()
    return None


def find_stat(text):
    """A number/weight/duration/percent worth a stat_callout."""
    m = re.search(r"\b(\d{1,4}(?:[.,]\d{1,3})?)\s?(pounds?|lbs?|kilos?|kg|"
                  r"percent|%|calories|grams?|years? old|weeks?|months?|"
                  r"days? a week|hours?|minutes?)\b", text.lower())
    return m.group(0) if m else None


def find_people(text, subject_words, coach_name):
    """Capitalized bigrams that are not the subject -> candidate people."""
    people = []
    if coach_name and coach_name.lower() in text.lower():
        people.append(coach_name)
    for m in re.finditer(r"\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b", text):
        cand = f"{m.group(1)} {m.group(2)}"
        cl = cand.lower()
        if m.group(1).lower() in PEOPLE_PREFIX_STOP:
            continue                      # "Then Deadpool", "For Deadpool"...
        if NOT_PEOPLE.search(cl):
            continue                      # movie titles, weekdays, cuisines
        if any(w in cl for w in subject_words):
            continue
        if coach_name and cl == coach_name.lower():
            continue
        people.append(cand)
    return list(dict.fromkeys(people))


def find_exercise(text):
    t = " " + text.lower() + " "
    for name, keys in EXERCISE_KEYS:
        if any(k in t for k in keys):
            return name
    return None


def body_signal(text):
    return bool(BODY_KEYS.search(text.lower()))


def compare_signal(text):
    t = text.lower()
    return bool(re.search(r"\b(before|then came back|versus|vs\.?|compared|"
                          r"at 38.*at 47|from .* to )\b", t))


def build_signals():
    cfg = load_cfg()
    subject = cfg.get("subject", "Ryan Reynolds")
    coach = cfg.get("coach", "")
    subj_words = [w.lower() for w in subject.split()]
    beats = json.loads((MANIFEST / "beats.json").read_text())["beats"]
    out = []
    for b in beats:
        t = b["text"]
        sig = {
            "beat_id": b["beat_id"], "text": t,
            "start": b["start"], "end": b["end"],
            "count": find_count(t),
            "stat": find_stat(t),
            "people": find_people(t, subj_words, coach),
            "exercise": find_exercise(t),
            "body": body_signal(t),
            "compare": compare_signal(t),
        }
        out.append(sig)
    (MANIFEST / "plan_signals.json").write_text(json.dumps(out, indent=1),
                                               encoding="utf-8")
    n = len(out)
    print(f"[OK] plan_signals.json - {n} beats | "
          f"counts:{sum(1 for s in out if s['count'])} "
          f"stats:{sum(1 for s in out if s['stat'])} "
          f"people:{sum(1 for s in out if s['people'])} "
          f"exercise:{sum(1 for s in out if s['exercise'])} "
          f"body:{sum(1 for s in out if s['body'])}")
    return out


def validate_plan(plan, beats, signals):
    """Hard rules. Returns list of violations (empty = valid)."""
    errs = []
    by_id = {p["beat_id"]: p for p in plan}
    sig_by_id = {s["beat_id"]: s for s in signals}
    if len(plan) != len(beats):
        errs.append(f"R6: plan has {len(plan)} entries, beats {len(beats)}")
    for b in beats:
        p = by_id.get(b["beat_id"])
        if not p:
            errs.append(f"R6: missing {b['beat_id']}")
            continue
        tr = p.get("treatment")
        if tr not in TREATMENTS:
            errs.append(f"{b['beat_id']}: unknown treatment {tr!r}")
            continue
        if b.get("tail") or not b.get("text"):
            continue                      # music-only tail: any treatment ok
        s = sig_by_id.get(b["beat_id"], {})
        cnt = s.get("count")
        ppl = s.get("people")
        # R1/R2 precedence: a beat that both enumerates AND names a person
        # may satisfy either rule
        if cnt and tr != "infographic_list" \
                and not (ppl and tr == "person_card"):
            errs.append(f"R1 {b['beat_id']}: enumerates '{cnt[1]}' but "
                        f"treatment={tr}")
        if tr == "infographic_list":
            items = p.get("items") or []
            want = (cnt[0] if cnt else len(items)) or 0
            if not items or (cnt and len(items) != cnt[0]):
                errs.append(f"R1 {b['beat_id']}: needs exactly {want} items, "
                            f"got {len(items)}")
        if ppl and tr != "person_card" \
                and not (cnt and tr == "infographic_list"):
            errs.append(f"R2 {b['beat_id']}: names {ppl} but "
                        f"treatment={tr}")
        if tr == "person_card" and not p.get("subject"):
            errs.append(f"R2 {b['beat_id']}: person_card without subject")
        if s.get("body") and not s.get("people") and not cnt \
                and not s.get("exercise") \
                and tr not in ("still_pushin", "split_compare"):
            errs.append(f"R3 {b['beat_id']}: body description but "
                        f"treatment={tr}")
        if s.get("exercise") and not s.get("people") and not cnt \
                and tr not in ("exercise_demo", "infographic_list",
                               "still_pushin"):
            errs.append(f"R4 {b['beat_id']}: names exercise "
                        f"'{s['exercise']}' but treatment={tr}")
        if tr == "exercise_demo" and not p.get("exercise"):
            errs.append(f"R4 {b['beat_id']}: exercise_demo without exercise")
    run, prev = 1, None
    for b in beats:
        tr = (by_id.get(b["beat_id"]) or {}).get("treatment")
        run = run + 1 if tr == prev else 1
        if run > 3:
            errs.append(f"R5 {b['beat_id']}: '{tr}' {run} in a row")
        prev = tr
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", action="store_true")
    ap.add_argument("--from", dest="from_file",
                    help="LLM-authored assignments to validate + finalize")
    args = ap.parse_args()

    if args.signals:
        build_signals()
        return 0

    if args.from_file:
        beats = json.loads((MANIFEST / "beats.json").read_text())["beats"]
        signals = json.loads((MANIFEST / "plan_signals.json").read_text())
        plan = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        if isinstance(plan, dict):
            plan = plan["plan"]
        errs = validate_plan(plan, beats, signals)
        if errs:
            print(f"[!] PLAN INVALID - {len(errs)} violations:")
            for e in errs[:40]:
                print("   ", e)
            return 1
        (MANIFEST / "plan.json").write_text(
            json.dumps({"plan": plan}, indent=1), encoding="utf-8")
        from collections import Counter
        dist = Counter(p["treatment"] for p in plan)
        print(f"[OK] manifest/plan.json - {len(plan)} beats: "
              + ", ".join(f"{k}:{v}" for k, v in dist.most_common()))
        return 0

    print("usage: --signals | --from FILE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
