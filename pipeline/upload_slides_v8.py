#!/usr/bin/env python3
"""Upload the review deck to Google Drive as a real Google Slides file.

Uses the existing Slides+Drive pickle at
  XL Eagle/Tools and Dashboards/Pickle creation/tokens/token_slides_info_xleagle_com.pickle
made by that folder's own generate_slides_token.py for info@xleagle.com.

Uploading the .pptx with mimeType=application/vnd.google-apps.presentation
converts it server-side, so the images travel embedded inside the file. The
alternative - assembling the deck through the Slides API - needs a publicly
fetchable URL for every image, which would mean making 172 frames of an
unreleased film link-readable. This shares nothing: the deck lands in the
owner's own Drive, private, and is immediately commentable.

Re-running with the same TITLE updates the existing deck in place rather than
making a second copy, so review comments are not stranded on an old version.
"""

from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parents[1]
TOKEN = Path(r"C:\Users\avina\OneDrive\Desktop\Claude Projects\XL Eagle"
             r"\Tools and Dashboards\Pickle creation\tokens"
             r"\token_slides_info_xleagle_com.pickle")
DECK = ROOT / "final_video/MRBEAST_V8_SLIDESHOW.pptx"
TITLE = "MrBeast V8 — picture review (172 slides)"
SLIDES_MIME = "application/vnd.google-apps.presentation"
PPTX_MIME = ("application/vnd.openxmlformats-officedocument"
             ".presentationml.presentation")


def creds():
    with open(TOKEN, "rb") as fh:
        c = pickle.load(fh)
    if not c.valid:
        if not (c.expired and c.refresh_token):
            raise RuntimeError(
                f"{TOKEN.name} cannot refresh - re-run generate_slides_token.py")
        c.refresh(Request())
        with open(TOKEN, "wb") as fh:
            pickle.dump(c, fh)
        print("[auth] token refreshed")
    return c


def main() -> int:
    if not DECK.exists():
        raise FileNotFoundError(f"{DECK} - run pipeline/slides_deck_v8.py")
    drive = build("drive", "v3", credentials=creds(), cache_discovery=False)

    who = drive.about().get(fields="user(emailAddress)").execute()
    print(f"[auth] {who['user']['emailAddress']}")

    q = (f"name = '{TITLE}' and mimeType = '{SLIDES_MIME}' "
         f"and trashed = false")
    found = drive.files().list(q=q, fields="files(id,name)",
                               pageSize=5).execute().get("files", [])

    media = MediaFileUpload(str(DECK), mimetype=PPTX_MIME, resumable=True)
    if found:
        fid = found[0]["id"]
        print(f"[drive] updating existing deck {fid} in place")
        f = drive.files().update(
            fileId=fid, media_body=media,
            fields="id,name,webViewLink,modifiedTime").execute()
    else:
        print("[drive] creating new deck (converting pptx -> Slides)")
        f = drive.files().create(
            body={"name": TITLE, "mimeType": SLIDES_MIME}, media_body=media,
            fields="id,name,webViewLink,createdTime").execute()

    pres = build("slides", "v1", credentials=creds(), cache_discovery=False)
    n = len(pres.presentations().get(
        presentationId=f["id"], fields="slides/objectId"
    ).execute().get("slides", []))

    print(f"\n[OK] {f['name']}")
    print(f"     {n} slides")
    print(f"     {f['webViewLink']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
