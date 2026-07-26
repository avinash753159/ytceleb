#!/usr/bin/env python3
"""v7_interludes.py - sentence-snap interlude windows with faster-whisper.

YouTube auto-captions carry no punctuation, so VTTs can't find sentence
boundaries. Instead: transcribe a padded region of each interlude source
with faster-whisper (punctuated output + word timestamps), then snap
t0 -> start of the sentence spoken at/just before the planned t0
t1 -> end of the last full sentence within +-6s of the planned t1
Drops an interlude only if no complete sentence fits the window.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
import json as _json
_cfg = _json.loads((ROOT / "config.json").read_text())
_CELEB_DIR = "statham" if _cfg.get("slug", "").startswith("jason") else "ryan"

PAD = 12.0


def transcribe(src, a, b):
    """Whisper the [a,b] slice of src; return [(t0,t1,word), ...] absolute."""
    wav = Path(tempfile.gettempdir()) / "intl_slice.wav"
    subprocess.run(["ffmpeg", "-ss", f"{a:.2f}", "-to", f"{b:.2f}",
                    "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                    "-y", str(wav)], capture_output=True, check=True)
    from faster_whisper import WhisperModel
    model = transcribe.model
    segs, _ = model.transcribe(str(wav), word_timestamps=True,
                               language="en")
    words = []
    for s in segs:
        for w in s.words or []:
            words.append((a + w.start, a + w.end, w.word.strip()))
    return words


def snap(words, t0, t1):
    """Sentence-snap [t0,t1] against punctuated whisper words."""
    ends = [i for i, (_, _, w) in enumerate(words)
            if re.search(r"[.!?]['\"]?$", w)]
    if not ends:
        return None
    # sentence starts = word after each sentence end (+ first word)
    starts = [0] + [i + 1 for i in ends if i + 1 < len(words)]
    # t0: latest sentence start at/before t0+1.5
    cand_s = [i for i in starts if words[i][0] <= t0 + 1.5]
    # t1: latest sentence end within [t1-8, t1+6]
    cand_e = [i for i in ends if t1 - 8 <= words[i][1] <= t1 + 6]
    if not cand_s or not cand_e:
        return None
    s_i, e_i = cand_s[-1], cand_e[-1]
    n0, n1 = max(words[s_i][0] - 0.25, 0), words[e_i][1] + 0.35
    if n1 - n0 < 6:
        return None
    return round(n0, 2), round(n1, 2), \
        " ".join(w for _, _, w in words[s_i:e_i + 1])


def main():
    from faster_whisper import WhisperModel
    transcribe.model = WhisperModel("base.en", compute_type="int8")
    inters = json.loads((MAN / "interludes.json").read_text())
    kept = []
    for it in inters:
        src = ROOT / "dossier" / _CELEB_DIR / f"{it['vid']}.mp4"
        if not src.exists():
            print(f"{it['id']}: SOURCE MISSING - dropped")
            continue
        words = transcribe(src, max(it["t0"] - PAD, 0), it["t1"] + PAD)
        r = snap(words, it["t0"], it["t1"])
        if not r:
            print(f"{it['id']}: no clean sentence window - DROPPED")
            continue
        n0, n1, text = r
        print(f"{it['id']}: {it['t0']}-{it['t1']} -> {n0}-{n1}")
        print(f"   \"{text[:110]}...\"" if len(text) > 110
              else f"   \"{text}\"")
        it["t0"], it["t1"] = n0, n1
        kept.append(it)
    json.dump(kept, open(MAN / "interludes.json", "w"), indent=1)
    # purge stale interlude segments so v6_assemble rebuilds them
    n = 0
    for f in (ROOT / "final_video" / "v6_work").glob("seg_*_zz_*.mp4"):
        f.unlink()
        n += 1
    for f in (ROOT / "final_video" / "v6_work").glob("lt_*.webm"):
        f.unlink()
        n += 1
    print(f"[OK] {len(kept)}/{len(inters)} interludes kept, "
          f"{n} stale artifacts purged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
