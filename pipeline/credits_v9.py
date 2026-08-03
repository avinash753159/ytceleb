#!/usr/bin/env python3
"""The description and credit list for V9, covering the footage ACTUALLY used.

DESCRIPTION_V8.md is stale for this cut: credits_v8.py reads
picture_v8_shots.json and only ever walks library/broll3 and library/broll,
so none of the broll7 clips - the entire stock layer of V9 - appear in it.
Shipping that description would credit the wrong footage.

HANDOFF section 8 is the requirement: the description must credit the score,
the Wikimedia medical stills, the Pexels stock photographers, and the
interview sources. Pexels' licence is generous but attribution is the thing
it asks for in return, and the medical stills are CC BY / CC BY-SA, where
attribution is a condition of use, not a courtesy.

This walks the PLAN rather than a directory, so a clip that was downloaded
but never drawn is not credited, and a clip that was drawn cannot be missed.
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

OUT = ROOT / "DESCRIPTION_V9.md"
ALLOW = ROOT / "manifest/broll_allow.json"
MEDICAL = ROOT / "dossier/mrbeast/medical"

SOURCES = [
    ("Joe Rogan Experience #1788", "PowerfulJRE"),
    ("The Diary Of A CEO", "YouTube"),
    ("Colin and Samir — The Full Story of MrBeast", "YouTube"),
    ("Colin and Samir (June 2023)", "YouTube"),
    ("Inside MrBeast's YouTube Machine", "Jon Youshaei"),
    ("Hi Me In 5 Years / Hi Me In 10 Years, 4 October 2015", "MrBeast"),
]


def used_stock() -> list[dict]:
    """Every broll clip the plan can actually draw, with its Pexels record."""
    import picture_plan_v9 as P
    allow = json.loads(ALLOW.read_text(encoding="utf-8"))
    groups = set()
    for slots, _ in P.PLAN.values():
        for s in slots:
            spec = s[2] if s[0] == "fix" else s[1]
            if spec[0] == "broll":
                groups.add(spec[1])
                groups.update(P.FALLBACK.get(spec[1], []))

    cred = {}
    cpath = ROOT / "library/broll7/CREDITS.json"
    if cpath.exists():
        for r in json.loads(cpath.read_text(encoding="utf-8")):
            cred[Path(r["file"]).name] = r

    out = []
    for g in sorted(groups):
        for it in allow.get(g, []):
            name = Path(it["file"]).name
            r = cred.get(name)
            out.append({
                "file": it["file"],
                "group": g,
                "photographer": (r or {}).get("photographer"),
                "url": (r or {}).get("url"),
            })
    return out


def medical_credits() -> list[dict]:
    rows = []
    for f in ("CREDITS.json", "CREDITS2.json"):
        p = MEDICAL / f
        if p.exists():
            rows += json.loads(p.read_text(encoding="utf-8"))
    return rows


def main() -> int:
    stock = used_stock()
    people = OrderedDict()
    for s in stock:
        who = s["photographer"]
        if who:
            people.setdefault(who, 0)
            people[who] += 1

    L = []
    L.append("# The Disease That Built MrBeast — description and credits (V9)")
    L.append("")
    L.append("## Credits")
    L.append("")
    L.append("**Interview and archive footage**")
    for title, who in SOURCES:
        L.append(f"- {title} — {who}")
    L.append("")
    L.append("**Music**")
    L.append("- Scott Buckley, CC BY 4.0")
    L.append("")
    L.append("**Medical stills — Wikimedia Commons**")
    for r in medical_credits():
        lic = r.get("license", "")
        author = (r.get("author") or "").split(".")[0][:70]
        L.append(f"- {r.get('title')} — {author} — {lic}")
    L.append("")
    L.append(f"**Stock footage — Pexels** ({len(stock)} clips, "
             f"{len(people)} photographers)")
    for who, n in sorted(people.items(), key=lambda kv: (-kv[1], kv[0])):
        L.append(f"- {who} ({n} clip{'s' if n > 1 else ''})")
    unknown = sum(1 for s in stock if not s["photographer"])
    if unknown:
        L.append(f"- {unknown} clip(s) from earlier library rounds "
                 f"(broll3-6); see library/broll*/CREDITS.json")
    L.append("")
    L.append("## Per-clip stock manifest")
    L.append("")
    L.append("| segment | file | photographer | source |")
    L.append("|---|---|---|---|")
    for s in stock:
        L.append(f"| {s['group']} | {Path(s['file']).name} | "
                 f"{s['photographer'] or '-'} | {s['url'] or '-'} |")
    L.append("")
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {OUT}")
    print(f"     {len(stock)} stock clips, {len(people)} named photographers, "
          f"{unknown} from earlier rounds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
