#!/usr/bin/env python3
"""v5_build_assets.py - compile manifest/assets_v5.json from the clip plan.

Beat types:
  cut     - exact [t0,t1] from a FULL dossier download (dossier/ryan/<id>.mp4)
  v5card  - full-screen reference-style graphic (comp + props)
  library - keep the V4 judge-verified asset (assets.json entry)

Graphic assignments (V5 style contract):
  TypeOn   b_003          - the hook question types itself
  SiteZoom b_004 (saladino programs + yellow highlight), b_024 (MH article)
  IconBurst all LIST beats - items as satellite icon cards flying in
  BarsRise  single/multi STAT beats
  MacroApp  b_064 (daily targets app mock)
  PeopleRow b_087 ("most people can't train 6 days")
  EraCard   handled via footage per plan (era clips are stronger)
"""
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOSS = ROOT / "dossier" / "ryan"

plan_clips = json.loads((MAN / "v5_plan.json").read_text(encoding="utf-8"))
v4_plan = {p["beat_id"]: p for p in
           json.loads((MAN / "plan.json").read_text())["plan"]}
v4_assets = json.loads((MAN / "assets.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}
words = json.loads((MAN / "words.json").read_text())["words"]


def ts_to_s(ts):
    m = re.match(r"(\d+):(\d+)", ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def parse_range(ts):
    m = re.match(r"(\d+:\d+)\s+to\s+(\d+:\d+)", ts)
    if not m:
        return None
    return ts_to_s(m.group(1)), ts_to_s(m.group(2))


def item_ms(items, bid):
    """Word-anchored reveal offsets for list items."""
    b = beats[bid]
    span = int((b["end"] - b["start"]) * 1000)
    n = len(items)
    return [int(span * (i + 0.6) / (n + 1)) for i in range(n)]


def durl(p, mime="image/png"):
    return f"data:{mime};base64," + \
        base64.b64encode(Path(p).read_bytes()).decode()


ICON = {"chest": "🏋️", "back": "🔙", "leg": "🦵", "shoulder": "🤸",
        "arm": "💪", "core": "🧱", "cardio": "⚡", "boxing": "🥊",
        "rest": "😴", "food": "🍗", "meal": "🍽️", "egg": "🍳",
        "chicken": "🍗", "salmon": "🐟", "oat": "🥣", "coffee": "☕",
        "shake": "🥤", "swing": "🏋️", "jump": "📦", "rope": "🪢",
        "carb": "🍚", "sugar": "🚫", "water": "💧", "train": "🏋️",
        "diet": "🥗", "recover": "🛌", "sleep": "😴"}


def pick_icon(text):
    t = text.lower()
    for k, v in ICON.items():
        if k in t:
            return v
    return "✅"


SITEZOOMS = {
    "b_004": {"shot": "library/sites/saladino_programs.png",
              "label": "donsaladino.com/all-programs",
              "focusY": 0.22, "zoomTo": 1.5,
              "highlightRect": {"x": 30, "y": 36.5, "w": 40, "h": 4.5}},
    "b_024": {"shot": "library/sites/mh_dp2_article.png",
              "label": "menshealth.com - Train Like a Celebrity",
              "focusY": 0.10, "zoomTo": 1.45,
              "highlightRect": {"x": 12, "y": 15, "w": 60, "h": 5}},
}

out = {}
for bid in sorted(beats):
    b = beats[bid]
    p4 = v4_plan.get(bid, {})
    tr = p4.get("treatment", "motion_broll")
    dur = round(b["end"] - b["start"], 3)

    # --- V5 graphic beats -------------------------------------------
    if bid == "b_003":
        out[bid] = {"type": "v5card", "comp": "TypeOn",
                    "props": {"text": "how does Ryan Reynolds actually "
                                      "train and eat?", "cps": 26}}
        continue
    if bid in SITEZOOMS:
        s = SITEZOOMS[bid]
        out[bid] = {"type": "v5card", "comp": "SiteZoom",
                    "props": {"src": durl(ROOT / s["shot"]),
                              "label": s["label"], "zoomTo": s["zoomTo"],
                              "focusY": s["focusY"],
                              "highlightRect": s["highlightRect"],
                              "highlightAtMs": 900}}
        continue
    if bid == "b_064":
        out[bid] = {"type": "v5card", "comp": "MacroApp", "props": {}}
        continue
    if bid == "b_087":
        out[bid] = {"type": "v5card", "comp": "PeopleRow",
                    "props": {"count": 5, "caption":
                              "MOST PEOPLE CAN'T TRAIN 6 DAYS A WEEK",
                              "highlightIndex": 2}}
        continue
    if tr == "infographic_list":
        items = p4.get("items", [])
        ms = item_ms(items, bid)
        sats = [{"icon": pick_icon(it["text"]), "label": it["text"][:22],
                 "atMs": ms[i]} for i, it in enumerate(items)]
        out[bid] = {"type": "v5card", "comp": "IconBurst",
                    "props": {"center": "💪", "satellites": sats,
                              "label": p4.get("title", "")[:34],
                              "labelAtMs": min(ms[-1] + 500,
                                               int(dur * 1000) - 800)}}
        continue
    if tr == "stat_callout":
        val = p4.get("value", "")
        nums = re.findall(r"[\d,]+", val)
        v0 = int(nums[0].replace(",", "")) if nums else 1
        out[bid] = {"type": "v5card", "comp": "BarsRise",
                    "props": {"title": p4.get("label", "").upper()[:36],
                              "bars": [{"label": p4.get("label", "")[:20],
                                        "value": v0, "display": val}]}}
        continue

    # --- footage beats: exact cut from the clip plan ----------------
    clips = plan_clips.get(bid, [])
    cut = None
    for c in clips:
        m = re.search(r"watch\?v=([\w-]{11})", c["url"])
        rng = parse_range(c["ts"])
        if m and rng:
            f = DOSS / f"{m.group(1)}.mp4"
            if f.exists() and f.stat().st_size > 500_000:
                cut = {"src": str(f), "t0": rng[0], "t1": rng[1],
                       "title": c["title"][:60], "vid": m.group(1)}
                break
    if cut:
        out[bid] = {"type": "cut", **cut}
    else:
        out[bid] = {"type": "library"}   # V4 judge-verified fallback

json.dump(out, open(MAN / "assets_v5.json", "w"), indent=1)
from collections import Counter
c = Counter(v["type"] for v in out.values())
cards = Counter(v.get("comp") for v in out.values() if v["type"] == "v5card")
print("assets_v5:", dict(c), "| cards:", dict(cards))
