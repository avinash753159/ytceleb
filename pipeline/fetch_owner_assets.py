#!/usr/bin/env python3
"""Fetch the specific assets the owner linked in the review deck.

These are copyrighted press and commercial images, used on his instruction
under a commentary/fair-use rationale, and each one is credited on screen to
its outlet and again in the description. That is a deliberate change from the
film's previous position (Pexels + Wikimedia CC + his own posts only), so the
outlet name travels with the file from the moment it lands.

A browser User-Agent is mandatory on every one of these hosts.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dossier/mrbeast/owner_links"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# key -> (kind, url, on-screen credit, why the owner asked for it)
WANT = {
    "nypost_transformation": (
        "image",
        "https://nypost.com/wp-content/uploads/sites/2/2023/06/"
        "NYPICHPDPICT000013429726.jpg?resize=1472,2048&quality=75&strip=all",
        "NEW YORK POST",
        "slide 1 - open on this instead of a talking head"),
    "drvaidji_crohns": (
        "image",
        "https://drvaidji.com/cdn/shop/articles/crohns-disease.jpg"
        "?v=1712557435",
        "DRVAIDJI.COM",
        "slide 37 - a real illustration of the disease, not a website"),
    "tenor_100m": (
        "page",
        "https://tenor.com/view/mrbeast100mil-100million-subscribers-"
        "mrbeast100million-100million-mrbeast-mr-beast-gif-26329206",
        "TENOR",
        "slide 2 - 100 million subscribers, instead of the card"),
    "drvaidji_article": (
        "page",
        "https://drvaidji.com/blogs/knowledge-base/what-is-crohns-disease",
        "DRVAIDJI.COM",
        "slide 18 - what Crohn's is, as imagery"),
    "menshealth_beforeafter": (
        "page",
        "https://www.menshealth.com/uk/weight-loss/a44397610/"
        "mr-beast-weight-loss-transformation-before-after/",
        "MEN'S HEALTH UK",
        "slide 20 - animate 190 to 139 over this"),
}

IMG_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
    re.I)
VID_RE = re.compile(
    r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)',
    re.I)


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,image/avif,image/webp,image/*,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = []
    for key, (kind, url, credit, why) in WANT.items():
        try:
            if kind == "image":
                data = get(url)
                ext = ".jpg"
                out = DEST / f"{key}{ext}"
                out.write_bytes(data)
            else:
                html = get(url).decode("utf-8", "ignore")
                m = VID_RE.search(html) or IMG_RE.search(html)
                if not m:
                    print(f"[warn] {key}: no og:image/og:video on the page")
                    continue
                media = m.group(1).replace("&amp;", "&")
                data = get(media)
                ext = ".mp4" if ".mp4" in media else (
                    ".gif" if ".gif" in media else ".jpg")
                out = DEST / f"{key}{ext}"
                out.write_bytes(data)
                url = media
            kb = out.stat().st_size / 1024
            print(f"[ok] {key:26} {kb:8.0f} KB  {out.name}")
            manifest.append({"key": key, "file": str(
                out.relative_to(ROOT)).replace("\\", "/"),
                "source_url": url, "on_screen_credit": credit,
                "why": why,
                "licence": "third-party, used on the owner's instruction as "
                           "commentary; credited on screen and in the "
                           "description"})
        except Exception as e:                                  # noqa: BLE001
            print(f"[FAIL] {key}: {type(e).__name__} {e}")

    (DEST / "CREDITS.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n[OK] {len(manifest)} assets -> {DEST}")
    for m in manifest:
        print(f"   {m['on_screen_credit']:16} {m['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
