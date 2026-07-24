#!/usr/bin/env python3
"""
embed_index.py - Phase 3: persistent shot embedding index.

Tag once, store forever: every CLEAN shot (library/shots.jsonl) is embedded
with OpenCLIP (SigLIP text-image tower) from 3 mean-pooled keyframes and
stored in library/shots.db (sqlite + sqlite-vec if loadable, else a numpy
sidecar). Narration beats embed with the same model's text tower; cosine
similarity gives top-K candidates. The b-roll library becomes reusable
across celebrities - the next render costs zero tagging.

CLI:
  py -3.12 pipeline/embed_index.py --build
  py -3.12 pipeline/embed_index.py --query "man doing kettlebell swings" -k 8
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
DB = LIB / "shots.db"
NPY = LIB / "shots_emb.npy"
META = LIB / "shots_meta.json"

MODEL = os.environ.get("CLIP_MODEL", "ViT-B-16-SigLIP")
PRETRAIN = os.environ.get("CLIP_PRETRAIN", "webli")


def load_model():
    import open_clip
    import torch
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL, pretrained=PRETRAIN)
    tokenizer = open_clip.get_tokenizer(MODEL)
    model.eval()
    torch.set_num_threads(max(2, (os.cpu_count() or 8) - 2))
    return model, preprocess, tokenizer


def extract_frame(src, t, out):
    subprocess.run(
        ["ffmpeg", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
         "-vf", "scale=384:-2", "-q:v", "3", "-y", str(out)],
        capture_output=True, timeout=60)
    return out.exists()


def build():
    import numpy as np
    import torch
    from PIL import Image
    model, preprocess, _ = load_model()

    shots = [json.loads(l) for l in
             (LIB / "shots.jsonl").read_text(encoding="utf-8").splitlines()]
    clean = [s for s in shots if s["verdict"] == "clean"]
    print(f"[*] embedding {len(clean)} clean shots ({MODEL})")

    tmp = Path(tempfile.mkdtemp(prefix="emb_"))
    embs, meta = [], []
    with torch.no_grad():
        for i, s in enumerate(clean):
            ln = s["end"] - s["start"]
            frames = []
            for k, frac in enumerate((0.2, 0.5, 0.8)):
                f = tmp / f"f{k}.jpg"
                if extract_frame(s["src"], s["start"] + ln * frac, f):
                    try:
                        frames.append(preprocess(Image.open(f).convert("RGB")))
                    except Exception:
                        pass
            if not frames:
                continue
            feats = model.encode_image(torch.stack(frames))
            feats = feats / feats.norm(dim=-1, keepdim=True)
            v = feats.mean(0)
            v = v / v.norm()
            embs.append(v.cpu().numpy().astype("float32"))
            meta.append({"id": f"{s['source']}|{s['scene']}",
                         "src": s["src"], "source": s["source"],
                         "scene": s["scene"], "start": s["start"],
                         "end": s["end"], "dur": s["dur"]})
            if (i + 1) % 50 == 0:
                print(f"    [{i + 1}/{len(clean)}]", flush=True)

    arr = np.stack(embs)
    np.save(NPY, arr)
    META.write_text(json.dumps(meta), encoding="utf-8")

    # optional sqlite-vec mirror (portable single-file index)
    try:
        import sqlite3
        import sqlite_vec
        db = sqlite3.connect(DB)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.execute("DROP TABLE IF EXISTS shots_vec")
        db.execute(f"CREATE VIRTUAL TABLE shots_vec USING "
                   f"vec0(embedding float[{arr.shape[1]}])")
        db.execute("DROP TABLE IF EXISTS shots_meta")
        db.execute("CREATE TABLE shots_meta(rowid INTEGER PRIMARY KEY, "
                   "meta TEXT)")
        for rid, (v, m) in enumerate(zip(arr, meta), start=1):
            db.execute("INSERT INTO shots_vec(rowid, embedding) VALUES (?,?)",
                       (rid, v.tobytes()))
            db.execute("INSERT INTO shots_meta VALUES (?,?)",
                       (rid, json.dumps(m)))
        db.commit()
        db.close()
        print(f"[OK] sqlite-vec index: {DB}")
    except Exception as e:
        print(f"[i] sqlite-vec unavailable ({e}); numpy sidecar is primary")
    print(f"[OK] {NPY} {arr.shape}, {META.name} ({len(meta)} shots)")


def query(text, k):
    import numpy as np
    import torch
    model, _, tokenizer = load_model()
    with torch.no_grad():
        t = model.encode_text(tokenizer([text]))
        t = (t / t.norm(dim=-1, keepdim=True))[0].cpu().numpy()
    arr = np.load(NPY)
    meta = json.loads(META.read_text(encoding="utf-8"))
    sims = arr @ t
    top = np.argsort(-sims)[:k]
    return [{**meta[i], "score": round(float(sims[i]), 4)} for i in top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--query")
    ap.add_argument("-k", type=int, default=20)
    args = ap.parse_args()
    if args.build:
        build()
        return 0
    if args.query:
        for r in query(args.query, args.k):
            print(f"{r['score']:.3f}  {r['id']:40s} "
                  f"{r['start']:.1f}-{r['end']:.1f}s")
        return 0
    print("usage: --build | --query TEXT [-k N]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
