#!/usr/bin/env python3
"""Economist-styled storyboard page. Self-contained: no external requests."""

from __future__ import annotations

import html
from collections import OrderedDict

CSS = """
:root{
  --red:#E3120B; --red-deep:#A50D08;
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
  font-family:var(--serif);line-height:1.55;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px 96px}

/* masthead */
.mast{border-top:6px solid var(--red);padding-top:18px;margin-top:0}
.brandrow{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  border-bottom:1px solid var(--rule);padding-bottom:14px}
.brand{background:var(--red);color:#fff;font-family:var(--sans);
  font-weight:700;font-size:12px;letter-spacing:.14em;
  text-transform:uppercase;padding:5px 10px}
.kicker{font-family:var(--sans);font-size:12px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted)}
h1{font-size:clamp(30px,4.6vw,50px);line-height:1.06;margin:26px 0 10px;
  font-weight:400;text-wrap:balance;letter-spacing:-.012em}
.standfirst{font-size:clamp(17px,2vw,21px);color:var(--ink-soft);
  max-width:62ch;margin:0 0 8px;line-height:1.5}
.byline{font-family:var(--sans);font-size:12px;color:var(--muted);
  letter-spacing:.06em;text-transform:uppercase;margin:18px 0 0;
  border-top:1px solid var(--rule);padding-top:12px}

/* generic section */
section{margin-top:52px}
h2{font-family:var(--sans);font-size:12px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--red);margin:0 0 14px;font-weight:700}
h3{font-size:26px;font-weight:400;margin:0 0 10px;letter-spacing:-.01em}
p{max-width:66ch}
.lede{font-size:17px;color:var(--ink-soft)}

/* audit table */
.tablewrap{overflow-x:auto;border:1px solid var(--rule);background:var(--panel)}
table{border-collapse:collapse;width:100%;min-width:560px;
  font-family:var(--sans);font-size:14px}
th{ text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);font-weight:700;padding:11px 14px;
  border-bottom:1px solid var(--rule);white-space:nowrap}
td{padding:11px 14px;border-bottom:1px solid var(--rule);
  color:var(--ink-soft);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{font-family:var(--mono);text-align:right;
  font-variant-numeric:tabular-nums;color:var(--ink)}
.verdict{font-weight:700}
.cut{color:var(--red)}
.keep{color:var(--ink)}

/* act header */
.act{margin-top:56px;border-top:3px solid var(--ink);padding-top:12px}
.actrow{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.actname{font-size:23px;letter-spacing:-.01em}
.actclock{font-family:var(--mono);font-size:13px;color:var(--muted);
  font-variant-numeric:tabular-nums}

/* shots */
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
  gap:26px;margin-top:22px}
.shot{background:var(--panel);border:1px solid var(--rule);
  display:flex;flex-direction:column}
.thumb{position:relative;aspect-ratio:16/9;background:var(--tint);
  overflow:hidden;border-bottom:1px solid var(--rule)}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.tc{position:absolute;left:0;bottom:0;background:var(--red);color:#fff;
  font-family:var(--mono);font-size:12px;padding:3px 8px;
  font-variant-numeric:tabular-nums;letter-spacing:.02em}
.card-ph{display:flex;align-items:center;justify-content:center;
  height:100%;background:
   repeating-linear-gradient(135deg,var(--tint),var(--tint) 9px,
   transparent 9px,transparent 18px);
  font-family:var(--sans);font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--muted);text-align:center;padding:16px}
.meta{padding:14px 16px 16px;display:flex;flex-direction:column;gap:9px;
  flex:1}
.onscreen{font-size:16px;line-height:1.42;margin:0}
.src{font-family:var(--sans);font-size:11px;letter-spacing:.07em;
  text-transform:uppercase;color:var(--muted)}
.why{font-size:14px;color:var(--ink-soft);margin:0;padding-top:9px;
  border-top:1px solid var(--rule);line-height:1.5}
.why b{color:var(--ink);font-weight:700}

/* callout */
.callout{border-left:4px solid var(--red);background:var(--tint);
  padding:16px 20px;margin:22px 0}
.callout p{margin:0 0 8px}
.callout p:last-child{margin-bottom:0}
ul{max-width:66ch;padding-left:20px}
li{margin:6px 0}
.foot{margin-top:60px;border-top:1px solid var(--rule);padding-top:16px;
  font-family:var(--sans);font-size:12px;color:var(--muted)}
@media (max-width:640px){ .shots{grid-template-columns:1fr} }
"""


def esc(s):
    return html.escape(str(s), quote=False)


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

AUDIT = [
    ("Airrack — <em>My 600 Day Transformation Against MrBeast</em>", "38",
     "Another creator’s channel. His transformation, his coach, his "
     "bodybuilding contest.", "Cut to Jimmy-only windows", "cut"),
    ("Chris Hemsworth — <em>MrBeast Takes On My Workout Circuit</em>", "21",
     "Hemsworth’s gym, Hemsworth’s crew, burned-in “8 STATIONS” graphics. "
     "Jimmy is barely in frame.", "Dropped entirely", "cut"),
    ("MrBeast — own BTS / produced videos", "25",
     "His content, but wall-to-wall stunt graphics, location cards and "
     "overlays.", "Hand-picked windows only", "cut"),
    ("Joe Rogan · Diary of a CEO · Colin and Samir", "19",
     "Jimmy is the subject, speaking, unambiguously him.",
     "Promoted — carries the film", "keep"),
    ("MrBeast archive (first video, Hi Me In 5/10 Years, Minecraft)", "17",
     "His own uploads as a teenager. Two of the four were never used at "
     "all.", "Promoted — the spine", "keep"),
]


