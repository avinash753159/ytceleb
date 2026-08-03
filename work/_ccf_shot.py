"""Capture the Crohn's & Colitis Foundation page - text column only.

Three attempts, recorded so nobody repeats them:

1. Plain `chrome --screenshot` caught a "3X MATCH / Gifts TRIPLED / Donate"
   fundraising modal across the middle of the page, plus a stock
   doctor-and-patient photo. Neither can be on screen: a donation
   solicitation reads as the film asking for money, and the photo is two
   people who are not Jimmy.
2. Removing every `position: fixed|sticky` element produced a blank white
   frame - this page's own content wrapper is sticky, so that deleted the
   article.
3. This one. Measured the page first: the h1 sits at x=150 y=214 in a
   1500-wide viewport with the body text below it and the modal off to the
   right. So: remove only imagery and elements whose class actually names a
   modal, then clip to a rectangle anchored on the measured heading position.
   Clipping beats element-screenshotting here because the article element
   wraps the whole page including the promos.
"""
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/docs_v8/ccf_page.png"
URL = "https://www.crohnscolitisfoundation.org/what-is-crohns-disease"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Imagery only, plus elements whose class/id literally names a modal. NOT
# "everything fixed" - that is what blanked the page.
KILL = """
() => {
  let n = 0;
  const pat = /flash-?match|3x-?match|modal|popup|lightbox|backdrop|cookie|consent/i;
  document.querySelectorAll('div,section,aside,dialog').forEach(el => {
    const t = String(el.className || '') + ' ' + String(el.id || '');
    if (pat.test(t)) { el.remove(); n++; }
  });
  document.querySelectorAll('img,picture,figure,video,iframe')
          .forEach(e => { e.remove(); n++; });
  return n;
}
"""


def main() -> int:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, headless=True)
        pg = b.new_page(viewport={"width": 1500, "height": 1500},
                        device_scale_factor=2, user_agent=UA)
        pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(4000)
        print("removed", pg.evaluate(KILL), "modal/media elements")
        pg.wait_for_timeout(500)

        h1 = pg.query_selector("h1")
        if h1 is None or not h1.bounding_box():
            raise RuntimeError("h1 gone - the KILL pattern is too broad again")
        bb = h1.bounding_box()
        print(f"h1 {h1.inner_text()[:50]!r} at "
              f"x={bb['x']:.0f} y={bb['y']:.0f} w={bb['width']:.0f}")

        clip = {"x": max(0.0, bb["x"] - 44), "y": max(0.0, bb["y"] - 44),
                "width": min(bb["width"] + 88, 1500 - max(0.0, bb["x"] - 44)),
                "height": 600}
        raw = OUT.with_suffix(".raw.png")
        pg.screenshot(path=str(raw), clip=clip)
        b.close()

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
         "-vf", "scale=1920:-2:flags=lanczos", str(OUT)],
        check=True, timeout=300)
    raw.unlink(missing_ok=True)
    kb = OUT.stat().st_size / 1024
    print(f"[OK] {OUT}  {kb:.0f} KB")
    if kb < 60:
        print("[warn] suspiciously small - look at it before trusting it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
