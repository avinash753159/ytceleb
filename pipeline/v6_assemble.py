#!/usr/bin/env python3
"""v6_assemble.py - RYAN_REYNOLDS_V6: narration beats + interview interludes.

Every segment now CARRIES AUDIO:
  beat pieces  -> video piece muxed with its narration slice (from the VO)
  interludes   -> source video+audio cut, with a <LowerThird> label overlay
Then one concat of all segments (uniform re-encode), loudnorm at the end.

Also runs the global uniqueness pass: perceptual-hash sampling on every beat
piece; if a visual duplicates an earlier beat (non-outro), the beat is
flagged so the operator pass can swap it BEFORE final concat.

Run:  py -3.12 pipeline/v6_assemble.py [--check-only]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble  # noqa: E402
from v4_core import ahash, hamming  # noqa: E402

MAN = ROOT / "manifest"
import json as _json
_cfg = _json.loads((ROOT / "config.json").read_text())
_CELEB_DIR = "statham" if _cfg.get("slug", "").startswith("jason") else "ryan"

WORK = ROOT / "final_video" / "v5_work"
V6W = ROOT / "final_video" / "v6_work"
OUT = ROOT / "final_video"
FPS = 30


def run(cmd, timeout=1800):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(" ".join(map(str, cmd))[:160] + "\n"
                           + (r.stderr or "")[-300:])
    return r


def _whoosh():
    """Synthesized card-entrance whoosh - soft air sweep, not static."""
    f = V6W / "sfx_whoosh2.wav"
    if not f.exists():
        run(["ffmpeg", "-f", "lavfi",
             "-i", "anoisesrc=color=brown:duration=0.34:sample_rate=48000",
             "-af", "highpass=f=220,lowpass=f=1400,"
             "afade=t=in:d=0.08,afade=t=out:st=0.14:d=0.2,volume=0.5",
             "-y", str(f)])
    return f


def mux_beat(piece, t0, t1, vo, dest, sfx=False):
    """Beat piece + its narration slice -> audio-carrying segment.

    sfx=True (graphic cards) mixes a subtle whoosh under the entrance.
    """
    if sfx:
        # normalize=0 keeps narration at unity throughout - amix's default
        # renormalization DOUBLES the narration once the short whoosh ends
        # (V9 bug: every card beat clipped at 0dB)
        run(["ffmpeg", "-i", str(piece),
             "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(vo),
             "-i", str(_whoosh()),
             "-filter_complex",
             # force BOTH to stereo first: amix with mono whoosh + stereo
             # VO silently downmixes narration +3dB hot (V9 audio bug #2)
             "[1:a]aformat=channel_layouts=stereo[n];"
             "[2:a]volume=0.6,aformat=channel_layouts=stereo[w];"
             "[n][w]amix=inputs=2:duration=first:"
             "dropout_transition=0:normalize=0[a]",
             "-map", "0:v:0", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-shortest", "-y", str(dest)])
    else:
        run(["ffmpeg", "-i", str(piece),
             "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(vo),
             "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-shortest", "-y", str(dest)])
    return dest


def interlude_seg(it, dest):
    """Cut the interview WITH ITS AUDIO + burn the source lower-third.

    V7: windows are sentence-snapped upstream (v7_interludes.py); a 0.2s
    audio fade in/out keeps entries/exits clean even mid-breath.
    V9: J-cut - interview audio leads the picture by 0.4s (audio starts
    early over the tail of the previous beat's visual), pro-editor feel.
    """
    src = ROOT / "dossier" / _CELEB_DIR / f"{it['vid']}.mp4"
    dur = it["t1"] - it["t0"]
    jlead = 0.4
    webm = V6W / f"lt_{it['id']}.webm"
    if not webm.exists():
        assemble.WORK = WORK
        assemble.render_remotion(
            "LowerThird", {"title": it["label"], "sub": "INTERVIEW"},
            webm, min(dur, 4.5), alpha=True)
    vs = assemble._video_start(src)
    t0 = max(it["t0"], vs + 0.05)
    ta = max(t0 - jlead, vs + 0.05)   # audio input starts earlier (J-cut)
    cb = it.get("crop_box")
    pre = ""
    if cb and any(cb):
        l, tp, r, btm = cb
        pre = (f"crop=iw*{1 - l - r:.3f}:ih*{1 - tp - btm:.3f}:"
               f"iw*{l:.3f}:ih*{tp:.3f},")
    run(["ffmpeg", "-ss", f"{t0:.2f}", "-i", str(src),
         "-c:v", "libvpx", "-i", str(webm),
         "-ss", f"{ta:.2f}", "-i", str(src),
         "-t", f"{dur:.2f}",
         "-filter_complex",
         f"[0:v]{pre}scale=1920:1080:force_original_aspect_ratio=increase,"
         f"crop=1920:1080,fps={FPS}[b];[b][1:v]overlay=0:0:eof_action=pass;"
         f"[2:a]afade=t=in:d=0.2,afade=t=out:st={max(dur - 0.2, 0):.2f}"
         ":d=0.2[a]",
         "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-y", str(dest)])
    return dest


def callout_piece(piece, bid, co, dur):
    """Overlay an alpha-webm comp (callout/bug) onto a footage piece."""
    comp = co.get("comp", "ArrowCallout")
    props = co.get("props") if "props" in co else {
        "name": co.get("name", ""), "sub": co.get("sub", ""),
        "targetX": co.get("targetX", 0.5),
        "targetY": co.get("targetY", 0.3)}
    webm = V6W / f"co_{bid}.webm"
    if not webm.exists():
        assemble.WORK = WORK
        assemble.render_remotion(comp, props, webm, min(dur, 5.0),
                                 alpha=True)
    out = V6W / f"cop_{bid}.mp4"
    run(["ffmpeg", "-i", str(piece), "-c:v", "libvpx", "-i", str(webm),
         "-filter_complex", "[0:v][1:v]overlay=0:0:eof_action=pass",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", "-an", "-y", str(out)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    V6W.mkdir(parents=True, exist_ok=True)
    assets5 = json.loads((MAN / "assets_v5.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((MAN / "beats.json").read_text())["beats"]}
    inters = {it["after"]: it for it in
              json.loads((MAN / "interludes.json").read_text())}
    callouts = json.loads((MAN / "callouts.json").read_text()) \
        if (MAN / "callouts.json").exists() else {}
    if (MAN / "bugs.json").exists():
        callouts.update(json.loads((MAN / "bugs.json").read_text()))
    cfg = json.loads((ROOT / "config.json").read_text())
    vo = ROOT / f"voiceover_{cfg.get('slug', 'ryan_reynolds')}.mp3"
    order = sorted(assets5)

    # ---------- uniqueness pass (before assembling) -------------------
    seen = []          # (bid, hash)
    dupes = []
    for idx, bid in enumerate(order):
        piece = WORK / f"p_{idx:03d}_{bid}.mp4"
        if not piece.exists() or bid >= "b_095":     # outro callbacks exempt
            continue
        f = V6W / f"uh_{bid}.jpg"
        subprocess.run(["ffmpeg", "-ss", "1.0", "-i", str(piece),
                        "-frames:v", "1", "-vf", "scale=160:-2",
                        "-y", str(f)], capture_output=True, timeout=60)
        if not f.exists():
            continue
        h = ahash(f)
        for pb, ph in seen:
            if hamming(h, ph) <= 4:
                dupes.append((bid, pb))
                break
        seen.append((bid, h))
    if dupes:
        print("[UNIQUENESS] duplicate visuals found:")
        for a, b in dupes:
            print(f"   {a} duplicates {b}")
        (MAN / "v6_dupes.json").write_text(json.dumps(dupes))
        if args.check_only:
            return 1
    else:
        print("[UNIQUENESS] clean - no visual repeats")
        (MAN / "v6_dupes.json").write_text("[]")
    if args.check_only:
        return 0

    # ---------- build audio-carrying segments -------------------------
    segs = []
    for idx, bid in enumerate(order):
        piece = WORK / f"p_{idx:03d}_{bid}.mp4"
        if not piece.exists():
            raise SystemExit(f"missing piece for {bid}")
        b = beats[bid]
        seg = V6W / f"seg_{idx:03d}_{bid}.mp4"
        if not seg.exists():
            if bid in callouts:
                piece = callout_piece(piece, bid, callouts[bid],
                                      b["end"] - b["start"])
            mux_beat(piece, b["start"], b["end"], vo, seg,
                     sfx=assets5[bid].get("type") == "v5card")
        segs.append(seg)
        if bid in inters:
            it = inters[bid]
            iseg = V6W / f"seg_{idx:03d}_zz_{it['id']}.mp4"
            if not iseg.exists():
                interlude_seg(it, iseg)
            segs.append(iseg)
        if (idx + 1) % 20 == 0:
            print(f"  [{idx + 1}/{len(order)}] segments", flush=True)

    lst = V6W / "concat.txt"
    lst.write_text("\n".join(f"file '{s.absolute().as_posix()}'"
                             for s in segs), encoding="utf-8")
    merged = V6W / "v6_merged.mp4"
    run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-y", str(merged)], timeout=5400)
    import os as _os
    _suffix = _os.environ.get("BUILD_SUFFIX", "DRAFT")
    final = OUT / f"{cfg.get('slug', 'video').upper()}_{_suffix}.mp4"
    music = ROOT / "assets" / "music.mp3"
    src = merged
    if music.exists():
        # music bed at low level, sidechain-ducked under narration
        withmus = V6W / "v6_music.mp4"
        run(["ffmpeg", "-i", str(merged), "-stream_loop", "-1",
             "-i", str(music),
             "-filter_complex",
             "[1:a]volume=0.16[m];[m][0:a]sidechaincompress=threshold="
             "0.03:ratio=8:attack=80:release=600[duck];"
             "[0:a][duck]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-y", str(withmus)], timeout=3600)
        src = withmus
    # two-pass LINEAR loudnorm: single-pass is dynamic and pumps the gain
    # at loud->quiet transitions (audible dip entering clips after cards)
    r = subprocess.run(
        ["ffmpeg", "-i", str(src), "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
         "-f", "null", "-"], capture_output=True, text=True, timeout=3600)
    stats = json.loads(r.stderr[r.stderr.rfind("{"):
                                r.stderr.rfind("}") + 1])
    run(["ffmpeg", "-i", str(src), "-c:v", "copy",
         "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11:linear=true"
         f":measured_I={stats['input_i']}"
         f":measured_TP={stats['input_tp']}"
         f":measured_LRA={stats['input_lra']}"
         f":measured_thresh={stats['input_thresh']}",
         "-c:a", "aac", "-b:a", "192k", "-y", str(final)], timeout=3600)
    print(f"[OK] {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
