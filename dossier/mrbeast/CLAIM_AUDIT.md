# MrBeast Documentary — Adversarial Claim Audit

Audit target: `THREE_COLUMN_SCRIPT_V1.md`, `RESEARCH.md`,
`manifest/mrbeast_soundbites.json`, locally stored captions and source metadata.

Audit posture: attempt to disprove or narrow every consequential claim. A
first-person statement proves that the speaker made the statement; it does not
independently prove a medical mechanism, a body-composition measurement, or a
causal interpretation.

## Verdict

**NOT READY FOR SCRIPT LOCK.**

- **PASS:** 15
- **WEAK:** 11
- **FAIL:** 3

The core biography is defensible if consistently attributed to Jimmy. The
medical guardrails are largely sound. Three corrections are mandatory:

1. Do not say the 310-day agreement "later expanded" into the 600-day
   challenge. The current evidence does not establish that chronology.
2. Do not state as fact that Jimmy lost substantial body fat *through* the
   complete five-part causal recipe in the ending. Several inputs and the
   magnitude of the result are self-reported, incompletely measured, or only
   indirectly documented.
3. Do not describe the initial 15-year-old archive as if illness timing,
   baseball status, upload date, and audience size are all verified in that
   exact image until the chosen upload is identified and dated.

## Claim-by-claim findings

### A. Medical

| Claim | Status | Exact evidence / attempted refutation | Required correction |
|---|---|---|---|
| Jimmy has Crohn's disease and says he was diagnosed at 15. | **PASS, with attribution** | DOACEO `FjrJ2DJN_pA`, 13:45–14:01 (`doaceo_weight_collapse`), and JRE `cLRLEnPaJLM`, approximately 86:38–86:48 (`jre_baseball_to_crohns`). Both are first-person accounts. No medical record is present, but none is reasonably required if phrased as his account. | On first mention use: **"Jimmy says he was diagnosed with Crohn's disease at 15."** Later references may be unqualified after attribution is established. |
| Crohn's is a chronic inflammatory bowel disease/disease causing digestive-tract inflammation. | **PASS** | NIDDK, *Crohn's Disease* and *Definition & Facts*, last reviewed July 2024: chronic disease causing inflammation in the digestive tract; Crohn's is an IBD. | Keep. Prefer the exact, simpler NIDDK wording over mechanistic shorthand. |
| Abnormal immune reactions play a role in Crohn's. | **PASS** | NIDDK says experts think genes, abnormal immune reactions, and the microbiome play a role. | Keep only as general medical context. |
| Jimmy's immune system/GI tract "attacks itself" or treats his gut as a foreign invader. | **WEAK as medicine; PASS as his quotation** | `doaceo_symptoms` and `jre_crohns_explanation` contain Jimmy's description. NIDDK's wording is more qualified: an abnormal immune reaction may attack bacteria that normally live in the intestines; experts are not certain of the cause. The soundbite's autoimmune explanation is an oversimplification. | Do not endorse the bite's mechanism in narration or graphics. Immediately follow it with: **"That is Jimmy's shorthand. NIDDK describes Crohn's as chronic digestive-tract inflammation in which genes, abnormal immune reactions, and the microbiome may all play a role."** |
| Crohn's severity/symptoms vary; symptoms can flare and enter remission. | **PASS** | NIDDK says symptoms vary from person to person; treatment aims to prevent flares and keep patients in remission. | Keep. |
| Jimmy went to the bathroom 8–10 times daily, did not digest food, and felt knife-like pain. | **PASS as first-person symptom report only** | DOACEO 15:18–15:48 (`doaceo_symptoms`, `doaceo_pain`). NIDDK supports diarrhea, abdominal pain/cramping, and weight loss as common symptoms, but not Jimmy's exact frequency or metaphor. | Retain the source voice. Narration must call these **his descriptions**, not clinical findings. |
| His treatment "shuts down" his immune system and causes him to get sick all the time. | **WEAK as medical fact; PASS as his account** | DOACEO 16:09–16:21 (`doaceo_treatment_burden`). NIDDK lists immunosuppressants and biologics, but the dossier does not identify his drug or establish complete immune shutdown or causation for every illness. | Never paraphrase this as a verified treatment mechanism. Introduce as: **"Jimmy describes his treatment this way…"** Do not put "immune system shut down" on an authoritative medical card. |
| Crohn's treatment is individualized. | **PASS** | NIDDK: no single treatment for every person; medicine depends on symptoms, inflammation location, and other factors. | Keep. |
| Crohn's nutrition needs can vary with symptoms, medicines, inflammation, surgery, and absorption. | **PASS, wording adjustment** | NIDDK eating/nutrition page: symptoms can reduce intake; small-intestine inflammation can reduce absorption; medicines and surgery can also affect absorption; recommended changes depend on symptoms and medicines. | Change **"Needs change with symptoms, medication, and absorption"** to **"Dietary needs can change with symptoms, medicines, and problems absorbing nutrients."** |
| No particular diet is known to cure IBD; this workout is not treatment advice. | **PASS** | Crohn's & Colitis Foundation source in research ledger; NIDDK says medicines and surgery do not cure Crohn's. | Keep. Strong and necessary guardrail. |
| Exercise may support health and strength but does not cure Crohn's. | **PASS in the limited form used** | The non-cure conclusion follows from authoritative treatment guidance; the general health/strength wording is modest. The dossier does not support any claim that exercise changed Jimmy's Crohn's course. | Keep. Never imply his fitness program induced remission or reduced Crohn's symptoms. |
| "Illness can still interrupt the plan without permission." | **WEAK / rhetorical** | Plausible general statement, but no specific interruption of Jimmy's workout plan is documented in the cited material. | Either retain explicitly as general risk (**"Crohn's can still interrupt a plan…"**) or support with a first-person example. Do not imply a documented interruption if none is shown. |

