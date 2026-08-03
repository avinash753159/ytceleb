#!/usr/bin/env python3
"""V9 storyboard page: one cell per 10 seconds of the finished film."""

from __future__ import annotations

import html

KIND = {
    "hero": ("Transformation", "#E3120B"),
    "clinical": ("Clinical", "#7A2E86"),
    "card": ("Graphic", "#1F6F5C"),
    "sync": ("Jimmy, sync", "#14120F"),
    "footage": ("B-roll", "#8A6B1F"),
}

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
  :root{--ground:#14120F;--panel:#1C1916;--ink:#F4F0EA;--ink-soft:#C9C2B8;
        --muted:#948C81;--rule:#332E28;--tint:#221E1A;--red:#F4392F}
}
:root[data-theme="dark"]{--ground:#14120F;--panel:#1C1916;--ink:#F4F0EA;
  --ink-soft:#C9C2B8;--muted:#948C81;--rule:#332E28;--tint:#221E1A;
  --red:#F4392F}
:root[data-theme="light"]{--ground:#FBFAF8;--panel:#FFFFFF;--ink:#14120F;
  --ink-soft:#4A443C;--muted:#7A736A;--rule:#DCD6CC;--tint:#F3EFE9;
  --red:#E3120B}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:var(--serif);line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1280px;margin:0 auto;padding:0 22px 90px}
.mast{border-top:6px solid var(--red);padding-top:18px}
.brandrow{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  border-bottom:1px solid var(--rule);padding-bottom:14px}
.brand{background:var(--red);color:#fff;font-family:var(--sans);
  font-weight:700;font-size:12px;letter-spacing:.14em;
  text-transform:uppercase;padding:5px 10px}
.kicker{font-family:var(--sans);font-size:12px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted)}
h1{font-size:clamp(28px,4.2vw,46px);line-height:1.06;margin:24px 0 10px;
  font-weight:400;text-wrap:balance;letter-spacing:-.012em}
.standfirst{font-size:clamp(16px,1.9vw,20px);color:var(--ink-soft);
  max-width:64ch;margin:0}
.byline{font-family:var(--sans);font-size:12px;color:var(--muted);
  letter-spacing:.06em;text-transform:uppercase;margin:16px 0 0;
  border-top:1px solid var(--rule);padding-top:12px}
section{margin-top:44px}
h2{font-family:var(--sans);font-size:12px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--red);margin:0 0 14px;font-weight:700}
p{max-width:66ch;color:var(--ink-soft)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-family:var(--sans);
  font-size:12px;margin:0 0 8px;padding:0;list-style:none}
.legend li{display:flex;align-items:center;gap:7px;color:var(--muted)}
.dot{width:10px;height:10px;border-radius:2px;display:inline-block}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(196px,1fr));
  gap:14px;margin-top:18px}
.cell{background:var(--panel);border:1px solid var(--rule);overflow:hidden;
  display:flex;flex-direction:column}
.cell.first{outline:2px solid var(--red);outline-offset:-2px}
.th{position:relative;aspect-ratio:16/9;background:var(--tint)}
.th img{width:100%;height:100%;object-fit:cover;display:block}
.ph{display:flex;align-items:center;justify-content:center;height:100%;
  background:repeating-linear-gradient(135deg,var(--tint),var(--tint) 8px,
   transparent 8px,transparent 16px);font-family:var(--sans);font-size:10px;
  letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
  text-align:center;padding:10px}
.t{position:absolute;left:0;top:0;background:var(--ink);color:var(--ground);
  font-family:var(--mono);font-size:11px;padding:2px 6px;
  font-variant-numeric:tabular-nums}
.k{position:absolute;right:0;bottom:0;color:#fff;font-family:var(--sans);
  font-size:9px;letter-spacing:.1em;text-transform:uppercase;padding:3px 6px}
.cap{padding:9px 10px 11px;font-size:12.5px;line-height:1.38;flex:1}
.cap .src{display:block;margin-top:5px;font-family:var(--sans);font-size:10px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.tablewrap{overflow-x:auto;border:1px solid var(--rule);
  background:var(--panel)}
table{border-collapse:collapse;width:100%;min-width:520px;
  font-family:var(--sans);font-size:13.5px}
th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);font-weight:700;padding:10px 13px;
  border-bottom:1px solid var(--rule)}
