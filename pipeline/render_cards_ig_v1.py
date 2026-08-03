#!/usr/bin/env python3
"""Render the five *diagrammatic* cards as 1920x1080 PNGs.

Same machinery and same house style as pipeline/render_cards_v8.py -
headless Chromium via Playwright, Anton embedded as base64, one
self-contained local HTML per card - but these are infographics rather
than headline cards: a bar that fills, a dial of ten segments, an icon
row, a rejected/accepted comparison, a signed document. The picture
carries the information; the words only label it.

Ground rules carried over verbatim from the v8 renderer:
  * ground #191419 with a ~6% #E3120B wash. NEVER pure black - a
    near-black card once tripped blackdetect and read as the film having
    died. The vignette here is milder than v8's (.16 vs .24) so the
    darkest pixel stays clear of the >=18 luma floor.
  * 22px #E3120B bar down the left edge.
  * Anton condensed uppercase for all display type.
  * no logo, no watermark, no channel name. Absolute for this film.
  * everything inside the 12% safe box: x 240-1680, y 140-940.

Every figure on these cards is sourced. Nothing here may be invented.
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
TMP = ROOT / "work" / "cards_html"
W, H = 1920, 1080

FONT_B64 = base64.b64encode(FONT.read_bytes()).decode("ascii")

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
@font-face{font-family:'Anton';src:url(data:font/ttf;base64,__FONT__)
  format('truetype');font-weight:400;font-style:normal}
html,body{width:1920px;height:1080px;overflow:hidden;background:#191419}
.frame{position:relative;width:1920px;height:1080px;background:#191419}

.rings{position:absolute;inset:0;overflow:hidden}
.rings i{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  border:1px solid rgba(227,18,11,.14);border-radius:50%}
.rings i:nth-child(1){width:1180px;height:1180px}
.rings i:nth-child(2){width:1760px;height:1700px;
  border-color:rgba(227,18,11,.10)}
.rings i:nth-child(3){width:2380px;height:2160px;
  border-color:rgba(227,18,11,.08)}
.bloom{position:absolute;left:50%;top:54%;width:1500px;height:900px;
  transform:translate(-50%,-50%);
  background:radial-gradient(ellipse at center,
    rgba(227,18,11,.24) 0%,rgba(227,18,11,.09) 34%,
    rgba(227,18,11,.03) 58%,rgba(227,18,11,0) 74%)}
/* milder than v8: these cards carry panels and hairlines out at the
   edges, and the darkest pixel has to stay above luma 18. */
.vig{position:absolute;inset:0;background:radial-gradient(ellipse 80% 84%
  at 50% 50%,rgba(0,0,0,0) 44%,rgba(0,0,0,.10) 80%,rgba(0,0,0,.16) 100%)}
.wash{position:absolute;inset:0;background:rgba(227,18,11,.06)}
.bar{position:absolute;left:0;top:0;width:22px;height:1080px;
  background:#E3120B}

/* the 12% safe box */
.safe{position:absolute;left:240px;top:140px;width:1440px;height:800px;
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center}

.title{font-family:'Anton',sans-serif;color:#fff;line-height:1.03;
  letter-spacing:.005em;text-transform:uppercase;
  text-shadow:0 0 60px rgba(227,18,11,.34),0 0 14px rgba(227,18,11,.30);
  width:1440px;white-space:nowrap;text-align:center}
.sub{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;
  color:#CFCFCF;font-size:36px;line-height:1.3;letter-spacing:.055em;
  text-transform:uppercase}
.note{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;
  color:#9E9298;font-size:26px;letter-spacing:.13em;
  text-transform:uppercase}
.chip{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;
  color:#B9B9B9;font-size:27px;letter-spacing:.13em;
  text-transform:uppercase;border:1px solid rgba(227,18,11,.42);
  border-left:4px solid #E3120B;border-radius:3px;
  padding:11px 24px 11px 22px;background:rgba(255,255,255,.035);
  white-space:nowrap}
.chip.loud{color:#EDEDED;font-size:32px;
  border-color:rgba(227,18,11,.6);border-left-color:#E3120B;
  background:rgba(227,18,11,.12)}
.rule{width:150px;height:4px;background:#E3120B;border-radius:2px}

/* ---------- card_scale : two bars, one of them almost nothing -------- */
.axis{width:1440px;display:flex;font-family:'Segoe UI',Arial,sans-serif;
  color:#9E9298;font-size:25px;letter-spacing:.16em;text-transform:uppercase}
.axis span{width:300px;text-align:right;padding-right:28px;color:#7E747A}
.srow{width:1440px;display:flex;align-items:center}
.slab{width:300px;text-align:right;padding-right:28px;
  font-family:'Anton',sans-serif;font-size:38px;color:#B7ADB2;
  letter-spacing:.03em;line-height:1}
.strack{width:1140px;height:120px;position:relative;
  background:rgba(255,255,255,.045);
  border:1px solid rgba(255,255,255,.09);border-radius:4px}
.sbar{position:absolute;left:0;top:0;height:100%;border-radius:3px;
  background:linear-gradient(90deg,#B60D08 0%,#E3120B 62%,#FF4038 100%);
  box-shadow:0 0 34px rgba(227,18,11,.55);display:flex;align-items:center;
  justify-content:flex-end}
.sbar.tiny{width:6px;box-shadow:0 0 22px rgba(227,18,11,.85);
  background:#FF4038}
.snow{font-family:'Anton',sans-serif;font-size:82px;color:#fff;
  line-height:1;padding-right:30px;letter-spacing:.01em;
  text-shadow:0 2px 18px rgba(0,0,0,.45)}
.sthen{position:absolute;left:34px;top:50%;transform:translateY(-50%);
  font-family:'Anton',sans-serif;font-size:60px;color:#CFC6CB;line-height:1}

/* ---------- card_protocol_ig : four icon tiles ---------------------- */
.tiles{display:flex;gap:32px}
.tile{width:336px;height:352px;border-radius:6px;
  background:rgba(255,255,255,.045);
  border:1px solid rgba(227,18,11,.28);border-top:5px solid #E3120B;
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:22px 16px 26px}
.tile .ico{height:112px;display:flex;align-items:center}
.hero{font-family:'Anton',sans-serif;color:#fff;font-size:56px;
  line-height:1;margin-top:26px;letter-spacing:.01em;white-space:nowrap}
.tsub{font-family:'Segoe UI',Arial,sans-serif;color:#B3A9AE;font-size:24px;
  letter-spacing:.12em;margin-top:16px;text-transform:uppercase;
  white-space:nowrap}

/* ---------- card_decade : a ten-segment dial ------------------------ */
.two{width:1440px;display:flex;align-items:center;justify-content:space-between}
.colL{width:790px;text-align:left}
.dialwrap{position:relative;width:520px;height:520px;
  display:flex;align-items:center;justify-content:center}
.dialtxt{position:absolute;left:0;top:0;width:520px;height:520px;
  display:flex;flex-direction:column;align-items:center;justify-content:center}
.dialnum{font-family:'Anton',sans-serif;font-size:172px;color:#fff;
  line-height:.9;text-shadow:0 0 50px rgba(227,18,11,.45)}
.dialcap{font-family:'Anton',sans-serif;font-size:44px;color:#E3120B;
  letter-spacing:.16em;margin-top:10px;line-height:1}

/* ---------- card_nomotivation : rejected vs. what held -------------- */
.row3{display:flex;align-items:center;gap:16px}
.panel{width:420px;height:470px;border-radius:6px;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(227,18,11,.3);border-top:5px solid #E3120B;
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;position:relative;padding:20px 14px}
.panel.dead{background:rgba(255,255,255,.028);
  border-color:rgba(255,255,255,.13);border-top-color:#6E6469;
  overflow:hidden}
.panel.dead .ico{opacity:.5}
.panel .plabel{font-family:'Anton',sans-serif;color:#fff;font-size:56px;
  line-height:1.06;margin-top:34px;text-align:center;letter-spacing:.01em}
.panel.dead .plabel{color:#9C9095}
/* the strike sits across the icon, clear of the words underneath */
.slash{position:absolute;left:-44px;top:162px;width:508px;height:10px;
  background:#E3120B;border-radius:5px;
  box-shadow:0 0 26px rgba(227,18,11,.8);
  transform:rotate(-20deg)}
.op{width:58px;display:flex;align-items:center;justify-content:center;
  filter:drop-shadow(0 0 16px rgba(227,18,11,.55))}

/* ---------- card_contract_ig : the document ------------------------- */
.doc{width:1300px;border-radius:5px;background:rgba(255,255,255,.055);
  border:1px solid rgba(227,18,11,.34);border-top:7px solid #E3120B;
  padding:38px 46px 34px;box-shadow:0 22px 52px rgba(0,0,0,.12)}
.docttl{font-family:'Anton',sans-serif;color:#fff;font-size:84px;
  line-height:1;text-align:center;white-space:nowrap;width:1208px;
  letter-spacing:.012em;text-shadow:0 0 44px rgba(227,18,11,.32)}
.hair{width:1208px;height:1px;background:rgba(255,255,255,.18);
  margin:26px 0 24px}
.clause{display:flex;align-items:center;gap:22px;text-align:left}
.num{width:52px;height:52px;flex:0 0 52px;border-radius:3px;background:#E3120B;
  font-family:'Anton',sans-serif;font-size:34px;color:#fff;display:flex;
  align-items:center;justify-content:center;line-height:1}
.ctxt{font-family:'Anton',sans-serif;color:#fff;font-size:58px;line-height:1.04;
  letter-spacing:.012em}
.pen{margin-top:22px;padding:18px 22px;border-left:6px solid #E3120B;
  background:rgba(227,18,11,.12);border-radius:0 4px 4px 0}
.pentag{font-family:'Segoe UI',Arial,sans-serif;color:#FF5A52;font-size:22px;
  letter-spacing:.22em;text-transform:uppercase;text-align:left;
  margin-bottom:10px}
.sigs{display:flex;justify-content:space-between;margin-top:34px}
.sig{width:530px}
.sigline{width:530px;height:2px;background:rgba(255,255,255,.36);
  margin-top:2px}
.sigcap{font-family:'Segoe UI',Arial,sans-serif;color:#9E9298;font-size:21px;
  letter-spacing:.2em;text-transform:uppercase;margin-top:12px;text-align:left}
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
        " let guard=400;"
        " while(guard-->0&&s>min&&el.scrollWidth>el.clientWidth+1){"
        "  s-=2;el.style.fontSize=s+'px';}}}"
        "</script></body></html>"
    )


# --------------------------------------------------------------------------
# icon vocabulary - flat SVG, red on the ground, no photography
# --------------------------------------------------------------------------
RED = "#E3120B"


def ico_week() -> str:
    """Seven filled marks: every day of the week."""
    cells = "".join(
        f"<rect x='{6 + i*26}' y='14' width='19' height='58' rx='3' "
        f"fill='{RED}'/>" for i in range(7))
    return (f"<svg width='196' height='96' viewBox='0 0 196 96'>{cells}"
            f"<rect x='4' y='84' width='190' height='5' rx='2.5' "
            f"fill='rgba(227,18,11,.45)'/></svg>")


def ico_steps() -> str:
    """A pair of footprints - forefoot, toes, heel."""
    def foot(x: int, y: int, rot: int) -> str:
        toes = "".join(
            f"<circle cx='{x + dx}' cy='{y + dy}' r='5.4' fill='{RED}'/>"
            for dx, dy in ((-13, -23), (-4.5, -29), (5, -29), (14, -24)))
        return (f"<g transform='rotate({rot} {x} {y})'>"
                f"<ellipse cx='{x}' cy='{y}' rx='19' ry='24' fill='{RED}'/>"
                f"{toes}"
                f"<ellipse cx='{x}' cy='{y+42}' rx='12.5' ry='15' "
                f"fill='{RED}'/></g>")
    return (f"<svg width='196' height='108' viewBox='0 0 196 108'>"
            f"{foot(60, 36, -10)}{foot(136, 54, -10)}</svg>")


def ico_clock45() -> str:
    """A 60-minute dial with 45 minutes swept."""
    return (
        "<svg width='112' height='112' viewBox='0 0 112 112'>"
        "<circle cx='56' cy='56' r='48' fill='none' "
        "stroke='rgba(255,255,255,.16)' stroke-width='11'/>"
        f"<circle cx='56' cy='56' r='48' fill='none' stroke='{RED}' "
        "stroke-width='11' stroke-linecap='butt' "
        "stroke-dasharray='226.2 75.4' transform='rotate(-90 56 56)'/>"
        f"<circle cx='56' cy='56' r='6' fill='{RED}'/>"
        f"<rect x='53' y='24' width='6' height='34' rx='3' fill='{RED}'/>"
        f"<rect x='56' y='53' width='26' height='6' rx='3' fill='{RED}'/>"
        "</svg>")


def ico_rest() -> str:
    """Pause: the day off, without claiming how many."""
    return (
        "<svg width='112' height='112' viewBox='0 0 112 112'>"
        f"<circle cx='56' cy='56' r='48' fill='none' stroke='{RED}' "
        "stroke-width='9'/>"
        f"<rect x='38' y='34' width='13' height='44' rx='4' fill='{RED}'/>"
        f"<rect x='61' y='34' width='13' height='44' rx='4' fill='{RED}'/>"
        "</svg>")


def ico_falling() -> str:
    """Five bars falling away - a quantity that does not hold."""
    hs = [96, 74, 54, 36, 20]
    bars = "".join(
        f"<rect x='{6 + i*38}' y='{100-h}' width='27' height='{h}' rx='3' "
        f"fill='#8C8189' opacity='{1 - i*0.15:.2f}'/>"
        for i, h in enumerate(hs))
    return (f"<svg width='196' height='108' viewBox='0 0 196 108'>{bars}"
            "<rect x='2' y='102' width='192' height='4' rx='2' "
            "fill='rgba(255,255,255,.22)'/></svg>")


def ico_two_people() -> str:
    """Two figures, tied together."""
    def person(cx: int, fill: str) -> str:
        return (f"<circle cx='{cx}' cy='26' r='20' fill='{fill}'/>"
                f"<path d='M{cx-34} 96 q0 -32 34 -32 q34 0 34 32 z' "
                f"fill='{fill}'/>")
    return (
        "<svg width='196' height='120' viewBox='0 0 196 120'>"
        f"{person(52, '#B7ADB2')}{person(144, RED)}"
        f"<path d='M52 108 L52 114 L144 114 L144 108' fill='none' "
        f"stroke='{RED}' stroke-width='6' stroke-linecap='round' "
        "stroke-linejoin='round'/></svg>")


def ico_penalty_doc() -> str:
    """A written page with a signature on it."""
    return (
        "<svg width='150' height='128' viewBox='0 0 150 128'>"
        "<path d='M14 6 h84 l38 36 v80 h-122 z' fill='rgba(255,255,255,.10)' "
        f"stroke='{RED}' stroke-width='5' stroke-linejoin='round'/>"
        f"<path d='M98 6 v36 h38' fill='none' stroke='{RED}' "
        "stroke-width='5' stroke-linejoin='round'/>"
        "<rect x='32' y='56' width='74' height='6' rx='3' fill='#B7ADB2'/>"
        "<rect x='32' y='72' width='58' height='6' rx='3' fill='#B7ADB2'/>"
        f"<path d='M32 100 q14 -16 26 -2 q10 12 22 -6 q9 -13 22 2' "
        f"fill='none' stroke='{RED}' stroke-width='6' stroke-linecap='round'/>"
        "</svg>")


def scrawl(seed: int) -> str:
    """A signature squiggle - two different hands, both red."""
    paths = {
        0: "M10 52 q22 -44 40 -10 q13 25 30 -18 q10 -25 26 6 q9 18 30 -20"
           " q12 -22 28 8",
        1: "M12 48 q18 -34 34 -4 q12 22 26 -20 q11 -32 30 4 q11 21 34 -14"
           " q14 -21 30 14",
    }
    return (f"<svg width='250' height='64' viewBox='0 0 250 64'>"
            f"<path d='{paths[seed]}' fill='none' stroke='{RED}' "
            f"stroke-width='6' stroke-linecap='round'/></svg>")


# --------------------------------------------------------------------------
# the five cards
# --------------------------------------------------------------------------
def card_scale() -> str:
    """8,726 in October 2015 -> 300 million+ today, as two bars."""
    return (
        "<div class='axis'><span>SUBSCRIBERS</span></div>"
        "<div class='srow' style='margin-top:26px'>"
        "  <div class='slab'>OCTOBER 2015</div>"
        "  <div class='strack'><div class='sbar tiny'></div>"
        "    <div class='sthen'>8,726</div></div>"
        "</div>"
        "<div class='srow' style='margin-top:34px'>"
        "  <div class='slab'>TODAY</div>"
        "  <div class='strack'><div class='sbar' style='width:1138px'>"
        "    <div class='snow'>300 MILLION+</div></div></div>"
        "</div>"
        "<div class='note' style='margin-top:40px'>"
        "AT TRUE SCALE, THE 2015 BAR WOULD BE INVISIBLE</div>"
        "<div class='chip' style='margin-top:46px'>"
        "HIS OWN 2015 SCREEN RECORDING</div>"
    )


def card_protocol_ig() -> str:
    tiles = [
        (ico_week(), "EVERY DAY", "WORKS OUT"),
        (ico_steps(), "12,500", "STEPS A DAY"),
        (ico_clock45(), "45 MINUTES", "5 DAYS A WEEK"),
        (ico_rest(), "REST DAYS", "WERE PART OF IT"),
    ]
    cells = "".join(
        f"<div class='tile'><div class='ico'>{ico}</div>"
        f"<div class='hero'>{hero}</div><div class='tsub'>{sub}</div></div>"
        for ico, hero, sub in tiles)
    return (
        "<div class='title' data-fit='54' style='font-size:82px'>"
        "WHAT HE ACTUALLY SAID HE DOES</div>"
        f"<div class='tiles' style='margin-top:46px'>{cells}</div>"
        "<div class='note' style='margin-top:44px'>"
        "NO TRAINING SPLIT, SETS, REPS OR CALORIES WERE EVER PUBLISHED.</div>"
    )


def dial10() -> str:
    """Ten segments closing a full circle: ten years on one problem."""
    r = 190
    circ = 2 * 3.141592653589793 * r          # 1193.805
    seg = circ / 10                            # 119.38
    gap = 15.0
    dash = seg - gap
    ticks = []
    for i in range(10):
        ang = -90 + (i + 0.5) * 36
        ticks.append(
            f"<circle cx='260' cy='260' r='6' fill='rgba(255,255,255,.34)' "
            f"transform='rotate({ang} 260 260) translate(0 -{r - 44})'/>")
    return (
        "<svg width='520' height='520' viewBox='0 0 520 520'>"
        f"<circle cx='260' cy='260' r='{r}' fill='none' "
        "stroke='rgba(255,255,255,.10)' stroke-width='30'/>"
        f"<circle cx='260' cy='260' r='{r}' fill='none' stroke='{RED}' "
        f"stroke-width='30' stroke-dasharray='{dash:.2f} {gap:.2f}' "
        "transform='rotate(-90 260 260)' "
        "style='filter:drop-shadow(0 0 16px rgba(227,18,11,.55))'/>"
        f"{''.join(ticks)}"
        "</svg>")


def card_decade() -> str:
    return (
        "<div class='two'>"
        "<div class='colL'>"
        "  <div style=\"font-family:'Anton',sans-serif;color:#fff;"
        "font-size:112px;line-height:1;letter-spacing:.01em;"
        "text-shadow:0 0 50px rgba(227,18,11,.32)\">ONE PROBLEM.</div>"
        "  <div class='rule' style='margin-top:34px'></div>"
        "  <div class='sub' style='margin-top:34px;font-size:38px'>"
        "&ldquo;YOU GIVE IT ENOUGH TIME,<br>ANYONE CAN SOLVE IT.&rdquo;</div>"
        "  <div class='chip' style='margin-top:40px;display:inline-block'>"
        "HIS ACCOUNT &mdash; JOE ROGAN #1788</div>"
        "</div>"
        f"<div class='dialwrap'>{dial10()}"
        "  <div class='dialtxt'><div class='dialnum'>10</div>"
        "    <div class='dialcap'>YEARS</div></div>"
        "</div>"
        "</div>"
    )


def op_arrow() -> str:
    return (f"<svg width='56' height='44' viewBox='0 0 56 44'>"
            f"<rect x='2' y='16' width='34' height='12' rx='6' fill='{RED}'/>"
            f"<path d='M32 4 L54 22 L32 40 z' fill='{RED}'/></svg>")


def op_plus() -> str:
    return (f"<svg width='48' height='48' viewBox='0 0 48 48'>"
            f"<rect x='18' y='2' width='12' height='44' rx='6' fill='{RED}'/>"
            f"<rect x='2' y='18' width='44' height='12' rx='6' fill='{RED}'/>"
            "</svg>")


def card_nomotivation() -> str:
    return (
        "<div class='row3'>"
        "  <div class='panel dead'>"
        f"    <div class='ico'>{ico_falling()}</div>"
        "    <div class='plabel'>NOT<br>MOTIVATION</div>"
        "    <div class='slash'></div>"
        "  </div>"
        f"  <div class='op'>{op_arrow()}</div>"
        "  <div class='panel'>"
        f"    <div class='ico'>{ico_two_people()}</div>"
        "    <div class='plabel'>A SECOND<br>PERSON</div>"
        "  </div>"
        f"  <div class='op'>{op_plus()}</div>"
        "  <div class='panel'>"
        f"    <div class='ico'>{ico_penalty_doc()}</div>"
        "    <div class='plabel'>A WRITTEN<br>PENALTY</div>"
        "  </div>"
        "</div>"
    )


def card_contract_ig() -> str:
    return (
        "<div class='doc'>"
        "  <div class='docttl' data-fit='46'>A LEGALLY BINDING CONTRACT</div>"
        "  <div class='hair'></div>"
        "  <div class='clause'><div class='num'>1</div>"
        "    <div class='ctxt'>WORK OUT EVERY SINGLE DAY</div></div>"
        "  <div class='pen'>"
        "    <div class='pentag'>Penalty clause</div>"
        "    <div class='clause'><div class='num'>2</div>"
        "      <div class='ctxt'>MISS ONE DAY:<br>"
        "HIS NAME, TATTOOED ON YOU</div></div>"
        "  </div>"
        "  <div class='sigs'>"
        f"    <div class='sig'>{scrawl(0)}<div class='sigline'></div>"
        "      <div class='sigcap'>Signed</div></div>"
        f"    <div class='sig'>{scrawl(1)}<div class='sigline'></div>"
        "      <div class='sigcap'>Signed</div></div>"
        "  </div>"
        "</div>"
        "<div class='chip loud' style='margin-top:34px'>"
        "AIRRACK&#8217;S ACCOUNT</div>"
    )


CARDS: dict[str, str] = {
    "card_scale": card_scale(),
    "card_protocol_ig": card_protocol_ig(),
    "card_decade": card_decade(),
    "card_nomotivation": card_nomotivation(),
    "card_contract_ig": card_contract_ig(),
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
