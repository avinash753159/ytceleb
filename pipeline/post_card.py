#!/usr/bin/env python3
"""Screenshot Jimmy's real X posts and frame them for 1920x1080.

WHY THIS IS A SCREENSHOT AND NOT A DRAWING
------------------------------------------
The first version of this module hand-drew the posts: Anton caps, a dark
rounded box, an ffmpeg drawtext transcription of his wording. It was
rejected on sight, and correctly - it looked like something the film had
made up. That destroys the only reason the shot exists. The post is the
film's primary evidence: HE wrote it, on a date, in public, and 656,000
people pressed like on it. A viewer can only take that on the picture's
word if the picture IS the post - X's own type, X's own avatar and
verified badge, X's own like counter, captured pixel for pixel.

So: headless Chrome loads X's public embed renderer and we photograph it.

WHAT ENDPOINT
-------------
Render:    https://platform.twitter.com/embed/Tweet.html?id=<ID>&theme=dark
Metadata:  https://cdn.syndication.twimg.com/tweet-result?id=<ID>&lang=en&token=a

Neither needs an API key, a bearer token or a logged-in session. The
embed renders the real markup and pulls the real photos from
pbs.twimg.com, so the frame contains no pixel this film invented.

HARD-WON FACTS - DO NOT REDISCOVER THESE
----------------------------------------
* A browser User-Agent is MANDATORY on every request to any X / twimg /
  platform.twitter.com host. Without one Cloudflare answers HTTP 403
  "error 1010", which reads exactly like a dead credential. That
  misdiagnosis burned an entire session. UA is set on both the urllib
  metadata call and the browser context.
* The embed clamps the post to max-width:550px, and it ignores ?width=,
  ?maxWidth= and the size of the containing window - all three were
  tested and all three come back 550px. 550px cannot fill a 1920 frame,
  so after load we widen exactly one CSS property on the one DIV that is
  the <article>'s parent. Nothing inside is touched: the fonts, avatar,
  business badge, photo grid, timestamp and counters are still X's own
  layout, just given a wider column.
* X's photo grid crops a PORTRAIT photo to 1:1, and the fixed-height
  header/footer only add height. So a portrait post can never be wider
  than it is tall no matter how far the column is widened (the aspect
  asymptote is 1.0). post_gains therefore lands at 39% of frame width,
  not the 62% post_obese gets from its landscape before/after pair.
  The alternative was cropping his head off. Framed as tall as the frame
  allows instead - see FRAME_H.
* chrome.exe --headless --screenshot refuses a RELATIVE output path with
  "Access is denied", and two runs sharing one --user-data-dir make the
  screenshot silently vanish. Playwright drives the same installed
  Chrome binary and sidesteps both, and it is the only way to get an
  element-tight capture plus a real wait-for-images.
* FRAME_H is 960, not 1010, on purpose. first_minute5.py consumes these
  PNGs with fit=False and a zoompan push that ends at 1.08x, which crops
  the outer ~4%. A card sized to the full frame height would have its
  rounded corners and its like counter shaved off in the cut.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PRIM = ROOT / "dossier/mrbeast/primary"
OUT = ROOT / "work/post_cards"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

EMBED = ("https://platform.twitter.com/embed/Tweet.html"
         "?id={sid}&theme=dark&lang=en&dnt=true")
SYND = ("https://cdn.syndication.twimg.com/tweet-result"
        "?id={sid}&lang=en&token=a")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

W, H = 1920, 1080
GROUND = "#0A0A0C"          # the film's ground
FRAME_H = 960               # card height in the finished frame (see docstring)
FRAME_W = 1440              # 75% of 1920 - the ceiling, rarely reached
DPR = 2                     # capture at 2x, downscale with lanczos

POSTS = [
    {
        "key": "post_obese",
        "status_id": "1674429048095916032",
        # Landscape before/after pair, so a wide column pays off: at 1000
        # CSS px the card comes out ~1.24:1 and fills ~62% of frame width.
        "css_w": 1000,
        "img": "mrbeast_transformation_2023-06-29.jpg",
        "text": ("Woke up and realized I was obese so I started lifting "
                 "and walking 12,500 steps a day. Still got a long way to "
                 "being yoked but I'm happy with my progress so far"),
        "date": "29 June 2023",
        "likes": "656,553",
        # Substring that must appear in the captured DOM, or we are looking
        # at a Cloudflare page / "Something went wrong" placeholder.
        "expect": "12,500 steps a day",
    },
    {
        "key": "post_gains",
        "status_id": "1914347042089877638",
        # Single portrait photo, 1:1-cropped by X, so the card can never be
        # wider than tall. Widening the column buys 2-3% of frame width and
        # pays for it by shrinking the type: at 1200px the timestamp lands
        # at ~9px in the finished frame and stops being readable. 700 puts
        # the type within ~10% of post_obese's on-screen size, which is the
        # thing that actually decides whether it reads as a screenshot.
        "css_w": 700,
        "img": "mrbeast_after_2025-04-21_1.jpg",
        "text": "Go get gains boyz",
        "date": "21 April 2025",
        "likes": "147,206",
        "expect": "Go get gains boyz",
    },
]

# Widen the column and drop the page's white backdrop so the card's
# rounded corners come out transparent and composite cleanly onto GROUND.
WIDEN_JS = """(w) => {
  const art = document.querySelector('article');
  const col = art.parentElement;          // carries max-width: 550px
  col.style.maxWidth = w + 'px';
  col.style.width = w + 'px';
  document.documentElement.style.background = 'transparent';
  document.body.style.background = 'transparent';
}"""

# Resolve only once every <img> in the card has finished, decoded or failed.
IMGS_JS = """() => Promise.all([...document.querySelectorAll('article img')]
  .map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; })))
  .then(() => [...document.querySelectorAll('article img')]
    .map(i => [i.currentSrc || i.src, i.naturalWidth, i.naturalHeight]))"""


def meta(sid: str) -> dict:
    """Verbatim text, timestamp and counts, straight from syndication.

    This is not used to draw anything - the picture comes from the embed.
    It goes into posts.json so the cut has a record of exactly what the
    post said and how many likes it carried at capture time.
    """
    req = urllib.request.Request(SYND.format(sid=sid),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    return {
        "text_verbatim": d.get("text", ""),
        "created_utc": d.get("created_at", ""),
        "favorite_count": d.get("favorite_count"),
        "reply_count": d.get("conversation_count"),
        "screen_name": (d.get("user") or {}).get("screen_name"),
        "media": [m.get("media_url_https")
                  for m in (d.get("mediaDetails") or [])],
    }


def shoot(posts: list[dict]) -> dict[str, Path]:
    """Photograph each embed with one headless Chrome, tight to the card."""
    from playwright.sync_api import sync_playwright

    if not CHROME.exists():
        raise FileNotFoundError(f"Chrome not found at {CHROME}")
    raw: dict[str, Path] = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=str(CHROME), headless=True,
                                args=["--hide-scrollbars", "--disable-gpu"])
        try:
            for p in posts:
                raw[p["key"]] = _one(br, p)
        finally:
            br.close()
    return raw


def _one(br, p: dict) -> Path:
    cw = p["css_w"]
    pg = br.new_page(viewport={"width": cw + 80, "height": 1600},
                     device_scale_factor=DPR, user_agent=UA)
    try:
        pg.goto(EMBED.format(sid=p["status_id"]), wait_until="load",
                timeout=90_000)
        pg.wait_for_selector("article", timeout=60_000)
        pg.evaluate(WIDEN_JS, cw)
        pg.wait_for_timeout(1200)          # let the grid relayout at width
        imgs = pg.evaluate(IMGS_JS)
        pg.wait_for_timeout(600)

        body = pg.inner_text("article")
        if p["expect"] not in body:
            raise RuntimeError(
                f"{p['key']}: embed did not render the post - looking for "
                f"{p['expect']!r}, got {body[:200]!r}")
        # The attached photo is the whole point of the frame; if twimg was
        # blocked we must NOT quietly ship a text-only card.
        photo = [i for i in imgs
                 if "pbs.twimg.com/media" in (i[0] or "") and i[1] >= 300]
        if not photo:
            raise RuntimeError(
                f"{p['key']}: post photo did not load from pbs.twimg.com; "
                f"imgs={imgs}. Composite {p['img']} by hand before shipping.")

        art = pg.query_selector("article")
        box = art.bounding_box()
        dest = OUT / f"raw_{p['key']}.png"
        art.screenshot(path=str(dest), omit_background=True)
        print(f"[shot] {p['key']}  css {box['width']:.0f}x{box['height']:.0f}"
              f"  photo {photo[0][1]}x{photo[0][2]}")
        return dest
    finally:
        pg.close()


def frame(card: Path, dest: Path) -> tuple[int, int]:
    """Fit the capture onto the 1920x1080 ground, centred, no watermark."""
    cw, ch = Image.open(card).size
    s = min(FRAME_H / ch, FRAME_W / cw)
    tw, th = int(round(cw * s)) // 2 * 2, int(round(ch * s)) // 2 * 2
    fc = (f"[1:v]scale={tw}:{th}:flags=lanczos[c];"
          f"[0:v][c]overlay=(W-w)/2:(H-h)/2:format=auto,format=rgb24")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"color=c={GROUND}:s={W}x{H}",
         "-i", str(card), "-filter_complex", fc, "-frames:v", "1",
         str(dest)], check=True, timeout=600)
    return tw, th


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = shoot(POSTS)
    made, records = [], []
    for p in POSTS:
        dest = OUT / f"{p['key']}.png"
        tw, th = frame(raw[p["key"]], dest)
        made.append(dest)
        records.append({
            **{k: v for k, v in p.items() if k != "expect"},
            "url": f"https://x.com/MrBeast/status/{p['status_id']}",
            "capture": "platform.twitter.com/embed/Tweet.html screenshot",
            "captured_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
            "card_px": [tw, th],
            "frame_px": [W, H],
            "frame_width_pct": round(100 * tw / W, 1),
            **meta(p["status_id"]),
        })
        print(f"OK  {dest.name}  card {tw}x{th}  "
              f"({100 * tw / W:.0f}% of frame width)")

    if len(made) == 2:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(made[0]), "-i", str(made[1]), "-filter_complex",
             "[0:v]scale=760:428[a];[1:v]scale=760:428[b];[a][b]hstack",
             "-frames:v", "1", str(OUT / "check.jpg")], check=False,
            timeout=300)
    (OUT / "posts.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(made)} real-post screenshots -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