def render(shots, imgs) -> str:
    by_act = OrderedDict((a, []) for a in ACT_CLOCK)
    for key, act, tc, onscreen, src, why in shots:
        by_act.setdefault(act, []).append((key, tc, onscreen, src, why))

    rows = "\n".join(
        f'<tr><td>{src}</td><td class="num">{n}</td><td>{esc(note)}</td>'
        f'<td class="verdict {cls}">{esc(verdict)}</td></tr>'
        for src, n, note, verdict, cls in AUDIT)

    acts_html = []
    for act, clock in ACT_CLOCK.items():
        items = by_act.get(act) or []
        if not items:
            continue
        cards = []
        for key, tc, onscreen, src, why in items:
            if key in imgs:
                thumb = (f'<img src="{imgs[key]}" alt="{esc(onscreen)}">')
            else:
                thumb = (f'<div class="card-ph">Designed graphic<br>'
                         f'{esc(src)}</div>')
            cards.append(
                f'<figure class="shot">'
                f'<div class="thumb">{thumb}'
                f'<span class="tc">{esc(tc)}</span></div>'
                f'<figcaption class="meta">'
                f'<p class="onscreen">{esc(onscreen)}</p>'
                f'<span class="src">{esc(src)}</span>'
                f'<p class="why">{esc(why)}</p>'
                f'</figcaption></figure>')
        acts_html.append(
            f'<div class="act"><div class="actrow">'
            f'<span class="actname">{esc(act)}</span>'
            f'<span class="actclock">{esc(clock)}</span></div>'
            f'<div class="shots">{"".join(cards)}</div></div>')

    return f"""<style>{CSS}</style>
<div class="wrap">
<header class="mast">
  <div class="brandrow">
    <span class="brand">Celeb Workout</span>
    <span class="kicker">Storyboard · Version 7 · Picture rebuild</span>
  </div>
  <h1>The Disease That Built MrBeast</h1>
  <p class="standfirst">A shot-by-shot plan for the picture layer, built
  against the locked 12:26 audio master. Every frame below is a real grab
  from a source that will actually be used — not a description of one.</p>
  <p class="byline">Audio approved · Picture not yet built · Thumbnails are
  live frames</p>
</header>

<section>
  <h2>The problem, in one number</h2>
  <h3>Fifty-nine of 128 shots in the last cut were other people</h3>
  <p class="lede">You said the film does not have MrBeast in it. That was
  correct, and the plan file proves it. I chose sources by <em>topic</em> —
  “gym footage” — instead of by <em>subject</em>. Two other creators’
  videos supplied 46% of the picture while the three interviews where Jimmy
  is actually the subject supplied 15%.</p>
  <div class="tablewrap">
  <table>
    <thead><tr><th>Source</th><th>Shots</th><th>What it actually is</th>
    <th>Verdict</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
  <div class="callout">
    <p><b>On the Minecraft footage.</b> That is his own 2013 upload,
    <em>Worst Minecraft Saw Trap Ever???</em> — authentic early MrBeast.
    The problem was never the clip, it was the placement: it appeared under
    narration about his illness. Moved under the line about uploading to an
    audience of nobody, it becomes the point rather than an error.</p>
  </div>
</section>

<section>
  <h2>Rules this version is built on</h2>
  <ul>
    <li><b>Only Jimmy.</b> No shot ships unless he is in frame or it is a
    document, a diagram or a designed card. Every candidate window is
    face-checked before use.</li>
    <li><b>Footage must illustrate the sentence.</b> Shots are tagged by
    subject — early YouTube, baseball, illness, gym, food, sleep — and
    matched to what the narration is saying, not drawn from a rota.</li>
    <li><b>No other creator’s branding, captions or overlays.</b> Every
    window is OCR-checked; anything with burned-in text is rejected.</li>
    <li><b>Numbers get designed cards</b>, not stock footage under them.</li>
    <li><b>Clinical imagery is brief.</b> Two seconds, licensed, credited,
    and never implied to be Jimmy.</li>
    <li><b>Music-only moments get hand-picked hero shots</b>, never
    whatever came next in the queue.</li>
  </ul>
</section>

<section>
  <h2>The film, shot by shot</h2>
  {"".join(acts_html)}
</section>

<footer class="foot">
  Thumbnails are real frames from the downloaded sources. Medical
  illustrations: Wikimedia Commons (CC0 / CC BY 3.0 / CC BY 4.0) and
  NIH–NIDDK, each credited on screen. Clinical photograph: Wikimedia
  Commons, CC BY 4.0. Score: Scott Buckley, CC BY 4.0.
</footer>
</div>"""
