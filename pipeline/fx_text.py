#!/usr/bin/env python3
"""Type and source material composited with footage.

Three effects, all picked by the owner off real references, and all costing
nothing per shot: they composite material already on disk rather than
generating new material. That is a different economy from $0.04 a still or
$0.30 a generated clip, and for a documentary that lives on citing sources it
is worth more than another generated metaphor.

`source_highlight` exists to resolve a standing contradiction. The owner
rejected website imagery four separate times - "Again it's a website. I did
not want this" - while rule F5 requires that when a published source is the
spine of a claim, the film shows the actual page. Treating the page as a
photographed physical object rather than a screen capture satisfies both: the
focus falls off, the paper drifts, the letterforms fringe, and the eye reads
it as a document being examined instead of a browser window.

Every function honours the library contract: exactly `frames` frames at
1920x1080/24fps. The assembler refuses anything else.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "graphics/public/fonts/Anton-Regular.ttf"
FPS = 24
OUT_W, OUT_H = 1920, 1080
THREADS = "2"

# Channel red. ffmpeg will not accept a 3-digit hex, and neither will PIL
# reliably - always six digits.
ACCENT = (227, 18, 11)
ACCENT_LIME = (198, 255, 60)


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

def smoothstep(t: float) -> float:
    """Eased 0..1 with zero derivative at both ends.

    A linear ramp reads as mechanical; every move in this library is eased.
    """
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3.0 - 2.0 * t)


def _encode(frame_dir: Path, dest: Path, frames: int) -> Path:
    """Encode a PNG sequence, refusing to ship a short render.

    A gap in the sequence makes ffmpeg's image2 demuxer stop dead and produce
    a silently truncated file, so every frame is verified present first.
    """
    missing = [i for i in range(frames)
               if not (frame_dir / f"f{i:05d}.png").exists()]
    if missing:
        raise RuntimeError(
            f"{len(missing)} frame(s) missing, first is {missing[0]} - "
            "refusing to encode a short piece")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
         "-i", str(frame_dir / "f%05d.png"), "-frames:v", str(frames),
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-threads", THREADS, str(dest)], check=True)
    return dest


def _clip_frames(clip: Path, frames: int, work: Path) -> list[Path]:
    """Extract `frames` frames from a clip, looping the source if short.

    Looping is banned in the ASSEMBLER, where a repeated shot is a defect the
    viewer sees. Here the clip is only a texture inside a matte, so wrapping
    is invisible and preferable to failing.
    """
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(clip),
         "-vf", f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
                f"crop={OUT_W}:{OUT_H}",
         str(work / "c%05d.png")], check=True)
    got = sorted(work.glob("c*.png"))
    if not got:
        raise RuntimeError(f"no frames decoded from {clip}")
    return [got[i % len(got)] for i in range(frames)]


def _fit_font(text: str, target_w: int, max_size: int = 900) -> ImageFont.FreeTypeFont:
    """Largest Anton size whose text still fits `target_w`."""
    lo, hi = 20, max_size
    best = ImageFont.truetype(str(FONT), lo)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(str(FONT), mid)
        w = f.getbbox(text)[2] - f.getbbox(text)[0]
        if w <= target_w:
            best, lo = f, mid + 1
        else:
            hi = mid - 1
    return best


# --------------------------------------------------------------------------
# 1. text_matte - footage through the type
# --------------------------------------------------------------------------

def text_matte(clip: Path, dest: Path, lines: list[str], frames: int, *,
               fill: float = 0.88, drift: float = 0.02,
               bloom: float = 0.55, min_luma: float = 72.0,
               edge: int = 2, edge_strength: float = 0.5) -> Path:
    """Footage plays THROUGH the letters; everything outside is near-black.

    The type is a mask, not an overlay.

    `fill` is the fraction of frame width the widest line occupies AT THE END
    of the push. The first version set the type wider than the frame on
    purpose and then pushed in further, so the word was clipped at both edges
    and unreadable - a title has to be legible before it is dramatic. The
    fitting now accounts for the whole move, so the word is whole in every
    frame including the last.
    """
    work = Path(tempfile.mkdtemp(prefix="textmatte_"))
    try:
        src = _clip_frames(clip, frames, work / "src")
        fdir = work / "out"
        fdir.mkdir(parents=True, exist_ok=True)

        # One mask for all frames, built oversized so the push has somewhere
        # to travel. Text is fitted to `fill` of the FINAL frame width -
        # divided by the push - so the widest line is still whole at the end.
        pad = int(OUT_W * drift) + 4
        mw, mh = OUT_W + pad * 2, OUT_H + pad * 2
        target = int(OUT_W * fill / (1.0 + drift))
        mask = Image.new("L", (mw, mh), 0)
        md = ImageDraw.Draw(mask)
        fonts = [_fit_font(t, target) for t in lines]
        heights = [f.getbbox(t)[3] - f.getbbox(t)[1] for f, t in zip(fonts, lines)]
        gap = int(mh * 0.02)
        total = sum(heights) + gap * (len(lines) - 1)
        y = (mh - total) // 2
        for f, t, h in zip(fonts, lines, heights):
            bb = f.getbbox(t)
            md.text(((mw - (bb[2] - bb[0])) // 2 - bb[0], y - bb[1]), t,
                    font=f, fill=255)
            y += h + gap

        for i in range(frames):
            p = smoothstep(i / max(1, frames - 1))
            # Slow push on the mask so the type breathes rather than sitting.
            s = 1.0 + drift * p
            w2, h2 = int(mw * s), int(mh * s)
            m = mask.resize((w2, h2), Image.LANCZOS)
            left, top = (w2 - OUT_W) // 2, (h2 - OUT_H) // 2
            m = m.crop((left, top, left + OUT_W, top + OUT_H))

            base = Image.open(src[i]).convert("RGB")
            a = np.asarray(m, dtype=np.float32) / 255.0
            rgb = np.asarray(base, dtype=np.float32)

            # The matte reads only if the footage inside the glyphs is
            # brighter than the ground. Over a dark clip the letters go
            # black-on-black and the title disappears - measured on a night
            # aerial where mean luminance inside the type was under 40.
            inside = a > 0.5
            if inside.any():
                lum = float((rgb.mean(axis=2)[inside]).mean())
                if lum < min_luma:
                    # Lift toward the target rather than clipping to it, so
                    # the footage keeps its shape instead of blowing out.
                    rgb = np.clip(rgb * (min_luma / max(lum, 1.0)) ** 0.8,
                                  0, 255)

            out = rgb * a[..., None]

            if edge > 0:
                # Warm-white rim, per the brand guideline: only for
                # separation, never as decoration.
                ring = np.asarray(
                    m.filter(ImageFilter.MaxFilter(edge * 2 + 1)),
                    np.float32) / 255.0 - a
                ring = np.clip(ring, 0.0, 1.0)[..., None]
                out = out * (1 - ring) + np.array(
                    [244, 242, 239], np.float32) * ring * edge_strength

            if bloom > 0:
                glow = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
                glow = glow.filter(ImageFilter.GaussianBlur(28))
                out = np.clip(out + np.asarray(glow, np.float32) * bloom, 0, 255)
            Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(
                fdir / f"f{i:05d}.png")

        return _encode(fdir, dest, frames)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------
# 2. source_highlight - a page as a physical object
# --------------------------------------------------------------------------

def find_phrase(page: Path, phrase: str) -> tuple[float, float, float, float]:
    """Locate `phrase` on the page and return its box in PAGE pixels.

    The highlight must sit ON the words. Passing a hand-guessed rectangle
    does not work and is not close: the first version of this effect took
    fractions of the OUTPUT frame while the page was a different aspect
    entirely, so the mark landed in the gutter below the line and covered
    nothing. OCR removes the guess - you name the phrase, the page says
    where it is.

    Within a line, the phrase's horizontal extent is interpolated by
    character offset. Proportional type makes that approximate, but the box
    is snapped to the line's own top and bottom, so it can be a few pixels
    wide of the mark and never off the line.
    """
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    res, _ = ocr(str(page))
    if not res:
        raise RuntimeError(f"no text found on {page}")

    want = phrase.lower().strip()
    for box, text, _conf in res:
        line = str(text)
        pos = line.lower().find(want)
        if pos < 0:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        span = x1 - x0
        n = max(1, len(line))
        end = pos + len(want)
        # Run to the end of the word the phrase lands in, then take the word
        # after it. A marker swipe stops at a word boundary, never mid-glyph,
        # and a highlight that stops exactly on the last requested character
        # reads as clipped.
        while end < len(line) and line[end] not in " \t\n":
            end += 1
        nxt = end
        while nxt < len(line) and line[nxt] in " \t\n":
            nxt += 1
        while nxt < len(line) and line[nxt] not in " \t\n":
            nxt += 1
        end = nxt
        hx0 = x0 + span * (pos / n)
        hx1 = x0 + span * (end / n)
        pad = (y1 - y0) * 0.12
        return hx0 - pad * 0.4, y0 - pad, hx1 + pad * 0.4, y1 + pad

    found = " | ".join(str(t)[:40] for _b, t, _c in res[:6])
    raise ValueError(f"phrase {phrase!r} not found on {page.name}. "
                     f"Lines detected: {found}")


def source_highlight(page: Path, dest: Path, frames: int, *,
                     phrase: str | None = None,
                     rect: tuple[float, float, float, float] | None = None,
                     zoom: float = 1.18, drift_x: float = 0.012,
                     focus: float = 14.0, fringe: int = 2,
                     colour: tuple[int, int, int] = (214, 240, 92)) -> Path:
    """A document examined, not a screenshot pasted.

    Give it `phrase` and it OCRs the page, finds those words, highlights their
    real box, and centres the sharp band on that line so focus and mark agree.
    `rect` (page pixels) is the manual override for pages OCR cannot read.

    `fringe` adds chromatic aberration - a couple of pixels of red/blue offset
    that grows toward the frame edge. It is the single cheapest cue that the
    viewer is looking through a lens at a physical object.
    """
    work = Path(tempfile.mkdtemp(prefix="srchl_"))
    try:
        fdir = work / "out"
        fdir.mkdir(parents=True, exist_ok=True)
        src = Image.open(page).convert("RGB")

        # Over-scale so the drift never exposes an edge.
        big_w = int(OUT_W * zoom)
        big_h = int(src.height * (big_w / src.width))
        if big_h < int(OUT_H * zoom):
            big_h = int(OUT_H * zoom)
            big_w = int(src.width * (big_h / src.height))
        big = src.resize((big_w, big_h), Image.LANCZOS)
        sx, sy = big_w / src.width, big_h / src.height

        # Locate the words, then carry their box through every transform the
        # page undergoes. The sharp band follows the same line, so focus and
        # highlight can never disagree.
        hl = None
        if phrase:
            rect = find_phrase(page, phrase)
        if rect:
            hl = (rect[0] * sx, rect[1] * sy, rect[2] * sx, rect[3] * sy)
            centre_y = (hl[1] + hl[3]) / 2
            half = max(OUT_H * 0.06, (hl[3] - hl[1]) * 1.9)
        else:
            centre_y, half = big_h / 2, OUT_H * 0.07

        for i in range(frames):
            p = smoothstep(i / max(1, frames - 1))
            # Push in slightly and drift sideways across the shot.
            s = 1.0 + 0.05 * p
            w2, h2 = int(big_w * s), int(big_h * s)
            fr = big.resize((w2, h2), Image.LANCZOS)
            cx = (w2 - OUT_W) // 2 + int(OUT_W * drift_x * (p - 0.5))
            # Frame the highlighted line, not the middle of the page.
            cy = int(centre_y * s - OUT_H / 2)
            cx = max(0, min(cx, w2 - OUT_W))
            cy = max(0, min(cy, h2 - OUT_H))
            fr = fr.crop((cx, cy, cx + OUT_W, cy + OUT_H))

            # Highlight goes UNDER the blur, so it sits on the paper rather
            # than floating above it. Coordinates come from OCR and are
            # carried through the same scale and crop as the page itself.
            if hl:
                hx0, hy0, hx1, hy1 = (hl[0] * s - cx, hl[1] * s - cy,
                                      hl[2] * s - cx, hl[3] * s - cy)
                grow = smoothstep(min(1.0, i / max(1, frames * 0.33)))
                d = ImageDraw.Draw(fr, "RGBA")
                d.rectangle([hx0, hy0, hx0 + (hx1 - hx0) * grow, hy1],
                            fill=(*colour, 150))

            sharp = np.asarray(fr, np.float32)
            soft = np.asarray(fr.filter(ImageFilter.GaussianBlur(focus)),
                              np.float32)
            # Depth-of-field mask: sharp across the highlighted line, falling
            # off above and below. The crop centres that line, so the band is
            # centred too - focus and highlight cannot drift apart.
            hb = (half * s) / OUT_H
            y0, y1 = max(0.0, 0.5 - hb), min(1.0, 0.5 + hb)
            ys = np.linspace(0.0, 1.0, OUT_H, dtype=np.float32)
            dist = np.where(ys < y0, (y0 - ys) / max(y0, 1e-6),
                            np.where(ys > y1, (ys - y1) / max(1 - y1, 1e-6),
                                     0.0))
            m = np.clip(1.0 - dist ** 0.75, 0.0, 1.0)[:, None, None]
            out = sharp * m + soft * (1.0 - m)

            if fringe:
                # Offset red and blue outward; strength grows with radius.
                o = np.zeros_like(out)
                o[..., 0] = np.roll(out[..., 0], fringe, axis=1)
                o[..., 1] = out[..., 1]
                o[..., 2] = np.roll(out[..., 2], -fringe, axis=1)
                xs = np.abs(np.linspace(-1, 1, OUT_W, dtype=np.float32))[None, :, None]
                out = out * (1 - xs) + o * xs

            Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(
                fdir / f"f{i:05d}.png")
        return _encode(fdir, dest, frames)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------
# 3. headline_over - text in front, footage behind
# --------------------------------------------------------------------------

def headline_over(clip: Path, dest: Path, headline: str, frames: int, *,
                  byline: str = "", accent_words: tuple[int, ...] = (),
                  size: float = 0.048, darken: float = 0.42,
                  colour: tuple[int, int, int] = ACCENT_LIME) -> Path:
    """A quoted headline over live footage, words accented as they land.

    `accent_words` are word indices that switch to the accent colour, and they
    arrive in sequence across the shot rather than all at once - the film has
    word-level timings in manifest/words.json, so in production these come
    from the narration rather than being spread evenly.
    """
    work = Path(tempfile.mkdtemp(prefix="headline_"))
    try:
        src = _clip_frames(clip, frames, work / "src")
        fdir = work / "out"
        fdir.mkdir(parents=True, exist_ok=True)

        font = ImageFont.truetype(str(FONT), int(OUT_H * size))
        small = ImageFont.truetype(str(FONT), int(OUT_H * size * 0.34))
        words = headline.split()
        space = font.getbbox(" ")[2]
        max_w = int(OUT_W * 0.62)

        # Wrap once; layout is identical every frame so only colour changes.
        rows, row, rw = [], [], 0
        for idx, wd in enumerate(words):
            ww = font.getbbox(wd)[2] - font.getbbox(wd)[0]
            if row and rw + space + ww > max_w:
                rows.append(row); row, rw = [], 0
            row.append((idx, wd, ww)); rw += ww + (space if len(row) > 1 else 0)
        if row:
            rows.append(row)

        line_h = int(OUT_H * size * 1.24)
        block_h = line_h * len(rows) + (int(OUT_H * size * 0.6) if byline else 0)
        x0, y0 = int(OUT_W * 0.075), (OUT_H - block_h) // 2

        for i in range(frames):
            p = i / max(1, frames - 1)
            base = Image.open(src[i]).convert("RGB")

            # Darken only behind the text block, feathered.
            veil = Image.new("L", (OUT_W, OUT_H), 0)
            ImageDraw.Draw(veil).rectangle(
                [0, y0 - 60, int(OUT_W * 0.76), y0 + block_h + 60],
                fill=int(255 * darken))
            veil = veil.filter(ImageFilter.GaussianBlur(90))
            arr = np.asarray(base, np.float32) * (
                1.0 - np.asarray(veil, np.float32)[..., None] / 255.0)
            frame = Image.fromarray(arr.astype(np.uint8))

            d = ImageDraw.Draw(frame)
            y = y0
            for r in rows:
                x = x0
                for idx, wd, ww in r:
                    # Accent words arrive in order across the shot.
                    on = idx in accent_words and p >= (
                        (accent_words.index(idx) + 1) / (len(accent_words) + 1))
                    d.text((x, y), wd, font=font,
                           fill=colour if on else (245, 243, 240))
                    x += ww + space
                y += line_h
            if byline:
                d.text((x0, y + 6), byline, font=small, fill=(176, 170, 165))

            frame.save(fdir / f"f{i:05d}.png")
        return _encode(fdir, dest, frames)
    finally:
        shutil.rmtree(work, ignore_errors=True)
