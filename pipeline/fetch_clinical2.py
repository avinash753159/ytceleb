#!/usr/bin/env python3
"""Download the second wave of clinical imagery: real, not diagrammatic.

Operator note: the labelled anatomy chart and the microscope slide "show me
nothing". What is wanted is what the disease actually looks like where it
does its damage - endoscopy inside the bowel, resected tissue, and skin.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dossier" / "mrbeast" / "medical"
LEDGER = DEST / "CREDITS2.json"
UA = "ytceleb-research/1.0 (contact info@xleagle.com)"

WANT = {
    # key: (commons title, what it shows, how it will be used)
    "endoscopy_ulcer": (
        "Ulcerated-colonic-mucosa-as-viewed-by-colonoscopy-in-a-patient-with-"
        "ulcerative-colitis-pone.0138750.g001.jpg",
        "Ulcerated mucosa seen from inside the bowel",
        "The 'what it looks like' shot - real, no labels"),
    "crohn_resected": (
        "Macro Iléon terminal, caecum et côlon ascendant - Maladie de Crohn "
        "55-o.apatho-1691p-ilcaco.jpg",
        "Resected terminal ileum with Crohn's damage",
        "Thickened, narrowed bowel - the physical consequence"),
    "ileitis_real": (
        "Ileitis terminalis bei langjaehrigem Morbus Crohn 63w - CT axial - "
        "001.jpg",
        "Long-standing Crohn's ileitis",
        "Secondary clinical view"),
    "small_intestine": (
        "Blausen 0817 SmallIntestine Anatomy.png",
        "Small intestine cross-section",
        "Zoom target - crop to the wall, drop the labels"),
    "badas_crohn": (
        "BADAS Crohn 2.jpg",
        "Clinical Crohn's presentation",
        "Part of the clinical strip"),
    "severe_colitis": (
        "Severe ulcerative colitis.jpg",
        "Severe inflammatory bowel damage (ulcerative colitis)",
        "Only usable if captioned as related IBD, never as Crohn's"),
}


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    titles = "|".join(f"File:{t}" for t, _, _ in WANT.values())
    url = ("https://commons.wikimedia.org/w/api.php?"
           + urllib.parse.urlencode({
               "action": "query", "titles": titles, "prop": "imageinfo",
               "iiprop": "url|extmetadata|size", "format": "json"}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode("utf-8"))

    by_title = {}
    for page in data["query"]["pages"].values():
        if "imageinfo" in page:
            by_title[page["title"].replace("File:", "")] = page["imageinfo"][0]

    import re
    ledger = []
    for key, (title, shows, use) in WANT.items():
        ii = by_title.get(title)
        if not ii:
            print(f"MISS  {key}: '{title[:52]}' not found")
            continue
        meta = ii.get("extmetadata", {})
        lic = re.sub(r"<[^>]+>", "",
                     meta.get("LicenseShortName", {}).get("value", "")).strip()
        author = re.sub(r"<[^>]+>", "",
                        meta.get("Artist", {}).get("value", "")).strip()
        ext = Path(urllib.parse.urlparse(ii["url"]).path).suffix
        out = DEST / f"{key}{ext}"
        if not out.exists():
            rq = urllib.request.Request(ii["url"],
                                        headers={"User-Agent": UA})
            with urllib.request.urlopen(rq, timeout=240) as rr:
                out.write_bytes(rr.read())
        ledger.append({"key": key, "file": out.name, "title": title,
                       "license": lic, "author": author or "unknown",
                       "shows": shows, "use": use,
                       "share_alike": "SA" in lic.upper(),
                       "source_page": "https://commons.wikimedia.org/wiki/"
                                      + urllib.parse.quote(f"File:{title}")})
        flag = "  [SHARE-ALIKE]" if "SA" in lic.upper() else ""
        print(f"OK    {key:18} {ii['width']}x{ii['height']:<5} {lic}{flag}")

    LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"\n{len(ledger)} assets -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