td{padding:10px 13px;border-bottom:1px solid var(--rule);
  color:var(--ink-soft);vertical-align:top}
tr:last-child td{border-bottom:0}
.callout{border-left:4px solid var(--red);background:var(--tint);
  padding:15px 19px;margin:18px 0}
.callout p{margin:0;color:var(--ink-soft)}
.foot{margin-top:52px;border-top:1px solid var(--rule);padding-top:16px;
  font-family:var(--sans);font-size:12px;color:var(--muted)}
"""

DROPPED = [
    ("Airrack — 600-day transformation", "38 shots",
     "Checked twelve windows: every one is a two-shot with Airrack, him "
     "alone, or neither of them. There is no Jimmy-only window. Dropped."),
    ("Chris Hemsworth — workout circuit", "21 shots",
     "His gym, his crew, burned-in graphics. Jimmy barely in frame."),
    ("MrBeast — Minecraft upload", "2 shots",
     "His own content, but no Jimmy on screen. Dropped on that rule."),
    ("Blausen labelled tract diagram", "1 shot",
     "Replaced with real inflamed tissue, unlabelled."),
]


def esc(s):
    return html.escape(str(s), quote=False)


def mmss(t):
    return f"{t//60}:{t%60:02d}"


def render(ticks, plan, imgs) -> str:
    cells = []
    prev = None
    for t, shot in ticks:
        _s, _e, key, label, src, kind = shot
        first = key != prev
        prev = key
        name, colour = KIND.get(kind, ("", "#666"))
        thumb = (f'<img src="{imgs[key]}" alt="{esc(label)}">'
                 if key in imgs else
                 f'<div class="ph">To design<br>{esc(src)}</div>')
        cells.append(
            f'<div class="cell{" first" if first else ""}">'
            f'<div class="th">{thumb}<span class="t">{mmss(t)}</span>'
            f'<span class="k" style="background:{colour}">{name}</span></div>'
            f'<div class="cap">{esc(label)}<span class="src">{esc(src)}</span>'
            f'</div></div>')

    legend = "".join(
        f'<li><span class="dot" style="background:{c}"></span>{n}</li>'
        for n, c in KIND.values())
    drops = "".join(
        f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>'
        for a, b, c in DROPPED)

    return f"""<style>{CSS}</style>
<div class="wrap">
<header class="mast">
  <div class="brandrow">
    <span class="brand">Celeb Workout</span>
    <span class="kicker">Storyboard · Version 9 · Every 10 seconds</span>
  </div>
  <h1>The Disease That Built MrBeast</h1>
  <p class="standfirst">Every ten seconds of the finished 12:26, as a frame.
  Red-outlined cells are where a new shot begins. Thumbnails are real grabs
  from the footage that will be used.</p>
  <p class="byline">75 frames · audio locked · nothing rendered yet</p>
</header>

<section>
  <h2>Sources dropped since the last pass</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>Source</th><th>Was</th><th>Why</th></tr></thead>
    <tbody>{drops}</tbody>
  </table></div>
  <div class="callout"><p><b>You were right about the Airrack frame.</b> I
  labelled it “Jimmy-only window” without checking. I pulled twelve frames
  around it: every one is a two-shot with Airrack in the red hoodie, or him
  alone, or a clip with neither of them in it. The source cannot satisfy the
  only-Jimmy rule, so it is gone — which removes 38 shots and means the
  interviews and stock now carry the film.</p></div>
</section>

<section>
  <h2>The film, every ten seconds</h2>
  <ul class="legend">{legend}</ul>
  <div class="grid">{"".join(cells)}</div>
</section>

<footer class="foot">
  Frames are real grabs. Medical and clinical stills: Wikimedia Commons —
  CC0, CC BY 2.0, CC BY 4.0, and one CC BY-SA 4.0, credited on screen. Gym
  footage: existing anonymous stock library, never implied to be Jimmy.
  Score: Scott Buckley, CC BY 4.0. Cells marked “to design” are graphics not
  yet built.
</footer>
</div>"""