### B. Adolescent chronology and biography

| Claim | Status | Exact evidence / attempted refutation | Required correction |
|---|---|---|---|
| Jimmy went from about 190 lb to 139 lb and lost roughly 50 lb after becoming ill. | **PASS as first-person report** | DOACEO `doaceo_weight_collapse`: "like 190 pounds down to 139"; `doaceo_fifty_pounds`: "I lost 50 pounds." JRE independently contains "I lost like 50 pounds." Arithmetic yields 51 lb, explaining the rounded wording. No contemporaneous scale record exists. | Say **"Jimmy says he fell from about 190 pounds to 139—roughly 50 pounds."** Avoid presenting the values as independently measured facts. |
| He lost all his muscle. | **WEAK / subjective** | Jimmy says "I lost all muscle I had." No measurement exists, and literal total muscle loss is impossible. The script's "The muscle disappeared" risks literalizing a colloquial statement. | Change to **"He says the weight and muscle he had built for baseball disappeared."** |
| Crohn's ended baseball and led him to go all-in on YouTube. | **PASS as Jimmy's account; WEAK as exclusive causation** | `doaceo_weight_collapse`: "I'm not playing baseball in college anymore… just all in on YouTube." JRE: played baseball nonstop, then lost ~50 lb when he got Crohn's. This establishes his retrospective interpretation, not that Crohn's was the sole cause of his career. | Keep the causal chain attributed: **"In Jimmy's telling, that ended the college-baseball path and pushed him all-in on YouTube."** |
| At 15 he was still playing baseball, uploading, and had an audience small enough for a classroom, while his body had begun to turn against him. | **FAIL pending selected archive proof** | The interviews support age 15, baseball, illness, and YouTube generally. The dossier does not identify the exact opening upload, its recording date, diagnosis-relative timing, or its audience size at that moment. An upload date is not necessarily a recording date. | Do not record this narration until the chosen upload has: source ID, upload date, evidence of age/recording period, and contemporaneous subscriber/view evidence. Otherwise use: **"In the archive, Jimmy is a teenager—still talking about baseball and still uploading to a tiny audience. He later said he was diagnosed at 15."** Remove the classroom comparison unless quantified. |
| "YouTube absorbed the future that remained"; Crohn's changed the available terrain but did not cause his success. | **WEAK but responsibly framed interpretation** | Supported by Jimmy's "all in on YouTube" account, but the language is interpretive. The explicit "did not cause his success" disclaimer prevents the strongest causal overreach. | Keep the disclaimer. Prefer **"helped redirect his time and identity"** over **"the digital [path] absorbed almost everything"** unless the obsession quotes immediately support it. |
| The title, "The Disease That Built MrBeast," is literally established. | **WEAK / provocative thesis, not fact** | Available evidence supports redirection after illness, not that disease "built" the person or caused the business. The script itself concedes this in the ending. | Title may remain as a question-driving formulation only if the opening or early thesis explicitly complicates it: **"Crohn's did not create MrBeast. But Jimmy says it closed one path just as he went all-in on another."** Never repeat the title phrase as a factual conclusion. |

### C. Work, psychology, and motivation

