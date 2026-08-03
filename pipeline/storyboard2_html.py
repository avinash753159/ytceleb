#!/usr/bin/env python3
"""V8 storyboard page. Self-contained; no external requests."""

from __future__ import annotations

import html
from collections import OrderedDict

CSS = """
:root{
  --red:#E3120B;
  --ground:#FBFAF8; --panel:#FFFFFF; --ink:#14120F; --ink-soft:#4A443C;
  --muted:#7A736A; --rule:#DCD6CC; --tint:#F3EFE9;
  --serif:Georgia,"Times New Roman",Times,serif;
  --sans:"Helvetica Neue",Helvetica,Arial,system-ui,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root{ --ground:#14120F; --panel:#1C1916; --ink:#F4F0EA;
         --ink-soft:#C9C2B8; --muted:#948C81; --rule:#332E28;
         --tint:#221E1A; --red:#F4392F; }
}
:root[data-theme="dark"]{ --ground:#14120F; --panel:#1C1916; --ink:#F4F0EA;
  --ink-soft:#C9C2B8; --muted:#948C81; --rule:#332E28; --tint:#221E1A;
  --red:#F4392F; }
:root[data-theme="light"]{ --ground:#FBFAF8; --panel:#FFFFFF; --ink:#14120F;
  --ink-soft:#4A443C; --muted:#7A736A; --rule:#DCD6CC; --tint:#F3EFE9;
  --red:#E3120B; }

*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:var(--serif);line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1140px;margin:0 auto;padding:0 24px 96px}
.mast{border-top:6px solid var(--red);padding-top:18px}
.brandrow{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  border-bottom:1px solid var(--rule);padding-bottom:14px}
.brand{background:var(--red);color:#fff;font-family:var(--sans);
  font-weight:700;font-size:12px;letter-spacing:.14em;text-transform:uppercase;
  padding:5px 10px}
.kicker{font-family:var(--sans);font-size:12px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted)}
h1{font-size:clamp(30px,4.6vw,50px);line-height:1.06;margin:26px 0 10px;
  font-weight:400;text-wrap:balance;letter-spacing:-.012em}
.standfirst{font-size:clamp(17px,2vw,21px);color:var(--ink-soft);
  max-width:62ch;margin:0;line-height:1.5}
.byline{font-family:var(--sans);font-size:12px;color:var(--muted);
  letter-spacing:.06em;text-transform:uppercase;margin:18px 0 0;
  border-top:1px solid var(--rule);padding-top:12px}
section{margin-top:52px}
h2{font-family:var(--sans);font-size:12px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--red);margin:0 0 14px;font-weight:700}
h3{font-size:25px;font-weight:400;margin:0 0 10px;letter-spacing:-.01em}
p{max-width:66ch}
.lede{font-size:17px;color:var(--ink-soft)}
.tablewrap{overflow-x:auto;border:1px solid var(--rule);background:var(--panel)}
table{border-collapse:collapse;width:100%;min-width:560px;
  font-family:var(--sans);font-size:14px}
th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);font-weight:700;padding:11px 14px;
  border-bottom:1px solid var(--rule);white-space:nowrap}
td{padding:11px 14px;border-bottom:1px solid var(--rule);
  color:var(--ink-soft);vertical-align:top}
tr:last-child td{border-bottom:0}
td.where{font-family:var(--sans);font-size:12px;color:var(--muted);
  white-space:nowrap}
.act{margin-top:56px;border-top:3px solid var(--ink);padding-top:12px}
.actrow{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.actname{font-size:23px;letter-spacing:-.01em}
.actclock{font-family:var(--mono);font-size:13px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));
  gap:26px;margin-top:22px}
.shot{background:var(--panel);border:1px solid var(--rule);
  display:flex;flex-direction:column}
.shot.hero{border:2px solid var(--red)}
.thumb{position:relative;aspect-ratio:16/9;background:var(--tint);
  overflow:hidden;border-bottom:1px solid var(--rule)}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.tc{position:absolute;left:0;bottom:0;background:var(--red);color:#fff;
  font-family:var(--mono);font-size:12px;padding:3px 8px;
  font-variant-numeric:tabular-nums}
.flag{position:absolute;right:0;top:0;background:var(--ink);color:var(--ground);
  font-family:var(--sans);font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;padding:4px 8px}
.card-ph{display:flex;align-items:center;justify-content:center;height:100%;
  background:repeating-linear-gradient(135deg,var(--tint),var(--tint) 9px,
   transparent 9px,transparent 18px);
  font-family:var(--sans);font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--muted);text-align:center;padding:16px}
.meta{padding:14px 16px 16px;display:flex;flex-direction:column;gap:9px;flex:1}
.onscreen{font-size:16px;line-height:1.42;margin:0}
.src{font-family:var(--sans);font-size:11px;letter-spacing:.07em;
  text-transform:uppercase;color:var(--muted)}
.why{font-size:14px;color:var(--ink-soft);margin:0;padding-top:9px;
  border-top:1px solid var(--rule);line-height:1.5}
.callout{border-left:4px solid var(--red);background:var(--tint);
  padding:16px 20px;margin:22px 0}
.callout p{margin:0}
ul{max-width:66ch;padding-left:20px} li{margin:6px 0}
.foot{margin-top:60px;border-top:1px solid var(--rule);padding-top:16px;
  font-family:var(--sans);font-size:12px;color:var(--muted)}
@media (max-width:640px){ .shots{grid-template-columns:1fr} }
"""

