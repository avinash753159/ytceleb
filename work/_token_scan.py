"""Report which stored OAuth pickle can write Drive/Slides.

Prints scopes, expiry and the verified account only. It never prints a token,
a refresh token or a client secret - the point is to pick the right credential,
not to move it anywhere.
"""
import glob
import os
import pickle
import sys

BASE = (r"C:\Users\avina\OneDrive\Desktop\Claude Projects\XL Eagle"
        r"\Tools and Dashboards\Pickle creation")
WANT = ("drive", "presentations")


def main() -> int:
    paths = sorted(set(
        glob.glob(os.path.join(BASE, "tokens", "*.pickle"))
        + glob.glob(os.path.join(BASE, "*.pickle"))
        + glob.glob(os.path.join(BASE, "gmail_credentials_package",
                                 "*.pickle"))))
    print(f"{len(paths)} pickles\n")
    hits = []
    for p in paths:
        try:
            with open(p, "rb") as fh:
                c = pickle.load(fh)
        except Exception as e:                                  # noqa: BLE001
            print(f"  {os.path.basename(p):46} unreadable: {type(e).__name__}")
            continue
        scopes = list(getattr(c, "scopes", None) or [])
        short = sorted({s.rsplit("/", 1)[-1] for s in scopes})
        useful = [w for w in WANT if any(w in s for s in scopes)]
        exp = getattr(c, "expiry", None)
        has_refresh = bool(getattr(c, "refresh_token", None))
        mark = "  <== " + "+".join(useful) if useful else ""
        print(f"  {os.path.basename(p):46} refresh={'y' if has_refresh else 'n'}"
              f" exp={exp} {','.join(short)[:70]}{mark}")
        if useful:
            hits.append((p, useful, has_refresh))
    print("\nCandidates that can write Drive and/or Slides:")
    for p, useful, r in hits:
        print(f"  {p}\n      scopes: {'+'.join(useful)}  refresh_token={r}")
    if not hits:
        print("  none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