| Claim | Status | Exact evidence / attempted refutation | Required correction |
|---|---|---|---|
| Jimmy obsessed over YouTube for a decade and sacrificed friendships/social fluency. | **PASS as first-person report** | JRE `jre_decade_of_obsession`, `jre_hyper_obsession`, and `jre_social_cost`. | Keep source voice; avoid diagnosing a psychiatric condition from "hyper-obsession." |
| He runs "one of the most controlled production machines on Earth" / is "the most productive creator alive." | **WEAK / superlative opinion** | No comparative data or definition establishes either ranking. The interviews support extreme operational focus, not a global superlative. | Remove **"the most productive creator alive."** Replace with **"one of YouTube's largest production operations"** only if scale evidence is shown, or simply **"a tightly controlled production operation."** |
| YouTube's measurable feedback rewarded the obsessive trait that made ordinary life difficult. | **WEAK / interpretation** | The JRE quotes support obsession, iteration, and social cost. They do not prove a single trait caused both success and difficulty. | Present as analysis, not fact: **"YouTube gave that obsession measurable feedback—and, by Jimmy's account, rewarded more of it."** |
| He "needed someone else" to make fitness consistent. | **WEAK / inference** | Jimmy says he called Eric, signed a pact, and they held each other accountable. This supports use of accountability, not psychological necessity. | Change **"needed someone else"** to **"chose to make someone else part of the system."** |
| The channel consumed too much of his health. | **WEAK / stronger than source** | `colin_why_he_started`: "I have not been working out or taking care of myself." It does not say the channel damaged his health or quantify consumption. | Use the source's narrower proposition: **"He realized his focus on the channel had left him not working out or taking care of himself."** |

### D. Contract and chronology

| Claim | Status | Exact evidence / attempted refutation | Required correction |
|---|---|---|---|
| Day 310 of a workout pact with Eric, tattoo penalty, with programmed rest days allowed. | **PASS as Jimmy's account** | Colin/Samir `9IQ_ldV9z_A`, published 2023-06-27, `colin_day_310_contract` at 12:11.96–12:34.60. Jimmy explicitly says day 310, contract, tattoo stakes, and programmed rest days. | Keep. Say **"day 310 of the pact"**, not "310 consecutive workouts." |
| "Every day" means following the program, including programmed rest. | **PASS** | Same soundbite. | Keep. This correction is important. |
| The tattoo applied if either person failed. | **PASS as broadly stated by Jimmy; details incomplete** | Jimmy says "if we didn't we'd get a tattoo of each other." Airrack later states that if *he* missed one day, he owed MrBeast's name tattooed on his forehead. The dossier does not contain the contract document or clearly establish symmetrical placement/terms. | Keep general stakes. Do not claim both faced identical forehead-tattoo terms without the document. |
| The contract was legally binding. | **WEAK / source assertion only** | Airrack says this in `airrack_contract_premise`; no contract is in the dossier and legal enforceability is not established. | Let Airrack say it in quotation. Narration/graphics should say **"a contract Airrack called legally binding."** |
| Eric is Eric Decker/Airrack. | **PASS with source identity context** | Airrack's channel/source and Jimmy's use of "Eric" align; Eric Decker is Airrack's public identity. The local film itself identifies the participants visually and contextually. | Identify once as **"Eric Decker, known as Airrack."** Include source/date lower third. |
| The agreement "later expanded into a longer transformation challenge." | **FAIL** | Colin/Samir (2023-06-27) establishes day 310 but does not state the intended endpoint. Airrack's 2024 film says he signed a 600-day agreement. These facts do not prove a later expansion; it may already have been a 600-day agreement whose duration Jimmy omitted in the 2023 answer. | Replace with: **"Jimmy described the pact on day 310 without naming its endpoint. In Airrack's later film, Eric described it as a 600-day bodybuilding challenge."** Do not use "expanded" or "evolved" absent further evidence. |
| The challenge lasted 602 days / involved working out every single day. | **WEAK literal wording; PASS as film-production/accountability claim** | `airrack_602_day_recap` says "602 days working out every single day"; the film later says it took 602 days to film. Jimmy had already clarified programmed rest days could count, so "602 consecutive workouts" would be false. | Say **"the project took 602 days to film"** or **"the pact ran across roughly 600 days, with programmed rest allowed."** Never say 602 consecutive training sessions. |
| Airrack documented trainers, travel, setbacks, and missed expectations. | **PASS for Airrack's journey; WEAK if applied equally to Jimmy** | The Airrack film captions document trainers, travel, changing plans, and disappointment, but most detailed footage follows Airrack. | Specify **"Airrack's film documents his side of the challenge…"** Do not imply every Airrack meal/workout/setback was Jimmy's. |

