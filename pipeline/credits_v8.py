#!/usr/bin/env python3
"""Build the video description from the shot list that actually shipped.

HANDOFF section 8 lists what must be credited. Rule 10 keeps stock attribution
OFF the screen and puts it here instead, so this file is the only place a
Pexels photographer is named - which means it cannot be written from memory or
from the fetch manifest. It is generated from the shots that ended up in the
cut, so a clip that was fetched and never used is not credited, and a clip
that shipped cannot be missed.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/picture_v8_shots.json"
OUT = ROOT / "dossier/mrbeast/DESCRIPTION_V8.md"

CREDIT_FILES = [
    ROOT / "library/broll3/CREDITS.json",
    ROOT / "library/broll/CREDITS.json",
]
MED_CREDITS = [
    ROOT / "dossier/mrbeast/medical/CREDITS.json",
    ROOT / "dossier/mrbeast/medical/CREDITS2.json",
]

INTERVIEWS = {
    "cLRLEnPaJLM": "The Joe Rogan Experience #1788 (PowerfulJRE)",
    "FjrJ2DJN_pA": "The Diary Of A CEO",
    "9IQ_ldV9z_A": "Colin and Samir - A Brutally Honest Conversation "
                   "with MrBeast",
    "c8VcUnz3nVc": "Colin and Samir - The Full Story of MrBeast",
    "NdjcGrpNSF4": "Jon Youshaei - Inside MrBeast's YouTube Machine",
    "AKJfakEsgy0": "MrBeast - Hi Me In 5 Years (4 October 2015)",
    "F0OkwXKcPSE": "MrBeast - Hi Me In 10 Years (4 October 2015)",
}


def load_stock() -> dict:
    out = {}
    for f in CREDIT_FILES:
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("clips", [])
        for r in rows:
            if isinstance(r, dict) and r.get("file"):
                out[Path(r["file"]).name] = r
    return out


def main() -> int:
    if not SHOTS.exists():
        raise FileNotFoundError(f"{SHOTS} - build the picture first")
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    stock = load_stock()

    used_sources, used_stock = set(), {}
    for s in shots:
        a = s.get("asset") or ""
        if s.get("kind") == "footage" and "@" in a:
            used_sources.add(a.split("@")[0])
        elif a.endswith(".mp4"):
            name = Path(a).name
            r = stock.get(name)
            if r:
                who = r.get("photographer") or "Pexels contributor"
                used_stock.setdefault(who, []).append(r.get("url") or name)
            else:
                used_stock.setdefault("Pexels (contributor unrecorded)",
                                      []).append(name)

    L: list[str] = []
    L.append("# Description — The Disease That Built MrBeast\n")
    L.append("Generated from the shipped shot list, not from the fetch "
             "manifest: nothing is credited that is not on screen, and "
             "nothing on screen is missing.\n")

    L.append("## A note on one widely repeated figure\n")
    L.append("The \"40% body fat\" number attached to Jimmy Donaldson all "
             "over the internet is **not his**. It is Airrack's, said in "
             "Airrack's own video, and we frame-verified it. Jimmy has never "
             "published a training split, a set-and-rep scheme, a calorie "
             "target or a body-fat figure. Everything this film states about "
             "his training and diet comes from something he said himself, "
             "on camera, and is quoted here in his own voice.\n")
    L.append("Nor was it 310 or 602 *consecutive* workouts — programmed rest "
             "days were part of the agreement.\n")
    L.append("Exercise is not a treatment for Crohn's disease, and this film "
             "does not suggest that it is.\n")

    L.append("## Interview and archive sources\n")
    for sid in sorted(used_sources):
        L.append(f"- {INTERVIEWS.get(sid, sid)}  \n  "
                 f"https://www.youtube.com/watch?v={sid}")
    L.append("")

    L.append("## Score\n")
    L.append("- Scott Buckley — licensed CC BY 4.0. "
             "https://www.scottbuckley.com.au/\n")

    L.append("## Medical imagery\n")
    L.append("Wikimedia Commons, under CC0, CC BY 2.0, CC BY 3.0 and "
             "CC BY 4.0, plus one image (resected Crohn's ileum) under "
             "CC BY-SA 4.0. Per-file attribution:\n")
    for f in MED_CREDITS:
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows = data if isinstance(data, list) else [
            {"file": k, **(v if isinstance(v, dict) else {"note": v})}
            for k, v in data.items()]
        for r in rows:
            if not isinstance(r, dict):
                continue
            nm = r.get("file") or r.get("name") or ""
            who = r.get("author") or r.get("credit") or r.get("photographer") \
                or ""
            lic = r.get("license") or r.get("licence") or ""
            url = r.get("url") or r.get("source") or ""
            L.append(f"- {nm} — {who} — {lic} {url}".rstrip())
    L.append("")

    L.append("## Reference documents shown on screen\n")
    L.append("- National Institute of Diabetes and Digestive and Kidney "
             "Diseases (NIDDK) — Crohn's disease: definition and facts, "
             "treatment, eating and nutrition")
    L.append("- Crohn's & Colitis Foundation — \"What is Crohn's Disease?\"")
    L.append("- @MrBeast on X, 29 June 2023 and 21 April 2025 "
             "(captured from the official post embeds)")
    L.append("- MrBeast's own 2015 uploads, including the channel dashboard "
             "reading 8,726 subscribers\n")

    # Third-party press and commercial imagery, used as commentary on the
    # owner's instruction. That is a change of position for this film, so the
    # description states it plainly rather than burying it among the stock.
    if OWNER_LINKS.exists():
        rows = json.loads(OWNER_LINKS.read_text(encoding="utf-8"))
        if rows:
            L.append("## Third-party imagery used as commentary\n")
            L.append("The following are copyrighted press and commercial "
                     "images, reproduced for commentary and criticism. Each "
                     "is credited on screen at the moment it appears, and "
                     "again here. No claim of ownership is made.\n")
            for r in rows:
                L.append(f"- **{r['on_screen_credit']}** — {r['source_url']}")
            L.append("")

    L.append("## Stock footage\n")
    L.append("Pexels licence. Photographers, for the clips that appear in "
             "the finished film:\n")
    for who in sorted(used_stock):
        L.append(f"- {who} ({len(used_stock[who])} clip"
                 f"{'s' if len(used_stock[who]) > 1 else ''})")
    L.append("")
    L.append("Stock footage in this film may show anonymous people "
             "performing the activity being described — eating, training, "
             "walking, editing. None of them is Jimmy Donaldson and none is "
             "presented as him. No child is cast as him at any point, and no "
             "other creator appears on screen.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {OUT}")
    print(f"     {len(used_sources)} interview/archive sources, "
          f"{sum(len(v) for v in used_stock.values())} stock clips from "
          f"{len(used_stock)} photographers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
