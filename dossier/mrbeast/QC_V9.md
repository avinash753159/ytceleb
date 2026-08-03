# QC — THE_DISEASE_THAT_BUILT_MRBEAST_V9.mp4

- file size: 172.1 MB
- duration: 738.605s (12.31 min)
- locked audio: 738.606s
- **A/V delta: -0.001s** (hard gate 0.25s) — PASS
- shots: 165; longest 6.00s (rule 4 cap 6.0s) — PASS
- shortest shot: 1.20s
- mix: broll 104, jimmy 35, sync 10, doc 7, still 5, clin 2, flash 1, card 1

## Rule checks

| rule | check | result |
|---|---|---|
| 2 no reuse | builder registry raised no Reuse; non-stock assets drawn twice | none |
| 3 no looping | builder refuses a clip shorter than the slot | enforced at build |
| 4 shot <= 6s | longest slot | 6.00s |
| 5 no camera cut inside a window | uncut_window() at build time | build-time only, NOT re-verified post-render |
| 6 perceptual dedupe | dHash compare in builder | enforced at build |
| 7 eyes-on identity | 17 review sheets, 4 reviewers + 3 skeptics | done, see below |
| 9 no stand-in people | 335 clips individually verdicted | 197 passed, 138 rejected |
| 13 clinical short | CLIN_HOLD 2.2s in plan | enforced |

## Machine checks run against THIS file

- blackdetect: one stretch, 652.37-654.73s (2.37s). INTENTIONAL — segment 65 is written as a black frame with a shaft of light under "So — did the disease build MrBeast?"
- freezedetect: none
- EBU R128: integrated -14.1 LUFS, true peak -1.1 dBFS, LRA 9.6 LU — inside YouTube's -14 LUFS target, no clipping

## Known remaining defects

- 8 shots borrow footage from a neighbouring sentence (s66, s67, s68, s72, s73, s16, s21, s39, s55) — listed by the build as `[degraded]`
- ~30 shots judged 'weak' by reviewers: generic-but-defensible stock, some near-duplicate pairs
- rule 5 is guaranteed at build time only; there is no post-render scene-cut audit
- HANDOFF section 7 open items 2,3,4,6,7 are untouched by this pass (they concern Jimmy footage and graphics, not stock)
