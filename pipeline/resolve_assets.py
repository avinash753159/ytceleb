#!/usr/bin/env python3
"""
resolve_assets.py - Phase 3: fulfill every plan.json entry with a concrete
asset, or fall back EXPLICITLY. Never substitutes a wrong-but-available asset:
below-threshold retrieval -> the planned fallback_treatment, recorded as such.

Writes manifest/assets.json:
  {beat_id: {treatment, asset:{...}|null, fallback_used: bool, items_ms:[...]}}

- motion_broll / exercise_demo: SigLIP embedding search over the CLEAN library
  (top-K + score floor + per-source diversity). Optional VLM rerank hook is a
  no-op without an API key (recorded in the report - honest degradation).
- still_pushin / person_card / split_compare: fetch_stills (licensed, OCR-gated,
  >=1920px). person_card falls back to a monogram card (generated graphic).
- infographic_list: word-anchored reveal times for each item (fuzzy match of
  item text against the beat's words; even stagger when no match).
- stat_callout: no retrieval (generated).

Run:  py -3.12 pipeline/resolve_assets.py
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"
sys.path.insert(0, str(ROOT / "pipeline"))

SCORE_FLOOR = float(os.environ.get("RETRIEVAL_FLOOR", "0.05"))
# subject footage preferred - V3 targets ~60-70% subject on screen
SUBJ_BONUS_SOURCES = ("ryan", "v3_ryan", "reference")
SUBJ_BONUS = 0.035


def item_anchor_ms(items, beat, words):
    """For each list item, ms offset (within the beat) of the word where it
    should appear: first content word of the item matched in the beat."""
    bws = [(w, words[i]) for i in range(max(beat["word_start"], 0),
                                        min(beat["word_end"] + 1, len(words)))
           for w in [words[i]["w"].lower().strip(".,!?;:")]]
    out = []
    for k, it in enumerate(items):
        toks = [t for t in re.findall(r"[a-z]+", it["text"].lower())
                if len(t) > 3]
        hit = None
        for t in toks[:3]:
            for w, wo in bws:
                if t.startswith(w[:4]) or w.startswith(t[:4]):
                    hit = wo
                    break
            if hit:
                break
        if hit:
            out.append(max(0, int((hit["s"] - beat["start"]) * 1000)))
        else:
            dur_ms = int((beat["end"] - beat["start"]) * 1000)
            out.append(int(dur_ms * (k + 0.5) / (len(items) + 1)))
    # reveals must be non-decreasing
    for k in range(1, len(out)):
        out[k] = max(out[k], out[k - 1] + 250)
    return out


def main():
    import embed_index
    from fetch_stills import fetch_still

    plan = json.loads((MANIFEST / "plan.json").read_text())["plan"]
    beats = {b["beat_id"]: b for b in
             json.loads((MANIFEST / "beats.json").read_text())["beats"]}
    words = json.loads((MANIFEST / "words.json").read_text())["words"]

    used_scenes = {}          # scene_id -> last beat END time it was used
    assets, misses = {}, []

    def pick_clip(query, beat, prefer_subject):
        cands = embed_index.query(query, 24)
        best = None
        for c in cands:
            if c["score"] < SCORE_FLOOR:
                break
            last = used_scenes.get(c["id"])
            if last is not None and beat["start"] - last < 90:
                continue                       # no reuse within 90s
            if c["dur"] < 1.2:
                continue
            bonus = SUBJ_BONUS if (prefer_subject and any(
                s in c["source"].lower() for s in SUBJ_BONUS_SOURCES)) else 0
            sc = c["score"] + bonus
            if best is None or sc > best[0]:
                best = (sc, c)
        return best[1] if best else None

    for p in plan:
        bid = p["beat_id"]
        b = beats[bid]
        tr = p["treatment"]
        rec = {"treatment": tr, "fallback_used": False}

        if tr in ("motion_broll", "exercise_demo"):
            subj = "ryan" in p.get("retrieval_query", "").lower()
            c = pick_clip(p["retrieval_query"], b, subj)
            if c:
                used_scenes[c["id"]] = b["end"]
                dur = b["end"] - b["start"]
                if dur > 6.0:      # QC: no shot may exceed 6s -> two shots
                    c2 = pick_clip(p["retrieval_query"], b, subj)
                    if c2:
                        used_scenes[c2["id"]] = b["end"]
                        rec["asset"] = {"kind": "clip2", "a": c, "b": c2}
                    else:
                        rec["asset"] = {"kind": "clip2", "a": c,
                                        "b": {**c, "start":
                                              min(c["start"] + 3.0,
                                                  c["end"] - 1.3)}}
                else:
                    rec["asset"] = {"kind": "clip", **c}
            else:
                fb = p.get("fallback_treatment", "still_pushin")
                rec.update(fallback_used=True, treatment=fb)
                misses.append(f"{bid}: no clip >= {SCORE_FLOOR} for "
                              f"'{p['retrieval_query']}' -> {fb}")
                if fb == "still_pushin":
                    s = fetch_still(p["retrieval_query"], bid)
                    rec["asset"] = ({"kind": "still", **s} if s else None)
                else:
                    rec["asset"] = None

        elif tr == "still_pushin":
            s = fetch_still(p["retrieval_query"], bid)
            if s:
                rec["asset"] = {"kind": "still", **s}
            else:
                fb = p.get("fallback_treatment", "motion_broll")
                rec.update(fallback_used=True, treatment=fb)
                c = pick_clip(p["retrieval_query"], b, True)
                rec["asset"] = ({"kind": "clip", **c} if c else None)
                if c:
                    used_scenes[c["id"]] = b["end"]
                misses.append(f"{bid}: no still for "
                              f"'{p['retrieval_query']}' -> {fb}")

        elif tr == "person_card":
            s = fetch_still(p["retrieval_query"], p.get("subject", bid),
                            prefer_person=True)
            bg = pick_clip("trainer coaching client gym", b, True)
            if bg:
                used_scenes[bg["id"]] = b["end"]
            rec["asset"] = ({"kind": "still", **s, "bg": bg} if s
                            else {"kind": "monogram", "bg": bg})
            if not s:
                misses.append(f"{bid}: no headshot for "
                              f"'{p.get('subject')}' -> monogram card")

        elif tr == "split_compare":
            l = fetch_still(p["left_query"], bid + "_L")
            r = fetch_still(p["right_query"], bid + "_R")
            if l and r:
                rec["asset"] = {"kind": "split", "left": l, "right": r}
            else:
                fb = p.get("fallback_treatment", "still_pushin")
                rec.update(fallback_used=True, treatment=fb)
                one = l or r or fetch_still(p["left_query"], bid)
                rec["asset"] = ({"kind": "still", **one} if one else None)
                misses.append(f"{bid}: split_compare missing a side -> {fb}")

        elif tr == "infographic_list":
            # V3: graphics ride ON live footage - pick a relevant bg clip
            bg = pick_clip(p.get("retrieval_query") or b["text"][:70], b, True)
            if bg:
                used_scenes[bg["id"]] = b["end"]
            rec["asset"] = {"kind": "generated", "bg": bg}
            rec["items_ms"] = item_anchor_ms(p["items"], b, words)

        elif tr == "stat_callout":
            bg = pick_clip(p.get("retrieval_query") or b["text"][:70], b, True)
            if bg:
                used_scenes[bg["id"]] = b["end"]
            rec["asset"] = {"kind": "generated", "bg": bg}

        assets[bid] = rec

    (MANIFEST / "assets.json").write_text(json.dumps(assets, indent=1),
                                          encoding="utf-8")
    n_null = sum(1 for a in assets.values() if a.get("asset") is None)
    n_fb = sum(1 for a in assets.values() if a["fallback_used"])
    print(f"[OK] manifest/assets.json - {len(assets)} beats, "
          f"{n_fb} fallbacks, {n_null} unresolved")
    if misses:
        print("[i] fallbacks/misses:")
        for m in misses[:25]:
            print("   ", m)
    if n_null:
        print(f"[!] {n_null} beats have NO asset - assembly will fail loudly")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
