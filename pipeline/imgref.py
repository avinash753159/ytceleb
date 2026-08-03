#!/usr/bin/env python3
"""Reference images for the shot list - a real image search, photos only.

WHY A HEADLESS BROWSER AND NOT AN HTTP CALL
-------------------------------------------
All the keyless HTTP endpoints are bot-locked, and each one fails in a way
that looks like success if you do not look at the pictures:

  bing.com/images/async   ignores the query completely and answers with
                          Japanese shopping listings, HTTP 200
  duckduckgo.com/i.js     HTTP 403 regardless of vqd, cookies or headers
  api.openverse.org       no medical corpus - 0 results for a Crohn's query
  bing.com/images/search  over plain urllib, answers a generic page: a query
                          for Crohn's endoscopy returned autumn quote cards

Headless Chrome against Bing returns the real result set. Verified by eye on
a contact sheet, not assumed - assuming is what put shipping crates under a
sentence about YouTube.

THE ONE THING THAT WILL BREAK THIS AGAIN
----------------------------------------
REUSE THE BROWSER, NEVER THE PAGE. Driving several queries through one page
makes Bing degrade after the first: query 1 came back correct, query 2 came
back as an unrelated stock portrait, query 3 as YouTube logo clip art and
query 4 - "heavy industrial machinery gears factory dark" - as Chainsaw Man
fan art. Every one HTTP 200 with a correct-looking landing URL. A fresh
browser context per query returns all four correctly. That is why
search_many() opens and closes a context inside the loop, which looks
wasteful and is not.

Bing's own filter tokens do most of the quality work:
  filterui:photo-photo        drop clip art and line drawings
  filterui:aspect-wide        drop portrait crops and square charts
  filterui:imagesize-medium   drop icons and favicons
They do NOT drop lecture slides, which dominate medical queries, so titles
are screened for those separately.
"""

from __future__ import annotations

import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEDICAL = ROOT / "dossier/mrbeast/medical"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FILTERS = "+filterui:photo-photo+filterui:aspect-wide+filterui:imagesize-medium"

# A slide deck of a bowel wall is not a reference for how to shoot a bowel
# wall. These dominate medical image search and have to go by title.
SLIDE = re.compile(
    r"\b(ppt|pptx|slideshare|slideserve|powerpoint|presentation|lecture|"
    r"quiz|flashcard|worksheet|infographic|clipart|vector|template)\b", re.I)

# Reference thumbnails with a stock agency's watermark burned across them are
# ugly in the document and unusable as a look reference. The picture is on a
# dozen other hosts without the lattice; take one of those instead.
WATERMARKED = re.compile(
    r"(shutterstock|alamy|dreamstime|123rf|depositphotos|istockphoto|"
    r"gettyimages|canstockphoto|vectorstock|stockphoto|agefotostock|"
    r"lookphotos|imago-images|pixta|pngtree|pikbest|freepik|adobe ?stock|"
    r"stock\.adobe|lovepik|rawpixel|vecteezy|storyblocks|dissolve\.com)", re.I)

# For "med" segments we want the specimen or the endoscopic photograph - the
# real thing, which is the whole point of those blocks. Labelled teaching
# diagrams and healthy-versus-diseased comparison plates crowd those queries
# out and are not a reference for how to shoot anything.
#
# "medart" segments are the opposite: the prompt IS an anatomical render, so a
# clean illustration is exactly the right reference and only the slide filter
# applies.
DIAGRAM = re.compile(
    r"\b(diagram|chart|comparison|versus|vs|difference|labell?ed|poster|"
    r"schematic|cartoon|drawing|graphic)\b", re.I)


def _url(q: str) -> str:
    return ("https://www.bing.com/images/search?"
            + urllib.parse.urlencode({"q": q, "qft": FILTERS,
                                      "form": "IRFLTR", "mkt": "en-US"}))


def _reject(title: str, url: str, page: str, kind: str | None) -> bool:
    if SLIDE.search(title):
        return True
    # Title as well as host: the agencies' pictures get republished on blogs
    # and news sites with the lattice still burned in, where the host name no
    # longer gives them away but the caption usually does.
    if (WATERMARKED.search(url) or WATERMARKED.search(page or "")
            or WATERMARKED.search(title)):
        return True
    if kind == "med" and DIAGRAM.search(title):
        return True
    return False


