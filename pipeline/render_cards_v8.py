#!/usr/bin/env python3
"""Render the v8 full-frame graphic cards as 1920x1080 PNGs.

Headless Chromium via Playwright: Anton is embedded as base64 so the page
is entirely self-contained, and a fit pass shrinks over-long lines before
the screenshot so nothing can clip.

Conventions carried from pipeline/mrbeast_picture_v7.py shot_card():
  * ground #191419 - a LIFTED near-black. A pure-black card once tripped
    blackdetect and read as the film having died.
  * 22px #E3120B bar down the left edge, plus a ~6% #E3120B wash.
  * Anton condensed uppercase, title >=78px, sub ~36px in #CFCFCF.
  * no logo, no watermark, no channel name. Absolute for this film.

The renderer pushes these in ~1.3x, so all content sits inside a 1440x800
box (12% margins) - wider than the 8% asked for, which is what a full
1.3x crop actually needs.
"""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "graphics" / "public" / "fonts" / "Anton-Regular.ttf"
OUT = ROOT / "work" / "cards"
TMP = ROOT / "work" / "cards_html"   # kept out of OUT: that dir is scanned
                                     # for card PNGs by the picture build
W, H = 1920, 1080
ACCENT = "#E3120B"

FONT_B64 = base64.b64encode(FONT.read_bytes()).decode("ascii")

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
@font-face{font-family:'Anton';src:url(data:font/ttf;base64,__FONT__)
  format('truetype');font-weight:400;font-style:normal}
