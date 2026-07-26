#!/usr/bin/env python3
"""v10_assemble.py - continuous-audio assembly (fixes the 113-joint audio).

OLD (v6): each beat = its own A/V segment; narration sliced per beat and
AAC-encoded 113 times -> encoder priming glitch at EVERY beat join.

NEW: video and audio are built separately and muxed ONCE.
  VIDEO: beat pieces trimmed to exact frame counts + interlude videos,
         one concat re-encode.
  AUDIO: the narration WAV plays CONTINUOUSLY per group (a group = run of
         beats between interludes; zero cuts inside), interlude audio
         inserted with 0.3s crossfades (J-cut feel), card whooshes overlaid
         at their timeline offsets, ONE final AAC encode + 2-pass linear
         loudnorm. 16 audio joins total instead of ~240.

Run: BUILD_SUFFIX=V2 py -3.12 pipeline/v10_assemble.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import assemble  # noqa: E402

MAN = ROOT / "manifest"
WORK = ROOT / "final_video" / "v5_work"
V6W = ROOT / "final_video" / "v6_work"
OUT = ROOT / "final_video"
FPS = 30
XFADE = 0.3


def run(cmd, timeout=3600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(" ".join(map(str, cmd))[:200] + "\n"
                           + (r.stderr or "")[-400:])
    return r


def probe_dur(f):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(f)], capture_output=True,
        text=True).stdout.strip())


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    _cd = "statham" if cfg.get("slug", "").startswith("jason") else "ryan"
    a5 = json.loads((MAN / "assets_v5.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((MAN / "beats.json").read_text())["beats"]}
    inters = {it["after"]: it for it in
              json.loads((MAN / "interludes.json").read_text())}
    bugs = json.loads((MAN / "bugs.json").read_text()) \
        if (MAN / "bugs.json").exists() else {}
    order = sorted(a5)
    vo = V6W / "vo_master.wav"

    AW = V6W / "aw"          # audio work
    AW.mkdir(parents=True, exist_ok=True)

    # ---------------- VIDEO: exact-frame beat videos + interludes --------
    vids = []                # (path, kind, meta)
    for idx, bid in enumerate(order):
        if a5[bid].get("type") == "spanned":
            if bid in inters:
                it = inters[bid]
                iseg = V6W / f"seg_{idx:03d}_zz_{it['id']}.mp4"
                if not iseg.exists() or iseg.stat().st_size < 10000:
                    raise SystemExit(f"missing interlude seg {it['id']}")
                vids.append((iseg, "interlude", (it,)))
            continue
        piece = WORK / f"p_{idx:03d}_{bid}.mp4"
        if not piece.exists():
            raise SystemExit(f"missing piece {bid}")
        b = beats[bid]
        if "span_until" in a5[bid]:
            nfr = round((beats[a5[bid]["span_until"]]["end"] -
                         b["start"]) * FPS)
        else:
            nfr = round((b["end"] - b["start"]) * FPS)
        vseg = V6W / f"v_{idx:03d}_{bid}.mp4"
        if not vseg.exists():
            vf = "fps=30"
            if bid in bugs:
                co = bugs[bid]
                webm = V6W / f"co_{bid}.webm"
                if not webm.exists():
                    assemble.WORK = WORK
                    assemble.render_remotion(
                        co["comp"], co.get("props", {}), webm,
                        min(nfr / FPS, 5.0), alpha=True)
                run(["ffmpeg", "-stream_loop", "-1", "-i", str(piece),
                     "-c:v", "libvpx", "-i", str(webm),
                     "-filter_complex",
                     f"[0:v]fps={FPS}[b];[b][1:v]overlay=0:0:"
                     "eof_action=pass",
                     "-frames:v", str(nfr), "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                     "-pix_fmt", "yuv420p", "-y", str(vseg)])
            else:
                run(["ffmpeg", "-stream_loop", "-1", "-i", str(piece),
                     "-vf", vf, "-frames:v", str(nfr), "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                     "-pix_fmt", "yuv420p", "-y", str(vseg)])
        vids.append((vseg, "beat", (bid, b)))
        if bid in inters:
            it = inters[bid]
            iseg = V6W / f"seg_{idx:03d}_zz_{it['id']}.mp4"   # has A+V
            if not iseg.exists() or iseg.stat().st_size < 10000:
                raise SystemExit(f"missing interlude seg {it['id']}")
            vids.append((iseg, "interlude", (it,)))
        if (idx + 1) % 25 == 0:
            print(f"  [video {idx + 1}/{len(order)}]", flush=True)

    lst = V6W / "concat_v10.txt"
    lst.write_text("\n".join(
        f"file '{Path(p).absolute().as_posix()}'" for p, _, _ in vids),
        encoding="utf-8")
    vtrack = V6W / "v10_video.mp4"
    run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
         "-y", str(vtrack)], timeout=7200)
    print("[OK] video track", flush=True)

    # ---------------- AUDIO: continuous narration + inserts --------------
    # groups of consecutive beats -> one uncut narration span each
    chunks = []              # audio files in order
    i = 0
    gi = 0
    while i < len(vids):
        p, kind, meta = vids[i]
        if kind == "beat":
            g0 = beats[meta[0]]["start"]
            j = i
            while j < len(vids) and vids[j][1] == "beat":
                j += 1
            last_bid = vids[j - 1][2][0]
            la = a5[last_bid]
            g1 = beats[la.get("span_until", last_bid)]["end"]
            f = AW / f"narr_{gi:02d}.wav"
            run(["ffmpeg", "-i", str(vo), "-af",
                 f"atrim=start={g0}:end={g1},asetpts=PTS-STARTPTS",
                 "-y", str(f)])
            chunks.append(f)
            gi += 1
            i = j
        else:
            it = meta[0]
            f = AW / f"intl_{it['id']}.wav"
            run(["ffmpeg", "-i", str(p), "-vn", "-ar", "48000", "-ac", "2",
                 "-y", str(f)])
            chunks.append(f)
            i += 1

    # crossfade-join the chain (audio joins only at interlude borders)
    cur = chunks[0]
    for k, nxt in enumerate(chunks[1:], 1):
        merged = AW / f"chain_{k:02d}.wav"
        run(["ffmpeg", "-i", str(cur), "-i", str(nxt),
             "-filter_complex",
             f"[0:a][1:a]acrossfade=d={XFADE}:c1=tri:c2=tri",
             "-y", str(merged)])
        if str(cur).startswith(str(AW)) and "chain_" in str(cur):
            Path(cur).unlink(missing_ok=True)   # keep disk flat
        cur = merged
    atrack = AW / "narration_chain.wav"
    Path(cur).replace(atrack)

    # whooshes at card starts (timeline offsets on the VIDEO timeline)
    t = 0.0
    delays = []
    for p, kind, meta in vids:
        if kind == "beat":
            bid, b = meta
            if a5[bid].get("type") == "v5card":
                delays.append(t)
            if "span_until" in a5[bid]:
                t += round((beats[a5[bid]["span_until"]]["end"] -
                            b["start"]) * FPS) / FPS
            else:
                t += round((b["end"] - b["start"]) * FPS) / FPS
        else:
            t += probe_dur(p)
    wh = V6W / "sfx_whoosh2.wav"
    if not wh.exists():
        run(["ffmpeg", "-f", "lavfi",
             "-i", "anoisesrc=color=brown:duration=0.34:sample_rate=48000",
             "-af", "highpass=f=220,lowpass=f=1400,afade=t=in:d=0.08,"
             "afade=t=out:st=0.14:d=0.2,volume=0.5", "-y", str(wh)])
    if delays:
        ins = ["-i", str(atrack)]
        fparts = []
        mix = "[0:a]"
        for k, dt in enumerate(delays):
            ins += ["-i", str(wh)]
            ms = int(dt * 1000)
            fparts.append(f"[{k+1}:a]volume=0.55,aformat=channel_layouts="
                          f"stereo,adelay={ms}|{ms}[w{k}]")
            mix += f"[w{k}]"
        fc = ";".join(fparts) + f";{mix}amix=inputs={len(delays)+1}:" \
             "duration=first:normalize=0[a]"
        awh = AW / "with_whooshes.wav"
        run(["ffmpeg", *ins, "-filter_complex", fc, "-map", "[a]",
             "-y", str(awh)])
        atrack = awh
    print("[OK] audio track", flush=True)

    # ---------------- MUX + 2-pass linear loudnorm ----------------------
    merged = V6W / "v10_merged.mp4"
    run(["ffmpeg", "-i", str(vtrack), "-i", str(atrack),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-y", str(merged)])
    r = subprocess.run(
        ["ffmpeg", "-i", str(merged), "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
         "-f", "null", "-"], capture_output=True, text=True, timeout=3600)
    stats = json.loads(r.stderr[r.stderr.rfind("{"):
                                r.stderr.rfind("}") + 1])
    suffix = os.environ.get("BUILD_SUFFIX", "V2")
    final = OUT / f"{cfg.get('slug', 'video').upper()}_{suffix}.mp4"
    run(["ffmpeg", "-i", str(merged), "-c:v", "copy", "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11:linear=true"
         f":measured_I={stats['input_i']}"
         f":measured_TP={stats['input_tp']}"
         f":measured_LRA={stats['input_lra']}"
         f":measured_thresh={stats['input_thresh']}",
         "-c:a", "aac", "-b:a", "192k", "-y", str(final)])
    print(f"[OK] {final} ({probe_dur(final):.1f}s, "
          f"{len(chunks)} audio chunks, {len(delays)} whooshes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
