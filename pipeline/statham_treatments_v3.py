#!/usr/bin/env python3
"""statham_treatments_v3.py - operator-feedback rebuild (ledger F1-F5):
fitness-first footage (real training >= 60%), shot-clamped cuts (never
cross a boundary), DocumentCards showing the ACTUAL published diary at
the exact narration moments, training-only interludes.

Run AFTER shots.json is complete. Then run statham_spans.py, then
v5_assemble + v10_assemble.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "statham"
DIARY = ROOT / "library" / "statham_refs" / "diary"
ACCENT = "#44708E"

beats = json.loads((MAN / "beats.json").read_text())["beats"]
bmap = {b["beat_id"]: b for b in beats}
order = [b["beat_id"] for b in beats]
shots = json.loads((MAN / "statham_shots.json").read_text())
old = json.loads((MAN / "assets_v5.json").read_text())


def durl(p, mime=None):
    p = Path(p)
    if mime is None:
        mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def shot_clamp(src, t_hint, need):
    """Window fully inside the shot containing t_hint. Returns (t0, loop)."""
    ss = shots.get(src, [])
    for s0, s1 in ss:
        if s0 <= t_hint < s1:
            if s1 - s0 >= need + 0.2:
                t0 = min(max(t_hint, s0 + 0.05), s1 - need - 0.1)
                return round(t0, 2), False
            return round(s0 + 0.05, 2), True     # short shot -> loop it
    return round(t_hint, 2), True


A = {}

# watermark kill: crop fractions [left, top, right, bottom] per source
CROPS = {
 "tf_d2V5ZgSDKFE": [0.0, 0.10, 0.12, 0.0],     # BB logo top-right
 "tf_kxTYWZHEOzI": [0.12, 0.10, 0.0, 0.0],     # title text top-left
 "tf_hfTRYwnoPZU": [0.0, 0.06, 0.06, 0.08],    # edge bugs/banners
 "xrxH5n93CzM": [0.10, 0.09, 0.0, 0.0],        # BBC bug top-left
 "AiAnWmlT4Bc": [0.08, 0.0, 0.0, 0.12],        # ET bug lower-left
 "C6YTQsvuiBw": [0.0, 0.08, 0.14, 0.0],        # DVDFilmBonus top-right
}


def cut(bid, src, t_hint):
    b = bmap[bid]
    need = b["end"] - b["start"]
    t0, loop = shot_clamp(src, t_hint, need)
    entry = {"type": "cut", "src": str(DOS / f"{src}.mp4"),
             "t0": t0, "t1": round(t0 + need + 0.2, 2),
             "vid": f"{src}@{t_hint}", "verified": True}
    if src in CROPS:
        entry["crop_box"] = CROPS[src]
    if loop:
        entry["loop"] = True
        entry["t1"] = round(t0 + min(
            need, next((s1 - t0 for s0, s1 in shots.get(src, [])
                        if s0 <= t0 < s1), need)), 2)
    A[bid] = entry


def exloop(bid, name):
    b = bmap[bid]
    A[bid] = {"type": "cut",
              "src": str(ROOT / "library/exloops" / f"{name}.mp4"),
              "t0": 0.0, "t1": round(b["end"] - b["start"] + 0.2, 2),
              "vid": f"exloop:{name}", "verified": True, "loop": True}


# ---- fitness-first pools (verified windows from WATCH_NOTES) -----------
D2, HF, KX = "tf_d2V5ZgSDKFE", "tf_hfTRYwnoPZU", "tf_kxTYWZHEOzI"
POOLS = {
 "open": [("tr_beekeeper", 127), (HF, 38), ("tr_transporter", 26),
          ("tr_lockstock", 88), ("tr_meg", 116)],
 "diver": [("xrxH5n93CzM", 2), ("xrxH5n93CzM", 26), ("xrxH5n93CzM", 56),
           ("xrxH5n93CzM", 68), ("xrxH5n93CzM", 86), ("xrxH5n93CzM", 110),
           ("tr_snatch", 22), ("xrxH5n93CzM", 98), ("xrxH5n93CzM", 122),
           ("tr_lockstock", 90), ("tr_snatch", 70), ("xrxH5n93CzM", 134),
           ("tr_lockstock", 60)],
 "system": [(HF, 2), ("tr_deathrace", 50), (D2, 90), (HF, 44), (D2, 156),
            (KX, 90), (HF, 110), (D2, 167), (HF, 56), (D2, 134),
            (HF, 50), (HF, 14), (D2, 101), (HF, 122),
            (D2, 35), (HF, 140), (D2, 200), (HF, 74), (D2, 123),
            (D2, 178)],
 "week": [(D2, 46), (D2, 57), (D2, 68), (HF, 80), (D2, 101), (KX, 12),
          (D2, 145), (HF, 14), (D2, 35), (KX, 40), (D2, 156), (HF, 110),
          (D2, 134), (KX, 22), (D2, 79)],
 "diet": [(D2, 2), (D2, 112), ("tr_beekeeper", 23),
          (D2, 189), (HF, 62), (KX, 34)],
 "evo": [("tr_meg", 116), (HF, 134), ("tr_wrath", 2),
         ("tr_meg", 134), ("tr_beekeeper", 114), (D2, 222),
         ("AiAnWmlT4Bc", 45), ("tr_beekeeper", 128), (D2, 211),
         ("AiAnWmlT4Bc", 60), ("tr_beekeeper", 135), (HF, 104)],
 "plan": [("exloop:trail_run", 0), (D2, 46), ("exloop:boxing", 0),
          (HF, 74), ("exloop:rowing_erg", 0), (D2, 90),
          ("exloop:pullup", 0), (KX, 90), ("exloop:burpee", 0),
          ("xrxH5n93CzM", 110), (D2, 57), ("xrxH5n93CzM", 14),
          (D2, 123)],
}
SECTIONS = [("open", "b_000", "b_006"), ("diver", "b_007", "b_015"),
            ("system", "b_016", "b_044"), ("week", "b_045", "b_070"),
            ("diet", "b_071", "b_083"), ("evo", "b_084", "b_096"),
            ("plan", "b_097", "b_112")]
idx_in = {s: 0 for s, _, _ in SECTIONS}


def section_of(bid):
    for s, a, z in SECTIONS:
        if a <= bid <= z:
            return s
    return "plan"


for bid in order:
    s = section_of(bid)
    pool = POOLS[s]
    src, t = pool[idx_in[s] % len(pool)]
    bump = 4 * (idx_in[s] // len(pool))
    idx_in[s] += 1
    if src.startswith("exloop:"):
        exloop(bid, src.split(":")[1])
    else:
        cut(bid, src, t + bump)

# ---- carry over V2 cards that stay (from old assets) --------------------
KEEP_CARDS = ["b_005", "b_025", "b_035", "b_051", "b_055", "b_058",
              "b_061", "b_064", "b_066", "b_073", "b_077", "b_083",
              "b_108", "b_111", "b_112"]
for bid in KEEP_CARDS:
    if old.get(bid, {}).get("type") == "v5card":
        A[bid] = old[bid]
    else:  # span leftovers from V2 spans run - recover card from parent
        for k, v in old.items():
            if v.get("type") == "v5card" and v.get("span_until") and \
                    k <= bid <= v["span_until"]:
                A[k] = {kk: vv for kk, vv in v.items() if kk != "span_until"}

# ---- DocumentCards: the ACTUAL published diary --------------------------
A["b_020"] = {"type": "v5card", "comp": "DocumentCard", "props": {
    "src": durl(DIARY / "mh_cover_oct2007.jpg"),
    "outlet": "Men's Health", "date": "October 2007",
    "note": "the actual cover — 'Watch His Workout'",
    "accent": ACCENT, "panFrom": 0.0, "panTo": 0.35}}
A["b_046"] = {"type": "v5card", "comp": "DocumentCard", "props": {
    "src": durl(DIARY / "wayback_p1.png"),
    "outlet": "menshealth.com", "date": "Sept 6, 2007",
    "author": "Mike Zimmerman",
    "note": "the original article, archived",
    "accent": ACCENT, "panFrom": 0.05, "panTo": 0.5}}
A["b_052"] = {"type": "v5card", "comp": "DocumentCard", "props": {
    "src": durl(DIARY / "diary_pdf_p2.png"),
    "outlet": "Men's Health", "date": "2007",
    "note": "his published deadlift log — 135 to 365",
    "accent": ACCENT, "panFrom": 0.05, "panTo": 0.3}}
A["b_059"] = {"type": "v5card", "comp": "DocumentCard", "props": {
    "src": durl(DIARY / "diary_pdf_p4.png"),
    "outlet": "Men's Health", "date": "2007",
    "note": "his logged 500m sprint times",
    "accent": ACCENT, "panFrom": 0.05, "panTo": 0.4}}

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

# ---- interludes: training-relevant only + 2 new training clips ---------
inters = json.loads((MAN / "interludes.json").read_text())
keep = [i for i in inters if i["id"] not in ("int_fallon", "int_jre")]
have = {i["id"] for i in keep}
keep = [i for i in keep if i["id"] not in ("int_choreo", "int_pushup")]
if "int_wgn" not in have:
    keep.append({"id": "int_wgn", "after": "b_089",
                 "vid": "n4oQnRG40c0", "t0": 55.0, "t1": 78.0,
                 "label": "Jason Statham — on his training, WGN"})
sec_order = {b: i for i, b in enumerate(order)}
keep.sort(key=lambda i: sec_order.get(i["after"], 999))
json.dump(keep, open(MAN / "interludes.json", "w"), indent=1)

cards = sum(1 for a in A.values() if a["type"] == "v5card")
train = sum(1 for a in A.values() if a["type"] == "cut" and
            ("tf_" in a["vid"] or "exloop" in a["vid"] or
             "xrxH5n" in a["vid"]))
foot = sum(1 for a in A.values() if a["type"] == "cut")
print(f"[OK] {len(A)} beats: {cards} cards, {foot} cuts "
      f"({train}/{foot} = {100*train//max(foot,1)}% training/dive), "
      f"{len(keep)} interludes")
