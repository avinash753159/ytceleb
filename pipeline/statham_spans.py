#!/usr/bin/env python3
"""statham_spans.py - F1 fix: concept cards cover their WHOLE narration
span (start phrase -> end phrase), and list items appear at the exact
moment their word is spoken (words.json lookup inside the span).

Rewrites assets_v5.json: span card sits on the first beat with
"span_until"; covered beats become {"type": "spanned", "parent": ...}.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"

beats = json.loads((MAN / "beats.json").read_text())["beats"]
bmap = {b["beat_id"]: b for b in beats}
order = [b["beat_id"] for b in beats]
words = json.loads((MAN / "words.json").read_text())["words"]
a5 = json.loads((MAN / "assets_v5.json").read_text())


def find_beat(pattern, start_from=0):
    for i in range(start_from, len(beats)):
        if re.search(pattern, beats[i]["text"], re.I):
            return i
    return None


def word_time(pattern, t0, t1):
    """First word matching pattern spoken inside [t0,t1]."""
    for w in words:
        if t0 <= w["s"] <= t1 and re.search(pattern, w["w"], re.I):
            return w["s"]
    return None


# card_bid -> (start_pattern, end_pattern, item_keyword_patterns)
SPANS = {
 "b_025": (r"six weeks.*seventeen|17 pounds|Six weeks", r"never.*gotten results",
           [r"17|seventeen", r"six|6", r"35|thirty"]),
 "b_035": (r"ran on two rules", r"tell you what.?s next",
           [r"rule|repeat", r"record"]),
 "b_051": (r"Day one", r"trampoline",
           None),
 "b_055": (r"Day two", r"Dan John",
           [r"front", r"pull", r"decline|push", r"power|cleans",
            r"knees"]),
 "b_058": (r"Day three", r"cool.{0,3}down|kettlebells",
           None),
 "b_061": (r"Day four", r"partner",
           None),
 "b_064": (r"Day five", r"fifty.?three|53",
           [r"rope", r"slams|ball", r"bench|dips", r"eleven|11"]),
 "b_073": (r"Two thousand calories|2,?000 calories", r"protein shakes",
           [r"egg", r"vegetables", r"meats", r"fish", r"nuts", r"shakes"]),
 "b_077": (r"No refined sugar", r"night of beers",
           [r"sugar", r"flour|bread", r"juice|booze"]),
 "b_083": (r"same as the gym|write it down", r"feeling full",
           [r"throat|record", r"bible|journal", r"gallon|water"]),
 "b_108": (r"repeat a workout", r"more water than",
           [r"One|repeat", r"Two|Record", r"Three|Thirty|35", r"Four|early",
            r"Five|calories"]),
}

changed = 0
claimed = set()          # beats already used by any span or card
for bid, a in a5.items():
    if a.get("type") == "v5card":
        claimed.add(bid)
for card_bid, (sp, ep, item_pats) in SPANS.items():
    if card_bid not in a5 or a5[card_bid].get("type") != "v5card":
        continue
    ci = order.index(card_bid)
    si = find_beat(sp, max(0, ci - 8))
    ei = find_beat(ep, si if si is not None else 0)
    if si is None or ei is None or ei < si:
        print(f"[skip] {card_bid}: span anchors not found")
        continue
    si = min(si, ci)
    ei = max(ei, ci)
    # never swallow another card or an already-claimed beat
    while si < ci and (order[si] in claimed and order[si] != card_bid):
        si += 1
    for j in range(si, ei + 1):
        if order[j] in claimed and order[j] != card_bid:
            if j <= ci:
                si = j + 1
            else:
                ei = j - 1
                break
    if si > ci or ei < ci or si > ei:
        print(f"[skip] {card_bid}: span collides with other cards")
        continue
    start_bid, end_bid = order[si], order[ei]
    t0, t1 = bmap[start_bid]["start"], bmap[end_bid]["end"]
    card = a5[card_bid]
    # retime item reveals to spoken moments (relative ms from span start)
    props = card["props"]
    key = next((k for k in ("steps", "items", "tiles", "satellites")
                if k in props), None)
    if key and item_pats:
        for item, pat in zip(props[key], item_pats):
            wt = word_time(pat, t0, t1)
            if wt is not None:
                item["atMs"] = max(200, int((wt - t0) * 1000))
    # move card to span start; mark covered beats
    a5[start_bid] = {"type": "v5card", "comp": card["comp"],
                     "props": props, "span_until": end_bid}
    for j in range(si, ei + 1):
        claimed.add(order[j])
        if j != si:
            a5[order[j]] = {"type": "spanned", "parent": start_bid}
    changed += 1
    print(f"{card_bid}: span {start_bid}->{end_bid} "
          f"({t1 - t0:.1f}s), items word-synced")

json.dump(a5, open(MAN / "assets_v5.json", "w"), indent=1)
print(f"[OK] {changed} cards converted to spans")
