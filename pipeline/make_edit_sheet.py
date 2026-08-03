#!/usr/bin/env python3
"""A Google Sheet the owner can edit: one row per shot, with the words.

Everything so far has been me describing the cut back to him. This inverts
it: every shot in programme order, the exact line spoken over it, what is on
screen now, and empty columns for what he wants instead.

Uploaded as CSV converted to a Google Sheet, which needs only the Drive scope
the existing token already has.
"""
import csv, io, json, pickle, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
TOKEN = Path(r"C:\Users\avina\OneDrive\Desktop\Claude Projects\XL Eagle"
             r"\Tools and Dashboards\Pickle creation\tokens"
             r"\token_slides_info_xleagle_com.pickle")
TITLE = "MrBeast V9 — shot list, tell me what you want"
CSV = ROOT / "work/MRBEAST_V9_EDIT.csv"


def words(edl, t):
    for s in edl["segs"]:
        if s["start"] <= t < s["end"]:
            txt = (s.get("text") or "").strip()
            if s["kind"] == "beat":
                return "[music only]", "BEAT"
            return txt, {"bite": "HIS VOICE", "narr": "NARRATION",
                         "card": "CARD"}.get(s["kind"], s["kind"])
    return "[lead-in / tail]", ""


def main() -> int:
    import mrbeast_picture_v9 as M
    from shot_prompts import PROMPTS
    edl = json.loads((ROOT / "manifest/edl_full.json").read_text(encoding="utf-8"))
    shots = M.allocate(edl, M.fx.probe_dur(M.AUDIO))

    rows = [["#", "start", "secs", "type", "what is on screen now",
             "the words spoken over it",
             "WHAT I WANT INSTEAD", "keep / replace / cut", "notes"]]
    for i, s in enumerate(shots):
        t = s["prog_start"]
        spec = s["spec"]
        kind = spec[0]
        if kind == "broll":
            now = f"stock, searched for segment {spec[1][1:]}"
        elif kind in ("sync",):
            now = "JIMMY - his lips on his own words"
        elif kind == "jimmy":
            now = "JIMMY - a verified window of him"
        elif kind in ("still", "clin"):
            now = f"licensed medical image ({spec[1]})"
        elif kind == "doc":
            now = f"real document / screenshot ({spec[1]})"
        else:
            now = f"{kind} {spec[1] if len(spec) > 1 else ''}"
        line, tag = words(edl, t + 0.05)
        try:
            seg_i = int(float(s["span"]))
        except (TypeError, ValueError):
            seg_i = None
        intent = PROMPTS.get(seg_i, "")
        if intent:
            intent = intent.split(". ")[0][:110]
        rows.append([
            f"{i:03d}", f"{int(t//60)}:{t%60:05.2f}", f"{s['dur']:.2f}",
            tag, now + (f"   [intended: {intent}]" if intent else ""),
            line, "", "", ""])

    CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"[csv] {CSV}  {len(rows)-1} shots")

    c = pickle.load(open(TOKEN, "rb"))
    if not c.valid and c.expired and c.refresh_token:
        from google.auth.transport.requests import Request
        c.refresh(Request())
        pickle.dump(c, open(TOKEN, "wb"))
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    drive = build("drive", "v3", credentials=c, cache_discovery=False)
    SHEET = "application/vnd.google-apps.spreadsheet"
    q = f"name = '{TITLE}' and mimeType = '{SHEET}' and trashed = false"
    found = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    media = MediaFileUpload(str(CSV), mimetype="text/csv", resumable=True)
    if found:
        f = drive.files().update(fileId=found[0]["id"], media_body=media,
                                 fields="id,webViewLink").execute()
        print("[drive] updated in place")
    else:
        f = drive.files().create(body={"name": TITLE, "mimeType": SHEET},
                                 media_body=media,
                                 fields="id,webViewLink").execute()
        print("[drive] created")
    print(f"\n[OK] {f['webViewLink']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
