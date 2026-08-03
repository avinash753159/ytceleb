"""Fix the residual quote damage from the previous over-eager catch-all."""
from pathlib import Path

p = Path("pipeline/storyboard3.py")
s = p.read_text(encoding="utf-8", errors="replace")

# The earlier catch-all matched the 2-char prefix before the 3-char
# sequences, leaving a stray marker after each converted quote.
FIX = {
    "”œ": "“",          # was left double quote
    "”": "”",     # was right double quote
    "”\x9d": "”",
}
n = 0
for bad, good in FIX.items():
    n += s.count(bad)
    s = s.replace(bad, good)

p.write_text(s, encoding="utf-8")
odd = [c for c in set(s) if ord(c) in (0x9d, 0x9c, 0x8c)]
print(f"fixed {n}")
print(f"stray control chars remaining: {odd}")
print(f"left quotes: {s.count(chr(0x201c))}  right quotes: {s.count(chr(0x201d))}")