ACT_CLOCK = OrderedDict([
    ("Cold open", "0:02 – 0:46"),
    ("The body he lost", "0:46 – 1:49"),
    ("What it feels like", "1:49 – 4:15"),
    ("The machine", "4:15 – 5:25"),
    ("The contract", "5:25 – 7:02"),
    ("The verified protocol", "7:02 – 8:49"),
    ("The limit of control", "8:49 – 9:54"),
    ("Something had to give", "9:54 – 11:00"),
    ("Reclaiming the body", "11:00 – 12:26"),
])

HERO = {"ba_open", "ba_payoff", "real_tissue", "clinical_strip"}


def esc(s):
    return html.escape(str(s), quote=False)


def render(shots, cut, imgs) -> str:
    by_act = OrderedDict((a, []) for a in ACT_CLOCK)
    for key, act, tc, onscreen, src, why in shots:
        by_act.setdefault(act, []).append((key, tc, onscreen, src, why))

    acts = []
    for act, clock in ACT_CLOCK.items():
        items = by_act.get(act) or []
        if not items:
            continue
        cards = []
        for key, tc, onscreen, src, why in items:
            hero = " hero" if key in HERO else ""
            flag = ""
            if key in ("ba_open", "ba_payoff"):
                flag = '<span class="flag">Transformation</span>'
            elif key in ("real_tissue", "clinical_strip", "zoom_wall",
                         "mechanism"):
                flag = '<span class="flag">Clinical</span>'
            if key in imgs:
                thumb = f'<img src="{imgs[key]}" alt="{esc(onscreen)}">'
            else:
                thumb = (f'<div class="card-ph">To be designed<br>'
                         f'{esc(src)}</div>')
            cards.append(
                f'<figure class="shot{hero}"><div class="thumb">{thumb}'
                f'{flag}<span class="tc">{esc(tc)}</span></div>'
                f'<figcaption class="meta">'
                f'<p class="onscreen">{esc(onscreen)}</p>'
                f'<span class="src">{esc(src)}</span>'
                f'<p class="why">{esc(why)}</p></figcaption></figure>')
        acts.append(
            f'<div class="act"><div class="actrow">'
            f'<span class="actname">{esc(act)}</span>'
            f'<span class="actclock">{esc(clock)}</span></div>'
            f'<div class="shots">{"".join(cards)}</div></div>')

    cutrows = "\n".join(
        f'<tr><td>{esc(what)}</td><td class="where">{esc(where)}</td>'
        f'<td>{esc(why)}</td></tr>' for what, where, why in cut)

    return f"""<style>{CSS}</style>
<div class="wrap">
<header class="mast">
  <div class="brandrow">
    <span class="brand">Celeb Workout</span>
    <span class="kicker">Storyboard · Version 8 · Revised on notes</span>
  </div>
  <h1>The Disease That Built MrBeast</h1>
  <p class="standfirst">Rebuilt around the transformation. Real clinical
  imagery instead of diagrams, gym footage under the protocol, Jimmy alone
  in every frame that has a person in it.</p>
  <p class="byline">Audio locked at 12:26 · Every thumbnail is a real grab ·
  Nothing built yet</p>
</header>

<section>
  <h2>What changed</h2>
  <h3>The transformation now opens and closes the film</h3>
  <p class="lede">It was buried before — one late shot of Jimmy and another
  creator. It is now the first image on screen, before a word is spoken, and
  the last thing the film pays off. Both instances are dated so the viewer
  knows exactly what they are comparing.</p>
  <div class="callout">
    <p><b>Clinical imagery is now real.</b> The labelled anatomy chart is
    gone, replaced by an unlabelled zoom to the bowel wall. The microscope
    slide is gone entirely. In their place: resected Crohn’s tissue, and a
    strip of four brief clinical shots — roughly six-tenths of a second
    each — rather than one long one.</p>
  </div>
</section>

<section>
  <h2>Cut on your notes</h2>
  <div class="tablewrap">
  <table>
    <thead><tr><th>Shot</th><th>Was in</th><th>Why it is gone</th></tr>
    </thead><tbody>{cutrows}</tbody>
  </table>
  </div>
</section>

<section>
  <h2>Rules</h2>
  <ul>
    <li><b>Only Jimmy.</b> No other creator appears in any frame. Eric is
    out of the film entirely.</li>
    <li><b>Transformation is the spine</b>, seeded at 0:02 and paid off at
    11:18, both dated.</li>
    <li><b>Clinical shots are short and plural</b> — never one long hold,
    never captioned or implied as Jimmy.</li>
    <li><b>Numbers ride over real footage</b>, not bare cards on black.</li>
    <li><b>Minecraft appears once</b>, under the line about uploading to
    nobody.</li>
    <li><b>No third-party captions, overlays or branding</b> — every window
    OCR-checked before use.</li>
  </ul>
</section>

<section>
  <h2>The film, shot by shot</h2>
  {"".join(acts)}
</section>

<footer class="foot">
  Thumbnails are real frames from downloaded sources and licensed stills.
  Clinical and anatomical images: Wikimedia Commons — CC0, CC BY 2.0,
  CC BY 3.0, CC BY 4.0 and one CC BY-SA 4.0, each credited on screen.
  Gym footage: existing stock library. Score: Scott Buckley, CC BY 4.0.
</footer>
</div>"""
