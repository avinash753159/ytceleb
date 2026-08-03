#!/usr/bin/env python3
"""Download licensed medical illustrations for the Crohn's explainer.

Only CC0 / CC BY are taken. Share-alike (CC BY-SA) is deliberately avoided:
its reciprocal-licensing term is awkward to satisfy for a still embedded in
a commercial video, and clean alternatives exist.

Writes the files plus a machine-readable credit ledger so the on-screen
source cards and the YouTube description can be generated from real data
rather than from memory.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dossier" / "mrbeast" / "medical"
LEDGER = DEST / "CREDITS.json"
UA = "ytceleb-research/1.0 (contact info@xleagle.com)"

WANTED = {
    "mechanism": "Crohn's Disease Mechanism.png",
    "tract": "Blausen 0316 DigestiveSystem.png",
    "villi_histology":
        "Cross-section histology of small intestinal villi of the terminal "
        "ileum.jpg",
    "villi_closeup": "Intestinal villi close up.jpg",
}
ALLOWED = re.compile(r"CC0|Public domain|CC BY 3\.0|CC BY 4\.0", re.I)


def api(params):
    url = ("https://commons.wikimedia.org/w/api.php?"
           + urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def clean(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    titles = "|".join(f"File:{t}" for t in WANTED.values())
    data = api({
        "action": "query", "titles": titles, "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "format": "json",
    })

    by_title = {}
    for page in data["query"]["pages"].values():
        if "imageinfo" not in page:
            print(f"MISSING {page.get('title')}")
            continue
        by_title[page["title"].replace("File:", "")] = page["imageinfo"][0]

    ledger = []
    for key, title in WANTED.items():
        ii = by_title.get(title)
        if not ii:
            print(f"SKIP {key}: not returned by API")
            continue
        meta = ii.get("extmetadata", {})
        lic = clean(meta.get("LicenseShortName", {}).get("value"))
        if not ALLOWED.search(lic or ""):
            print(f"REJECT {key}: license '{lic}' not in allow-list")
            continue

        ext = Path(urllib.parse.urlparse(ii["url"]).path).suffix
        out = DEST / f"{key}{ext}"
        req = urllib.request.Request(ii["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as r:
            out.write_bytes(r.read())

        entry = {
            "key": key,
            "file": out.name,
            "title": title,
            "license": lic,
            "author": clean(meta.get("Artist", {}).get("value")) or "unknown",
            "credit_line": clean(meta.get("Credit", {}).get("value")) or "",
            "source_page":
                "https://commons.wikimedia.org/wiki/"
                + urllib.parse.quote(f"File:{title}"),
            "pixels": f"{ii['width']}x{ii['height']}",
            "on_screen_card": None,   # filled below
        }
        needs_by = "CC BY" in lic.upper() and "CC0" not in lic.upper()
        entry["on_screen_card"] = (
            f"{entry['author']} / Wikimedia Commons / {lic}"
            if needs_by else f"Wikimedia Commons / {lic}")
        ledger.append(entry)
        print(f"OK  {key:16} {out.name:28} {ii['width']}x{ii['height']}  "
              f"{lic}")

    LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"\n{len(ledger)} assets -> {DEST}")
    print(f"credit ledger -> {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
