#!/usr/bin/env python3
"""V9 storyboard - a frame every 10 seconds across the whole 12:26.

Source palette is now restricted to footage where Jimmy is verifiably the
person on screen, plus licensed stills, plus anonymous gym stock:

  Joe Rogan #1788        Jimmy alone at the desk
  Diary of a CEO         Jimmy alone
  Colin and Samir        Jimmy singles only
  MrBeast own archive    Jimmy alone in his bedroom
  Licensed medical       diagrams, tissue, clinical photographs
  Gym stock library      anonymous, never implied to be him
  Designed cards         numbers and the system infographic

DROPPED: Airrack (checked 12 windows - every one is a two-shot with Airrack,
or neither of them), Chris Hemsworth (his gym, his crew), the Minecraft
upload (no Jimmy on screen), and the Blausen labelled chart.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"
MED = ROOT / "dossier/mrbeast/medical"
LIB = ROOT / "library/exloops"
WORK = ROOT / "work/storyboard3"
OUT = WORK / "storyboard.html"

TW, TH = 320, 180
STEP = 10
TOTAL = 746

ROGAN = SRC / "cLRLEnPaJLM.mp4"
DOACEO = SRC / "FjrJ2DJN_pA.mp4"
COLIN = SRC / "9IQ_ldV9z_A.mp4"
TEEN = ARC / "AKJfakEsgy0.mp4"
TEEN10 = ARC / "F0OkwXKcPSE.mp4"

# (start, end, key, on-screen, source label, kind)
PLAN = [
    (0, 14, "ba_open", "TRANSFORMATION — his own June 2023 photo beside "
     "today, both dated", "@MrBeast 29 Jun 2023 + present-day", "hero"),
    (14, 24, "rogan_energy", "“One of the least energetic people you'll "
     "ever meet”", "Joe Rogan #1788", "sync"),
    (24, 34, "teen_1", "The kid alone in his bedroom, camera running",
     "MrBeast — Hi Me In 5 Years", "footage"),
    (34, 46, "present_hold", "Present-day Jimmy, held — music-only title "
     "break", "Colin and Samir", "hero"),

    (46, 62, "teen_2", "Same room, different day — the body before",
     "MrBeast — Hi Me In 5 Years", "footage"),
    (62, 78, "rogan_baseball", "Baseball, then Crohn's at fifteen",
     "Joe Rogan #1788", "sync"),
    (78, 96, "doaceo_collapse", "Uninterrupted: 190 pounds down to 139",
     "Diary of a CEO", "sync"),
    (96, 110, "card_weight", "190 → 139 — the number falls as he says it",
     "Designed card", "card"),

    (110, 126, "doaceo_symptoms", "Eight to ten bathroom trips a day",
     "Diary of a CEO", "sync"),
    (126, 142, "ibd_real", "Real inflamed bowel tissue — no labels, no "
     "diagram", "Wikimedia / CC0", "clinical"),
    (142, 162, "real_tissue", "Resected Crohn's ileum — thickened, scarred",
     "Wikimedia / CC BY-SA 4.0", "clinical"),
    (162, 182, "mechanism", "Healthy lining beside Crohn's-damaged lining",
     "Wikimedia / CC0", "clinical"),
    (182, 198, "clinical_strip", "Four brief clinical shots, ~0.6s each",
     "Wikimedia / CC BY, CC0", "clinical"),
    (198, 218, "rogan_dead", "“I'm dead. I just lay in bed all day.”",
     "Joe Rogan #1788", "sync"),
    (218, 236, "rogan_remicade", "Naming the treatment — IV every eight "
     "weeks, for life", "Joe Rogan #1788", "sync"),
    (236, 255, "card_infusion", "Infusion calendar running years forward",
     "Designed card", "card"),

    (255, 276, "the_post", "THE POST, as a document — his handle, the date, "
     "and “I was obese” in his own words", "@MrBeast, 29 June 2023",
     "hero"),
    (276, 296, "rogan_obsession", "“Obsessed over YouTube every day for a "
     "decade”", "Joe Rogan #1788", "sync"),
    (296, 314, "card_machine", "INFOGRAPHIC — uploads, hours, scale of the "
     "system he built", "Designed graphic", "card"),
    (314, 326, "teen_3", "Alone, still uploading to nobody",
     "MrBeast own archive", "footage"),

    (326, 348, "colin_1", "“I have not been working out or taking care of "
     "myself”", "Colin and Samir", "sync"),
    (348, 368, "gym_a", "A man training — steady, unremarkable, repeated",
     "Pexels — Pressmaster", "footage"),
    (368, 390, "card_310", "DAY 310 counting up over the routine",
     "Stock + counter", "card"),
    (390, 408, "gym_b", "Dumbbell work — the ordinary part nobody films",
     "Pexels — Michelangelo Buonarroti", "footage"),
    (408, 423, "colin_2", "The pact, and what programmed rest actually "
     "meant", "Colin and Samir", "sync"),

    (423, 446, "walk_steps", "Walking — 12,500 STEPS ring filling over it",
     "Pexels — Mary Taylor + counter", "card"),
    (446, 468, "gym_c", "Barbell work — the verified part of the protocol",
     "Pexels — Ojyrai Films", "footage"),
    (468, 490, "colin_3", "“It's costing me uploads and I do it anyway”",
     "Colin and Samir", "sync"),
    (490, 512, "card_record", "THE 40% FIGURE IS NOT HIS — frame check "
     "proves Airrack said it, not Jimmy", "Designed card", "card"),
    (512, 530, "gym_d", "Ordinary repetitions, no glamour",
     "Pexels — Pressmaster", "footage"),

    (530, 552, "rogan_limit", "The method failing — effort without the "
     "result", "Joe Rogan #1788", "sync"),
    (552, 566, "doaceo_treatment", "The treatment burden — immune system "
     "suppressed", "Diary of a CEO", "sync"),
    (566, 574, "tired", "Exhaustion — what the illness costs him daily",
     "Pexels — RDNE Stock project", "footage"),
    (574, 595, "gym_e", "An empty gym, lights going off in rows",
     "Pexels — Ds babariya", "footage"),

    (595, 617, "doaceo_give", "Beast Games, the workload — training was "
     "what broke", "Diary of a CEO", "sync"),
    (617, 638, "doaceo_sleep", "“I've got to fix sleep first”",
     "Diary of a CEO", "sync"),
    (638, 660, "gym_f", "A dark bedroom. Nothing moving. “Fix sleep first.”",
     "Pexels — Film geek", "footage"),

    (660, 686, "ba_payoff", "THE TRANSFORMATION, FULL — held long, both "
     "dated", "Archive + present-day", "hero"),
    (686, 706, "rogan_life", "“It's just life.”", "Joe Rogan #1788", "sync"),
    (706, 728, "present_end", "Present-day Jimmy, held — who he is now",
     "Diary of a CEO", "sync"),
    (728, TOTAL, "card_end", "End frame — no logo over footage",
     "Designed card", "card"),
]

GRABS = {
    "rogan_energy": (ROGAN, 5266.4), "rogan_baseball": (ROGAN, 5240),
    "rogan_dead": (ROGAN, 5356.5), "rogan_remicade": (ROGAN, 5366),
    "rogan_obsession": (ROGAN, 176), "rogan_limit": (ROGAN, 5430),
    "rogan_life": (ROGAN, 5418),
    "doaceo_collapse": (DOACEO, 832), "doaceo_symptoms": (DOACEO, 925),
    "doaceo_treatment": (DOACEO, 975), "doaceo_give": (DOACEO, 2782),
    "doaceo_sleep": (DOACEO, 2796), "present_end": (DOACEO, 975),
    # colin_3 at 770 landed on the two hosts, and present_end at 120 was a
    # black intro frame. Both verified against a contact sheet.
    "present_hold": (COLIN, 712), "colin_1": (COLIN, 758),
    "colin_2": (COLIN, 735), "colin_3": (COLIN, 726),
    "teen_1": (TEEN, 25), "teen_2": (TEEN, 48), "teen_3": (TEEN, 78),
    "teen10": (TEEN10, 42),
}
GYM = ["gym_a", "gym_b", "gym_c", "gym_d", "gym_e", "gym_f"]


def run(a):
    subprocess.run(a, check=True, timeout=600, capture_output=True)


def grab(v, t, dest, w=TW):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss",
         f"{t:.2f}", "-i", str(v), "-frames:v", "1", "-vf",
         f"scale={w}:-2", "-q:v", "6", str(dest)])
    return dest


def crop_zoom(img, dest, box, w=TW, h=TH):
    l, t, r, b = box
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
         str(img), "-vf",
         f"crop=iw*{1-l-r:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},"
         f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
         "-q:v", "6", str(dest)])
    return dest


def pair(a, b, dest, w=TW, h=TH):
    half = w // 2
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(a),
         "-i", str(b), "-filter_complex",
         f"[0:v]scale={half}:{h}:force_original_aspect_ratio=increase,"
         f"crop={half}:{h}[l];[1:v]scale={half}:{h}:"
         f"force_original_aspect_ratio=increase,crop={half}:{h}[r];"
         f"[l][r]hstack=inputs=2", "-frames:v", "1", "-q:v", "6", str(dest)])
    return dest


def strip(imgs, dest, w=TW, h=TH):
    n = len(imgs)
    cell = w // n
    ins = []
    for p in imgs:
        ins += ["-i", str(p)]
    sc = ";".join(f"[{i}:v]scale={cell}:{h}:"
                  f"force_original_aspect_ratio=increase,crop={cell}:{h}[c{i}]"
                  for i in range(n))
    lab = "".join(f"[c{i}]" for i in range(n))
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
         "-filter_complex", f"{sc};{lab}hstack=inputs={n}", "-frames:v", "1",
         "-q:v", "6", str(dest)])
    return dest


def b64(p):
    return "data:image/jpeg;base64," + base64.b64encode(
        p.read_bytes()).decode("ascii")


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    tmp = WORK / "_t"
    tmp.mkdir(exist_ok=True)
    imgs = {}

    for k, (v, t) in GRABS.items():
        if not v.exists():
            continue
        p = WORK / f"{k}.jpg"
        if not p.exists():
            grab(v, t, p)
        imgs[k] = b64(p)

    # The 'before' is now HIS OWN photo from the June 2023 post, not a 2013
    # bedroom grab. Dated, first-person, and the origin of the 12,500 figure.
    POST = ROOT / ("dossier/mrbeast/primary/"
                   "mrbeast_transformation_2023-06-29.jpg")
    before = POST if POST.exists() else grab(TEEN, 25, tmp / "b.jpg", 700)
    a1 = grab(COLIN, 712, tmp / "a1.jpg", 700)
    a2 = grab(DOACEO, 120, tmp / "a2.jpg", 700)
    for k, aft in (("ba_open", a1), ("ba_payoff", a2)):
        p = WORK / f"{k}.jpg"
        if not p.exists():
            pair(before, aft, p)
        imgs[k] = b64(p)
    if POST.exists():
        p = WORK / "the_post.jpg"
        if not p.exists():
            crop_zoom(POST, p, (0.0, 0.02, 0.0, 0.02))
        imgs["the_post"] = b64(p)

    med = {
        "ibd_real": (MED / "severe_colitis.jpg", (0.18, 0.18, 0.18, 0.18)),
        "real_tissue": (MED / "crohn_resected.jpg", (0.05, 0.10, 0.05, 0.10)),
        "mechanism": (MED / "mechanism.png", (0.02, 0.02, 0.02, 0.50)),
    }
    for k, (src, box) in med.items():
        if not src.exists():
            continue
        p = WORK / f"{k}.jpg"
        if not p.exists():
            crop_zoom(src, p, box)
        imgs[k] = b64(p)

    clin = [MED / n for n in ("skin_leg.jpg", "skin_leg2.jpg",
                              "badas_crohn.jpg", "severe_colitis.jpg")]
    clin = [c for c in clin if c.exists()]
    if clin:
        p = WORK / "clinical_strip.jpg"
        if not p.exists():
            strip(clin, p)
        imgs["clinical_strip"] = b64(p)

    # Purpose-fetched b-roll. The old loop library was all explosive
    # CrossFit movement - no empty gym, no walking, no dark room - so those
    # beats were illustrated with jiu-jitsu under invented captions.
    BROLL = ROOT / "library/broll"
    for key, clip, t in (
            ("gym_a", "gym_lifting", 3.0),
            ("gym_b", "gym_dumbbell", 4.0),
            ("gym_c", "gym_barbell", 2.5),
            ("gym_d", "gym_lifting", 8.0),
            ("gym_e", "gym_empty", 5.0),
            ("gym_f", "bedroom_dark", 4.0),
            ("walk_steps", "walking_street", 3.0),
            ("tired", "man_tired", 4.0)):
        src = BROLL / f"{clip}.mp4"
        if src.exists():
            p = WORK / f"{key}.jpg"
            if not p.exists():
                grab(src, t, p)
            imgs[key] = b64(p)

    # Designed graphics, rendered for real from the Remotion comps.
    cards = ROOT / "work/cards"
    for k in ("card_weight", "card_310", "card_steps", "card_time",
              "card_rest", "card_record"):
        png = cards / f"{k}.png"
        if png.exists():
            p = WORK / f"{k}.jpg"
            if not p.exists():
                crop_zoom(png, p, (0, 0, 0, 0))
            imgs[k] = b64(p)
    return imgs


def ticks():
    """One entry per STEP seconds, resolved against the plan."""
    out = []
    for t in range(0, TOTAL, STEP):
        shot = next((s for s in PLAN if s[0] <= t < s[1]), PLAN[-1])
        out.append((t, shot))
    return out


def main() -> int:
    imgs = build()
    from storyboard3_html import render
    OUT.write_text(render(ticks(), PLAN, imgs), encoding="utf-8")
    print(f"[OK] {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"[frames] {TOTAL//STEP} ticks, {len(imgs)} distinct images")
    print(f"[no art] {sorted({s[2] for s in PLAN} - set(imgs))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

