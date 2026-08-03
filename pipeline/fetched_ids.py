#!/usr/bin/env python3
"""Every asset id this project has already downloaded.

An audit of 56 freshly fetched clips found 8 were re-downloads of Pexels ids
already cleared into manifest/broll_allow.json - identical footage, paid for
twice in audit time, and one of them would have put the same shot in the film
under two filenames. The fetchers were de-duplicating only against their own
run.

Call `known_ids()` before downloading anything and skip what comes back.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "manifest/broll_allow.json"
CREDIT_GLOBS = ["library/*/CREDITS.json", "dossier/mrbeast/*/CREDITS.json"]
_ID_IN_NAME = re.compile(r"_(\d{4,})\.\w+$")


def known_ids() -> set[int]:
    """Provider ids already downloaded, from every credits file AND from the
    filenames in the allow-list - because a clip can be present without its
    credits file surviving."""
    ids: set[int] = set()

    for pattern in CREDIT_GLOBS:
        for cf in ROOT.glob(pattern):
            try:
                rows = json.loads(cf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(rows, dict):
                rows = rows.get("clips", [])
            for r in rows if isinstance(rows, list) else []:
                if not isinstance(r, dict):
                    continue
                for key in ("pexels_id", "id", "provider_id"):
                    v = r.get(key)
                    if isinstance(v, int):
                        ids.add(v)
                    elif isinstance(v, str) and v.isdigit():
                        ids.add(int(v))
                m = _ID_IN_NAME.search(str(r.get("file") or ""))
                if m:
                    ids.add(int(m.group(1)))

    if ALLOW.exists():
        try:
            allow = json.loads(ALLOW.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            allow = {}
        for items in allow.values():
            for it in items:
                m = _ID_IN_NAME.search(str(it.get("file") or ""))
                if m:
                    ids.add(int(m.group(1)))

    return ids


if __name__ == "__main__":
    got = known_ids()
    print(f"{len(got)} asset ids already downloaded")
    print("sample:", sorted(got)[:12])