### E. Workout, movement, diet, and body composition

| Claim | Status | Exact evidence / attempted refutation | Required correction |
|---|---|---|---|
| Jimmy consistently resistance-trained under a coach. | **PASS at high level** | Colin/Samir establishes daily workouts/programmed rest; Airrack captions at 1:46–1:49 say "Jimmy already had a trainer"; the film shows weight training. It does not provide Jimmy's complete program. | Keep **"resistance training with a trainer/coach."** Do not name the coach or give a split until primary attribution is secured. |
| Jimmy has not publicly supplied a reliable complete split, set count, exercise list, meal plan, or calorie target in the acquired evidence. | **PASS as an evidence-bound statement** | Searches across acquired interview/Airrack captions do not yield a complete Jimmy-specific prescription. Detailed plans in the Airrack film primarily belong to Airrack. | Keep, but phrase **"In the sources we could verify…"** rather than claiming universal nonexistence across the entire internet. |
| Jimmy started at 41% body fat. | **WEAK as measurement; PASS as his statement** | Airrack 8:32–8:34 (`airrack_jimmy_41_percent`) contains Jimmy saying, on camera, "I started off at 41% body fat." No method, date, device, error margin, or record is supplied. | Display **"Jimmy's stated starting figure: 41%"**, not simply "41% body fat." Do not imply clinical precision. |
| He went from 40%+ to below 20% body fat. | **WEAK pending primary capture** | Contemporary secondary reporting quotes Jimmy's June 2023 posts saying "40%+… sub 20%," but the current dossier lacks the original/archived post. The dates/methods of either measurement are unknown. | Hold from narration and graphics until a defensible primary capture is archived. Even then say **"Jimmy reported…"**, with dates and no claim of measurement accuracy. |
| He walked 15,000 steps a day in June 2023 and took calls while walking. | **PASS as contemporaneous self-report** | Colin/Samir published 2023-06-27: `colin_daily_protocol` says 15,000 steps/day; `colin_two_hour_cost` says he took calls during the steps. | Keep with interview date and attribution: **"In June 2023, Jimmy said…"** |
| A separate transformation post said 12,500 steps/day. | **WEAK pending primary capture** | Multiple contemporary reports and preserved repost text quote the June 29, 2023 post, but the dossier does not hold the original post or a defensible archive capture. | Keep out of locked script unless the primary capture is archived. If unavailable, omit; 15,000 is enough and already verified. |
| The workout took roughly 90 minutes; the total cost was at least two hours including steps/food. | **PASS as June 2023 self-report, with nuance** | `colin_daily_protocol`: "an hour and a half every day, and then the food, and… 15,000 steps"; `colin_two_hour_cost`: "at least two hours of my day… doesn't [go to main channel]." The two-hour figure is total diverted time, not a measured sum allocated exclusively to bodily activity. | Say **"Jimmy estimated the workout at about 90 minutes and said the routine redirected at least two hours of his day from the main channel."** Do not graph 90 minutes + food/steps as a precise clock equation. |
| Food was managed as a verified pillar of Jimmy's protocol. | **WEAK** | Colin/Samir only says "and then the food" was time-consuming. Secondary reporting quotes "good diet." Airrack's detailed food monitoring applies mainly to Airrack. No Jimmy meal plan or calorie target is verified. | Rename card **"FOOD: DETAILS NOT PUBLIC"**. Narration: **"Jimmy counted food among the time costs and later publicly credited a good diet, but the acquired interviews do not reveal a reproducible plan."** Archive the primary post before using the latter clause. |
| Accountability and consistency were part of the system. | **PASS** | `colin_day_310_contract`, `colin_three_month_habit`, and Airrack film. | Keep. |
| Jimmy lost substantial body fat through lifting, movement, food management, coaching, and accountability. | **FAIL as presently worded** | Lifting, steps, a trainer, accountability, and self-reported body-fat change are separately supported to varying degrees. The evidence does not isolate causation, objectively measure "substantial," or establish "food management" with adequate detail. The sentence collapses self-report, observed behavior, and causal inference into a fact. | Replace with: **"Jimmy publicly credited his progress to months of lifting, high daily step counts, sleep, and diet; the interviews also document a trainer and an accountability pact. His exact measurements and complete program are not public."** Use only after archiving the relevant June 2023 posts. If not archived: **"The record shows sustained lifting, high daily step counts, a trainer, and an accountability pact; Jimmy says he lost fat, but the exact measurements and complete program are not public."** |
| Consistency produced progress, but much less than he expected. | **PASS as his assessment** | `airrack_jimmy_progress_reality`: Jimmy says he cannot believe how little progress he made and that their expectations were naive. | Keep as Jimmy's reflection. Do not turn it into a universal rate-of-change claim. |
| Fitness did not erase Crohn's or guarantee health. | **PASS** | No source says the disease was cured; authoritative medical sources say Crohn's has no cure and treatment aims at remission. | Keep. This is the correct payoff boundary. |

