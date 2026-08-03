"""Merge the five-source fan-out into the allow-list and catalogue the rest.

The workflow's audit agents returned their verdicts as structured data rather
than writing the manifest themselves - deliberately, so five agents could not
race on one file. This does the merge, and it re-verifies rather than trusting:
every path must resolve and every duration is re-probed from the file, because
an earlier round shipped 14 entries as bare filenames that the builder silently
skipped and 11 rounded durations that let it seek past end-of-file.

Video groups go to manifest/broll_allow.json. The medical and primary-material
hauls are NOT stock groups - they are stills and documents - so they are
catalogued to manifest/research_assets.json for wiring into the plan by hand.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = Path(
    r"C:\Users\avina\.claude\projects"
    r"\C--Users-avina-OneDrive-Desktop-Claude-Projects-YouTube-CelebWorkout"
    r"\60a59a40-b54a-456e-8754-c8dac4a27f06\subagents\workflows"
    r"\wf_ea3e82f9-a1f\journal.jsonl")
ALLOW = ROOT / "manifest/broll_allow.json"
RESEARCH = ROOT / "manifest/research_assets.json"

# Groups the picture plan draws stock from. Anything else from the fan-out is
# research material (stills, documents), not b-roll.
VIDEO_GROUPS = {
    "training", "walk2", "walk", "editing", "night_work", "eating",
    "gut_pain", "tired", "athlete", "clinic", "bed", "desk", "clock",
    "meds", "iv", "food", "gym_room", "eq_barbell", "eq_dumbbell",
    "eq_machine", "bb_field", "bb_gear", "calendar",
}


def probe(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True,
        timeout=120).stdout.strip()
    try:
        return round(float(r), 2)
    except ValueError:
        return 0.0


def collect() -> list[dict]:
    """Every `kept` entry from every audit agent in the run."""
    out = []
    if not JOURNAL.exists():
        raise FileNotFoundError(JOURNAL)
    for line in JOURNAL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        val = rec.get("result") or rec.get("value") or rec
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                continue
        if isinstance(val, dict) and isinstance(val.get("kept"), list):
            for k in val["kept"]:
                if isinstance(k, dict) and k.get("file"):
                    out.append(k)
    return out


def main() -> int:
    kept = collect()
    print(f"{len(kept)} kept entries across the run\n")

    allow = json.loads(ALLOW.read_text(encoding="utf-8"))
    have = {Path(it["file"]).name for g in allow for it in allow[g]}

    added, research, missing, dupes = 0, [], [], 0
    for k in kept:
        rel = str(k["file"]).replace("\\", "/").lstrip("./")
        p = ROOT / rel
        if not p.exists():
            hits = list(ROOT.glob(f"**/{Path(rel).name}"))
            if hits:
                p = hits[0]
                rel = str(p.relative_to(ROOT)).replace("\\", "/")
            else:
                missing.append(rel)
                continue
        if p.name in have:
            dupes += 1
            continue
        group = (k.get("group") or "").strip()
        entry = {"file": rel, "duration": probe(p), "class": "OBJECT",
                 "crop": k.get("crop") or None,
                 "window": k.get("window") or None,
                 "note": (k.get("note") or "")[:400]}
        if group in VIDEO_GROUPS and p.suffix.lower() in (".mp4", ".mov",
                                                          ".webm"):
            if entry["duration"] < 1.0:
                missing.append(rel + " (unreadable duration)")
                continue
            allow.setdefault(group, []).append(entry)
            have.add(p.name)
            added += 1
        else:
            entry["group"] = group
            research.append(entry)

    ALLOW.write_text(json.dumps(allow, indent=2), encoding="utf-8")
    RESEARCH.write_text(json.dumps(research, indent=2), encoding="utf-8")

    print(f"merged into broll_allow.json : {added}")
    print(f"catalogued as research       : {len(research)}")
    print(f"already present (skipped)    : {dupes}")
    if missing:
        print(f"could not resolve            : {len(missing)}")
        for m in missing[:8]:
            print("   ", m)
    print("\nallow-list now:")
    print("  total", sum(len(v) for v in allow.values()))
    print("  " + ", ".join(f"{k} {len(v)}" for k, v in sorted(allow.items())))
    if research:
        from collections import Counter
        print("\nresearch assets by group:",
              dict(Counter(r["group"] for r in research)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