def search_many(queries: dict, per: int = 14) -> dict:
    """queries: {key: (search string, kind)} -> {key: [record, ...]}.

    kind is None, "med" (real specimen / endoscopic photograph wanted) or
    "medart" (anatomical illustration wanted).

    One browser process for the whole run, one fresh context per query. See
    the module docstring for why the context cannot be shared.
    """
    from playwright.sync_api import sync_playwright

    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        for key, (q, kind) in queries.items():
            ctx = None
            try:
                ctx = browser.new_context(
                    user_agent=UA, viewport={"width": 1500, "height": 1200},
                    locale="en-US")
                page = ctx.new_page()
                page.goto(_url(q), wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(1200)
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(1200)
                metas = page.eval_on_selector_all(
                    "a.iusc", "els => els.map(e => e.getAttribute('m'))")
                recs, seen = [], set()
                for m in metas:
                    if not m:
                        continue
                    try:
                        d = json.loads(m)
                    except Exception:                            # noqa: BLE001
                        continue
                    u, title = d.get("murl"), (d.get("t") or "").strip()
                    if not u or u in seen:
                        continue
                    if _reject(title, u, d.get("purl") or "", kind):
                        continue
                    seen.add(u)
                    recs.append({"url": u, "thumb": d.get("turl"),
                                 "title": title, "page": d.get("purl")})
                    if len(recs) >= per:
                        break
                out[key] = recs
                print(f"  [{key:>5}] {len(recs):>2} hits  {q[:56]}", flush=True)
            except Exception as e:                               # noqa: BLE001
                out[key] = []
                print(f"  [{key:>5}] FAIL {type(e).__name__}  {q[:50]}",
                      flush=True)
            finally:
                if ctx is not None:
                    try:
                        ctx.close()
                    except Exception:                            # noqa: BLE001
                        pass
        browser.close()
    return out


def fetch(rec: dict, box=(600, 420)):
    """Full image first, Bing's thumbnail host as fallback. None if unusable."""
    for key in ("url", "thumb"):
        u = rec.get(key)
        if not u:
            continue
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": UA, "Accept": "image/avif,image/webp,*/*",
                "Referer": rec.get("page") or "https://www.bing.com/"})
            im = Image.open(io.BytesIO(
                urllib.request.urlopen(req, timeout=20).read())).convert("RGB")
            if im.width < 240 or im.height < 170:
                continue
            if not (1.05 <= im.width / im.height <= 2.6):
                continue
            im.thumbnail(box, Image.LANCZOS)
            return im
        except Exception:                                        # noqa: BLE001
            continue
    return None


def local(name: str, box=(600, 420)):
    """One of the already-licensed medical stills in dossier/mrbeast/medical."""
    p = MEDICAL / name
    if not p.exists():
        return None
    try:
        im = Image.open(p).convert("RGB")
        im.thumbnail(box, Image.LANCZOS)
        return im
    except Exception:                                            # noqa: BLE001
        return None


def contact_sheet(cells, path, cell=(300, 210), cols=5):
    """A labelled grid, so a human can actually look at what was chosen."""
    from PIL import ImageDraw, ImageFont
    rows = max(1, (len(cells) + cols - 1) // cols)
    sh = Image.new("RGB", (cell[0] * cols, (cell[1] + 24) * rows), (17, 17, 17))
    d = ImageDraw.Draw(sh)
    try:
        f = ImageFont.truetype("arial.ttf", 12)
    except Exception:                                            # noqa: BLE001
        f = ImageFont.load_default()
    for i, (im, lab) in enumerate(cells):
        x, y = (i % cols) * cell[0], (i // cols) * (cell[1] + 24)
        if im is not None:
            t = im.copy()
            t.thumbnail((cell[0] - 8, cell[1] - 8), Image.LANCZOS)
            sh.paste(t, (x + 4 + (cell[0] - 8 - t.width) // 2, y + 4))
        else:
            d.text((x + 12, y + 90), "no image", fill=(190, 70, 70), font=f)
        d.text((x + 6, y + cell[1] + 4), str(lab)[:46],
               fill=(205, 205, 205), font=f)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sh.save(path)
    return path