## Script corrections required before lock

### P0 — Must fix

1. **Opening archive composite claim**
   - Current: "Jimmy Donaldson is fifteen, still playing baseball, still
     uploading to an audience small enough to fit inside a classroom…"
   - Fix: verify the exact archive/date/audience or rewrite to separate the
     independently supported facts.

2. **600-day chronology**
   - Current: "The agreement later expanded into a longer transformation
     challenge."
   - Fix: "Jimmy described the pact on day 310 without naming its endpoint.
     In Airrack's later film, Eric described it as a 600-day bodybuilding
     challenge."

3. **Ending causal summary**
   - Current: "Jimmy lost substantial body fat through sustained lifting,
     high daily movement, food management, coaching, and accountability."
   - Fix with one of the evidence-bounded alternatives in the table above.

### P1 — Fix before narration record

4. Attribute the 190 → 139, 50 lb, symptom-frequency, pain, treatment, 41%,
   and body-fat-result claims to Jimmy.
5. Replace "the most productive creator alive."
6. Replace "needed someone else" with "chose to make someone else part of the
   system."
7. Replace "the channel had consumed too much of his health" with Jimmy's
   narrower statement that he had not been working out or taking care of
   himself.
8. Replace "The muscle disappeared" with a clearly attributed, nonliteral
   formulation.
9. Explain that Jimmy's "gut attacks itself" phrasing is his shorthand, not
   the film's clinical definition.
10. Do not show `12,500`, `sub-20%`, or the before/after post until the
    original or a defensible archive capture is stored.
11. Label `41%` as a stated figure and disclose that the measurement method is
    unknown.
12. Do not use "602 days working out every single day" in narration. Use the
    project duration and preserve the programmed-rest qualification.
13. Change the food card to acknowledge that the verified diet detail is
    insufficient for a reproducible plan.

### P2 — Evidence labeling / editorial hygiene

14. Distinguish clearly among:
    - **verified recording:** the person said it;
    - **self-reported metric:** no independent measurement;
    - **medical context:** authoritative general information;
    - **editorial inference:** the film's interpretation.
15. Put source name and publication date beside every changing numeric
    snapshot (`190`, `139`, `310`, `15,000`, `41%`, and any later metric).
16. Correct the JRE chronology in production notes if needed: the local
    PowerfulJRE metadata reports upload date `2024-06-27`, while episode
    number 1788 is commonly associated with an earlier release. Do not put a
    JRE date on screen until the original episode publication/re-upload history
    is resolved.

## Evidence inventory used

### Local primary audiovisual records

- `FjrJ2DJN_pA` — The Diary Of A CEO, uploaded 2025-02-20.
- `9IQ_ldV9z_A` — Colin and Samir, uploaded 2023-06-27.
- `cLRLEnPaJLM` — PowerfulJRE local upload metadata says 2024-06-27; original
  episode/re-upload chronology unresolved.
- `7r3ORKgNUjw` — Airrack, uploaded 2024-06-08.
- Corresponding local `.vtt` captions and `manifest/mrbeast_soundbites.json`.

### Authoritative medical context

- NIDDK, *Crohn's Disease*:
  https://www.niddk.nih.gov/health-information/digestive-diseases/crohns-disease
- NIDDK, *Treatment for Crohn's Disease*:
  https://www.niddk.nih.gov/health-information/digestive-diseases/crohns-disease/treatment
- NIDDK, *Eating, Diet, & Nutrition for Crohn's Disease*:
  https://www.niddk.nih.gov/health-information/digestive-diseases/crohns-disease/eating-diet-nutrition
- Crohn's & Colitis Foundation food guidance already listed in `RESEARCH.md`.

## Lock gate

The claim phase may be called complete only after:

- all P0 and P1 changes are reflected in the narration actually used by the
  radio edit;
- the chosen teenage opening source is dated and context-verified;
- the 600-day wording no longer invents an expansion chronology;
- unsupported social-post metrics are either archived as primary evidence or
  omitted;
- a second audit compares the rendered narration transcript—not merely the
  planning script—against this report.

