# MrBeast Documentary — Adversarial Claim Audit V2

Audit target: `THREE_COLUMN_SCRIPT_V2.md` against `CLAIM_AUDIT.md`,
`CLAIM_REPLACEMENTS.md`, `manifest/mrbeast_soundbites.json`, local captions,
metadata, and the existing verification contact sheet.

## Final re-audit verdict

Re-audit scope: current `THREE_COLUMN_SCRIPT_V2.md`,
`manifest/mrbeast_soundbites.json`, and
`manifest/mrbeast_radio_cutlist_v2.json`.

### Script text: **LOCK APPROVED**

All four prior V2 blockers are closed:

1. The misleading `airrack_602_day_recap` bite is removed from V2 and replaced
   with qualified narration:

   > Airrack says the project took six hundred and two days to film. The pact
   > ran across roughly six hundred days, with programmed rest allowed.

2. The 41% row is removed. The bank now correctly identifies
   `airrack_jimmy_41_percent` as Airrack speaking about himself, marks it
   `rejected_for_jimmy_claim`, and warns that it must never be attributed to
   Jimmy.
3. All five formerly pending source windows are now marked
   `transcript_and_frames_verified`.
4. "Tiny audience" is removed. The cutlist uses the evidence-safe line:

   > Before the giant sets, Jimmy played baseball and uploaded videos online.
   > He later said the diagnosis came at fifteen.

The current V2 script text is approved for narration lock.

### Current V2 radio cutlist: **FULL LOCK APPROVED**

Final recut checks:

- 58 segments
- total duration: `677.184s`
- hook duration: `89.424s`
- fitted timeline: pass
- duplicate source-window scan: none
- every used bite: `transcript_and_frames_verified`
- rejected 41% bite: absent
- misleading 602-day bite: absent
- qualified 602-day narration: present
- `12,500`, `sub-20%`, named coach, precise diet, and invented split: absent
- all cutlist narration matches the approved V2 copy; three initial automated
  string mismatches were confirmed to be PowerShell UTF-8/em-dash decoding
  artifacts, not wording differences

The previous duplicate `airrack_jimmy_progress_reality` blocker is closed. The
final cutlist uses the source once, in the reversal chapter, and contains no
duplicate bite windows.

**Final claim verdict: V2 script and V2 radio cutlist are fully locked.**

## Items that now pass

### Medical framing — PASS

- Diagnosis is attributed to Jimmy.
- His symptom and treatment descriptions remain source voice, not medical
  authority.
- The "attacking itself" explanation is explicitly labeled Jimmy's shorthand.
- NIDDK supplies the general definition and uncertainty.
- Diet wording correctly mentions symptoms, medicines, and nutrient
  absorption.
- The film explicitly says exercise is not a cure and the video is biography,
  not treatment advice.

### Weight and body composition — PASS, subject to Blocker 2

- `190 → 139` is labeled `JIMMY'S ACCOUNT`.
- The baseball/muscle/college-path chain is framed "in his telling."
- `41%` is designed as a stated figure with unknown method.
- Unsupported `12,500 steps`, `sub-20%`, and social before/after imagery are
  excluded.
- The ending now says Jimmy reports fat loss and acknowledges incomplete exact
  measurements.

### Workout and diet — PASS

- The verified protocol is limited to accountability, programmed resistance
  training, high daily movement, and protected time.
- No split, exercise list, sets, reps, meal plan, calorie target, or named
  coach is invented.
- The 15,000-step figure is dated and attributed.
- Ninety minutes and at least two hours are correctly separated.
- Airrack's diet/trainer details are explicitly kept separate from Jimmy's.
- The food card says the reproducible details are not public.

### Contract chronology — PASS, except Blocker 1

- Day 310 is correctly described as adherence to the pact, not 310 consecutive
  workouts.
- Programmed rest is preserved.
- Airrack's 2024 film is separated from Jimmy's 2023 interview.
- V2 explicitly says the record does not establish that the pact later
  expanded.
- "Legally binding" remains Airrack's quotation rather than an endorsed legal
  conclusion.

### Causality and rhetoric — PASS

- "The most productive creator alive" is removed.
- Accountability is framed as Jimmy's choice, not a psychological necessity.
- The script no longer says the channel "consumed his health."
- The title thesis is complicated twice: Crohn's did not create MrBeast.
- The ending gives agency rather than cure or biological control.

## Nonblocking cautions

These do not prevent a draft radio edit, but must be checked in the rendered
cut:

1. **"Move hundreds of people around a set"** should be paired with visual or
   production evidence showing that scale; otherwise remove "hundreds."
2. Keep `airrack_jimmy_progress_reality` unique; the final cutlist now uses it
   only once.
3. The JRE lower third must omit a date until original-release/re-upload
   chronology is resolved.
4. The end-screen bridge must remain absent until an actual next subject is
   selected.
5. Every numeric graphic must carry the promised source/date/self-report
   labeling in the rendered frame, not merely in this planning document.
6. The actual rendered narration transcript requires a final line-by-line
   audit; planning-text approval does not transfer automatically to alternate
   takes or improvised bridge copy.

## Strict lock checklist

Final lock requires **YES** to all:

- [x] The 602-day audio contradiction is removed or verbally corrected.
- [x] The 41% clip is omitted and its source-bank attribution corrected.
- [x] All five pending bite windows are frame-verified.
- [ ] Teenage archive source IDs and dates are recorded.
- [x] "Tiny audience" is removed.
- [ ] No upload date is presented as a recording date.
- [ ] JRE publication date is omitted or independently resolved.
- [x] No `12,500`, `sub-20%`, named coach, precise diet, or precise split has
      entered the script or graphics.
- [x] The duplicate full `airrack_jimmy_progress_reality` windows are removed;
      the source appears once.
- [ ] All number cards include source, date, and attribution.
- [ ] The final narration transcript matches the approved V2 wording.
- [ ] On-screen graphics preserve every qualification in speech.
- [ ] A final adversarial audit finds no newly introduced medical or causal
      claim.

## Final assessment

**FULL CLAIM LOCK APPROVED.** V2 script text and the 58-segment V2 radio cutlist
are clean. Runtime is `677.184s`, the hook is `89.424s`, all used bites are
transcript-and-frame verified, and no duplicate source windows remain.
Unchecked items above are downstream picture/render QA gates, not claim or
radio-lock defects.