html,body{width:1920px;height:1080px;overflow:hidden;background:#191419}
.frame{position:relative;width:1920px;height:1080px;background:#191419}

/* faint concentric rings - the visual signature of the existing cards */
.rings{position:absolute;inset:0;overflow:hidden}
.rings i{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  border:1px solid rgba(227,18,11,.14);border-radius:50%}
.rings i:nth-child(1){width:1180px;height:1180px}
.rings i:nth-child(2){width:1760px;height:1700px;
  border-color:rgba(227,18,11,.10)}
.rings i:nth-child(3){width:2380px;height:2160px;
  border-color:rgba(227,18,11,.08)}

/* soft accent bloom behind the type */
.bloom{position:absolute;left:50%;top:54%;width:1500px;height:900px;
  transform:translate(-50%,-50%);
  background:radial-gradient(ellipse at center,
    rgba(227,18,11,.26) 0%,rgba(227,18,11,.10) 34%,
    rgba(227,18,11,.03) 58%,rgba(227,18,11,0) 74%)}
/* gentle edge fall-off. Deliberately mild: the darkest pixel must stay
   clearly above #0A0A0C or blackdetect reads the film as dead. */
.vig{position:absolute;inset:0;background:radial-gradient(ellipse 78% 82%
  at 50% 50%,rgba(0,0,0,0) 40%,rgba(0,0,0,.16) 78%,rgba(0,0,0,.24) 100%)}
/* the ~6% wash from shot_card */
.wash{position:absolute;inset:0;background:rgba(227,18,11,.06)}
.bar{position:absolute;left:0;top:0;width:22px;height:1080px;
  background:#E3120B}

.safe{position:absolute;left:240px;top:140px;width:1440px;height:800px;
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center}

/* width is fixed and white-space is nowrap so the fit pass can SEE the
   overflow: a shrink-to-fit element never reports scrollWidth > clientWidth
   and the line silently wraps instead. */
.title{font-family:'Anton',sans-serif;color:#fff;line-height:1.02;
  letter-spacing:.005em;text-transform:uppercase;
  text-shadow:0 0 60px rgba(227,18,11,.34),0 0 18px rgba(0,0,0,.5);
  width:1400px;white-space:nowrap;text-align:center}
.sub{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;
  color:#CFCFCF;font-size:36px;line-height:1.28;letter-spacing:.055em;
  text-transform:uppercase;max-width:1400px}
.sub.anton{font-family:'Anton',sans-serif;letter-spacing:.02em;
  line-height:1.1}
.chip{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;
  color:#9A9A9A;font-size:26px;letter-spacing:.13em;
  text-transform:uppercase;border:1px solid rgba(227,18,11,.42);
  border-left:4px solid #E3120B;border-radius:3px;
  padding:11px 24px 11px 22px;background:rgba(0,0,0,.26);white-space:nowrap}
.chip.loud{color:#D6D6D6;font-size:29px}
.rule{width:150px;height:4px;background:#E3120B;border-radius:2px}

/* card_machine then -> now */
.jump{display:flex;align-items:center;justify-content:center;gap:52px}
.then{font-family:'Anton',sans-serif;font-size:88px;color:#B9B9B9;
  line-height:1}
.arrow{font-family:'Segoe UI',Arial,sans-serif;font-size:104px;
  color:#E3120B;line-height:1;font-weight:700;
  text-shadow:0 0 26px rgba(227,18,11,.6)}
.now{font-family:'Anton',sans-serif;font-size:184px;color:#fff;
  line-height:.96;text-shadow:0 0 70px rgba(227,18,11,.42)}

/* card_infusion2 - 52 weeks of one year, eight to a row, so the marks
   stack into one vertical red line instead of scattering diagonally. */
.grid{display:grid;grid-template-columns:repeat(8,96px);gap:16px}
.cell{width:96px;height:54px;border-radius:4px;
  background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.11)}
.cell.on{background:#E3120B;border-color:#F2554F;
  box-shadow:0 0 22px rgba(227,18,11,.75)}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def page_html(body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{CSS.replace('__FONT__', FONT_B64)}</style></head><body>"
        "<div class='frame'>"
        "<div class='rings'><i></i><i></i><i></i></div>"
        "<div class='bloom'></div><div class='vig'></div>"
        "<div class='wash'></div><div class='bar'></div>"
        f"<div class='safe'>{body}</div>"
        "</div>"
        "<script>"
        "function fitAll(){"
        "for(const el of document.querySelectorAll('[data-fit]')){"
        " let s=parseFloat(getComputedStyle(el).fontSize);"
        " const min=parseFloat(el.dataset.fit);"
        " const box=el.parentElement;"
        " let guard=400;"
        " while(guard-->0&&s>min&&(el.scrollWidth>el.clientWidth+1"
        "   ||box.scrollHeight>box.clientHeight+1)){"
        "  s-=2;el.style.fontSize=s+'px';}}}"
        "</script></body></html>"
    )


def std(title: str, tsize: int, sub: str = "", chip: str = "",
        sub_anton: bool = False, sub_size: int = 36,
        chip_loud: bool = False, rule: bool = False,
        gap: int = 46) -> str:
    """The default card: statement, supporting line, attribution chip."""
    out = [f"<div class='title' data-fit='54' "
           f"style='font-size:{tsize}px'>{esc(title)}</div>"]
    if rule:
        out.append(f"<div class='rule' style='margin-top:{gap}px'></div>")
    if sub:
        cls = "sub anton" if sub_anton else "sub"
        # a \n in the copy is a line break only - never a change of wording
        txt = esc(sub).replace("\n", "<br>")
        out.append(f"<div class='{cls}' style='margin-top:{gap}px;"
                   f"font-size:{sub_size}px'>{txt}</div>")
    if chip:
        cls = "chip loud" if chip_loud else "chip"
        out.append(f"<div class='{cls}' style='margin-top:64px'>"
                   f"{esc(chip)}</div>")
    return "".join(out)


def machine() -> str:
    return (
        "<div class='jump'>"
        "<span class='then'>8,726</span>"
        "<span class='arrow'>&#8594;</span>"
        "<span class='now'>300 MILLION</span>"
        "</div>"
        "<div class='sub' style='margin-top:58px'>OCTOBER 2015, TO NOW</div>"
        "<div class='chip' style='margin-top:60px'>"
        "HIS OWN 2015 SCREEN RECORDING</div>"
    )


def infusion2() -> str:
    # 52 weeks; an infusion at week 1 and every eighth week after -
    # seven marks in a single year, indefinitely.
    cells = "".join(
        f"<div class='cell{' on' if i % 8 == 0 else ''}'></div>"
        for i in range(52))
    return (
        "<div class='title' data-fit='54' style='font-size:92px'>"
        "ONE YEAR OF TREATMENT</div>"
        f"<div class='grid' style='margin-top:48px'>{cells}</div>"
        "<div class='sub' style='margin-top:48px'>"
        "SIX OR SEVEN INFUSIONS. EVERY YEAR.</div>"
    )


def card_end() -> str:
    return ("<div class='title' data-fit='60' style='font-size:132px;"
            "letter-spacing:.02em'>THE DISEASE THAT BUILT MRBEAST</div>")


CARDS: dict[str, str] = {
    "card_infusion": std(
        "REMICADE, EVERY EIGHT WEEKS", 118,
        "AN IV INFUSION. INDEFINITELY.",
        "HIS ACCOUNT — JOE ROGAN #1788"),
    "card_infusion2": infusion2(),
    "card_machine": machine(),
    "card_machine2": std(
        "ONE PROBLEM. TEN YEARS.", 132,
        '"YOU GIVE IT ENOUGH TIME, ANYONE CAN SOLVE IT."',
        "HIS ACCOUNT — JOE ROGAN #1788", sub_size=38),
    "card_contract": std(
        "NOT MOTIVATION", 168,
        "A SECOND PERSON, AND A WRITTEN PENALTY",
        rule=True, sub_size=40),
    "card_contract2": std(
        "A LEGALLY BINDING CONTRACT", 122,
        "WORK OUT EVERY SINGLE DAY",
        "AIRRACK'S ACCOUNT", sub_size=42, chip_loud=True),
    "card_contract2b": std(
        "MISS ONE DAY", 176,
        "HIS NAME, TATTOOED ON YOU",
        "AIRRACK'S ACCOUNT", sub_anton=True, sub_size=62,
        chip_loud=True),
    "card_effort": std(
        "ENOUGH EFFORT BEATS ANYTHING", 122,
        "EXCEPT THIS", sub_anton=True, sub_size=88, rule=True, gap=44),
    "card_time2": std(
        "INPUT. TIME. OUTPUT.", 158,
        "THE BODY DID NOT READ THE SPREADSHEET", sub_size=40),
    "card_rest2": std(
        "THREE MONTHS", 172,
        '"THEN IT\'S EASY"', sub_anton=True, sub_size=74,
        chip="HIS ACCOUNT — COLIN AND SAMIR"),
    # The sub is a correction - the internet repeats 600 as consecutive
    # workouts. It carries more weight than the title, and breaks on the
    # sentence so the denial lands as its own line.
    "card_600": std(
        "SIX HUNDRED DAYS", 104,
        "REST DAYS INCLUDED.\nNOT SIX HUNDRED CONSECUTIVE.",
        sub_anton=True, sub_size=78, rule=True, gap=44),
    "card_end": card_end(),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb",
                                          "--disable-lcd-text"])
        page = browser.new_page(viewport={"width": W, "height": H},
                                device_scale_factor=1)
        for key, body in CARDS.items():
            f = TMP / f"{key}.html"
            f.write_text(page_html(body), encoding="utf-8")
            page.goto(f.as_uri())
            page.evaluate("() => document.fonts.ready")
            page.evaluate("() => fitAll()")
            dest = OUT / f"{key}.png"
            page.screenshot(path=str(dest))
            written.append(str(dest))
        browser.close()
    print(json.dumps(written, indent=1))


if __name__ == "__main__":
    main()
