# Questions for the owner

Numbers and rulings the brief leaves open. Nothing below is defaulted in code: `owner.toml` holds what has been
ruled, and a missing key fails loud where it is needed. Each open question blocks only what it names.

## Open

1. **Question set: pick one** (no API call is made before you do). Loaded dry, no model calls:

   | | A. CrowdMillionaire (recommended) | B. Open Trivia DB |
   |---|---|---|
   | source, licence | github.com/bahadiri/Millionaire, MIT; cite Aydin, Yilmaz, Demirbas, *Concurrency Computat.* 2017, e4168 | opentdb.com, CC BY-SA 4.0 |
   | what it is | questions from the Turkish *Kim Milyoner Olmak İster?* live show, in Turkish | crowd-written trivia, English, not from the show |
   | size | 3,810 unique (live + practice, deduplicated; 6 with repeated options dropped) | 5,298 verified, including true/false; the four-option share was not counted |
   | four options, one right | yes (`choiceA`..`choiceD`, `correct_choice`) | yes, for `type=multiple` |
   | difficulty per question | the show's level, 1-12. Tiers: 1-4 easy, 5-8 medium, 9-12 hard: 1,853 / 1,464 / 499 | contributor-rated easy / medium / hard (1,770 / 2,424 / 1,104 counted with true/false) |
   | after the 200 + 100 split (seed 20260922) | play pools 1,549 / 1,163 / **198**: 500 games draw 2,500 hard questions, each reused about 13 times | not tried |
   | loader change | a converter from the two CSVs to the JSONL above (tried: it loads, splits and draws a game) | a converter from the API's JSON (HTML-decode; shuffle the right answer among the four with a seed) |

   Considered and rejected: the English WWTBM set (huggingface.co/datasets/WWTBM/wwtbm, CC BY-NC-SA 4.0), which is the
   US show's own questions but only 1,000, with 39 hard (533 / 428 / 39). It cannot fill 300 per tier.
   With A the instruments read Turkish. That is fine for calibration (the same questions calibrate and play), but it
   is a choice.

## Status: brief 002, as of 2026-09-25 (wald 0.1.0)

**Built** (`showcases/omniscience/`, def8698), against brief 002 as drafted:
- the loader, pinned to the public CSV's sha256; the seeded draw, and the calibration/test split stratified by domain
  (`questions.py`);
- the observations: the read with AA's prompt, the confidence call and its bucket, five agreement samples and the
  second opinion, each call logged at its declared price (`observe.py`);
- the grader, with AA's prompt verbatim and one call per distinct (question, answer) (`grader.py`);
- the fit, as the chain rule with Dirichlet(1) means, back-off, and the held-out score from `arena.calibration`, with
  the independence contrast (J2) (`fit.py`);
- the two-stage packs, generated for each (bucket, p, c), played with `wald.run`, and the exact oracle for the J1
  regret (`packs.py`);
- the four contestants and the paired Δ (`board.py`);
- the runner, whose wallet reserves every call before making it and holds across a resume (`run.py`);
- the scoreboard (`scoreboard.py`).

**Dry-run tested.** One end-to-end run: 294 questions, $2.90 declared, `claude-haiku-4-5-20251001` in all three
roles, self-graded, so degenerate (`SCOREBOARD.md`). It showed that every call is recorded and priced, every pack
passes `wald.load_pack` and is played by wald, and every contestant is scored from the same record. It showed
nothing about the fit. It also produced two findings, now in 2.5 and 2.7. The 23 test functions in
`tests/test_omniscience_*.py` use scripted transports:
- the chain-rule fit;
- the joint, never independent, second opinion;
- back-off;
- lawful packs, with the oracle ≥ wald;
- wald switching to the second answer;
- the budget and the resume;
- the guard against frozen models.

**Not built.** The brief names each of these; the list is complete:
- a Gemini transport (2.9a);
- recording the model name the response reports, for an alias (2.3);
- reasoning effort in the OpenAI transport (2.3);
- the seal. The brief keeps the test split sealed until the fit is committed, but the runner fits and plays in one
  pass;
- the SE recomputed from the fitted kernels before the test split opens (2.1);
- dollars per question by act on the scoreboard. Today it gives dollars by instrument.

**Open.** Every pre-registration item below, 2.1–2.14. None is ruled. Brief 002's re-plan on wald v0.2 (below it,
when written) supersedes the World and the calibration. It does not supersede the items about data, instruments,
penalties, baselines or claims.

## Pre-registration: brief 002 (rule before any call to gpt-6-astra, gpt-5.5 or claude-opus-5)

**BLOCKING.** No call to `gpt-6-astra`, `gpt-5.5` or `claude-opus-5` may be made, by any script in any session,
until every item below has a ruling under `## Ruled` naming this section. `showcases/omniscience/owner.toml`
carries no `[instruments.*]` until then. That absence, not this sentence, is what makes the block real: no code can
build an instrument the file does not name. The dry run's proposals live in `showcases/omniscience/dryrun.toml`
and are not rulings. Facts below were measured on 2026-09-23 and are cited in `briefs/002-omniscience.md`.

2.9 comes first, because the others are worth less if its answer is no.

- **2.9 Grader (`grader.*`) — load-bearing.** AA graded with `gemini-2.5-flash-preview-09-2025`, which is no longer
  served; AA runs no grading service. The published board therefore cannot be reproduced exactly, and any grader
  we choose measures a neighbouring metric. Options: (a) `gemini-2.5-flash` (GA, the same family; $0.30/$2.50;
  needs a Gemini transport, not yet built; key `GEMINI_API_KEY` is in the keyring) with AA's prompt verbatim;
  (b) another model with AA's prompt. Either way the board says "re-scored with <grader>, not AA's grader", and no
  row is compared with AA's published numbers as if it were theirs. Also rule: grader reasoning on or off, and
  whether a sample of grades is audited by hand. **Blocks:** every score.
- **2.1 Split (`split.*`).** Proposed: 300 calibration / 300 test, stratified 50/50 within each domain, seeded
  (2.14). The held-out score is 5-fold within calibration, so no third slice is spent. Worst-case standard errors
  for the test split, since per-question utility lies in [−p, 1]:

  | n_test | p | SE of a contestant's mean (≤) | SE of a paired difference (≤) |
  |---|---|---|---|
  | 300 | 1 | 0.058 (5.8 Index points) | 0.115 |
  | 300 | 3 | 0.115 | 0.231 |
  | 300 | 10 | 0.318 | 0.635 |
  | 200 | 1 / 3 / 10 | 0.071 / 0.141 / 0.389 | 0.141 / 0.283 / 0.778 |
  | 400 | 1 / 3 / 10 | 0.050 / 0.100 / 0.275 | 0.100 / 0.200 / 0.550 |

  These are bounds. A paired difference is driven only by the questions where two contestants act differently,
  so the real SE is smaller. It is recomputed from the fitted kernels before the test split is opened, and printed.
  At p = 10 even the bound says a 300-question test separates only large differences; AA itself says the public
  set is too small for domain-level claims. **Blocks:** the fit, the claims' power.
- **2.2 Data (`questions.*`).** `ArtificialAnalysis/AA-Omniscience-Public` at revision `e4883edb…` (2026-08-24),
  Apache-2.0, 600 rows, CSV sha256 `1e04603d…d02f`, 100 per domain. Confirm this revision is the board. **Blocks:**
  the loader's pin.
- **2.3 Primary instrument (`instruments.primary.*`).** `gpt-6-astra` is on the API, so the GPT-5.5 fallback is not
  needed. It is listed only as an alias; no dated snapshot is listed, so the model behind it can change mid-run.
  Rule: accept the alias and record the response's model field per call, or wait for a snapshot. Also rule
  reasoning effort and max output tokens. They are part of the instrument, and they set most of the cost (2.14).
  Key `OPENAI_API_KEY`. **Blocks:** any primary call.
- **2.4 Answer prompt.** AA's prompt verbatim with `{domain}`/`{subtopic}` (the README, which names real fields),
  not the paper's `{topic}`/`{category}`. Confirm. **Blocks:** the read.
- **2.5 Confidence (`confidence.*`).** Proposed: a second call after the answer ("You answered X to this question.
  How confident are you, 0–100?"), so the answer itself is elicited exactly as AA elicits it. The confidence is the
  reply's first line if that line is a lone whole number, and `unread` otherwise; Haiku, in the dry run, puts the
  number first and then explains. The cost is one extra primary call per question. The alternative is one call
  asking for answer and confidence together: cheaper, but the answer is no longer AA's. Buckets proposed: 0–49,
  50–79, 80–94, 95–100, plus `unread`. A declined read needs no bucket of its own: it is graded NOT_ATTEMPTED and
  scores 0 whichever act submits it. **Blocks:** the read, the bucket.
- **2.6 Agreement samples (`agreement.*`).** Five further calls with AA's prompt at the instrument's sampling
  settings. If `gpt-6-astra` rejects `temperature` (reasoning models may), samples vary only as the API varies them,
  and that is recorded. Price: the declared per-call price × 5, or a separately declared batch price. **Blocks:** the
  agreement act.
- **2.7 What "matches" means.** Proposed: normalised exact match (case, whitespace, punctuation, a leading
  article) between a sample and the read, and between the second opinion and the read. It is free and
  deterministic, but it calls "Paris" and "Paris, France" different. The dry run found a worse case: two declines
  worded differently ("I don't have reliable information…" / "I don't have enough information…") count as
  disagreeing, so a model that declines consistently shows k = 0. Declines are frequent (Haiku declined most of the
  smoke run's questions). The alternative is an equivalence judge call per pair (six per question, priced), or a
  judge that also says "this is a decline". **Blocks:** k and s.
- **2.8 Penalties (`penalties`).** p ∈ {1, 3, 10} as briefed. PARTIAL scores 0 at every p, as in the Index.
  Confirm both. **Blocks:** the packs.
- **2.10 Prices (`lambda_usd`, `second_price_grid`).** λ_usd, in utility per dollar. At λ_usd = 1 a right answer
  is worth $1, and real API prices are small against it. Second-opinion price grid, in utility: proposed
  {0, 0.05, 0.1, 0.25, 0.5, 1, 2, ∞}, where ∞ means no second opinion. "Near the stake" = {0.5, 1, 2}. The grid is a
  re-solve over the recorded second opinions, not further calls. The scoreboard's dollar columns use the real
  declared price. **Blocks:** the packs.
- **2.11 Fit (`fit.*`).** Beta(1,1) for binary cells, and one pseudo-count per outcome for multi-outcome kernels.
  Minimum cell count before backing off: proposed 10. Back-off order: bucket first, then k into {0–2, 3–4, 5}.
  **Blocks:** the fit.
- **2.12 Second opinion (`instruments.second.*`).** `claude-opus-5`, asked AA's prompt verbatim, graded like any
  answer. Its kernel is fitted from the joint table of both instruments' graded outcomes, never as its own
  accuracy multiplied by the primary's. Its declared price is the mean measured dollars per call, as for
  Millionaire. Key: `LLM_API_KEY` today, the Anthropic transport's default. Say whether it should become
  `ANTHROPIC_API_KEY` now that two providers run side by side. **Blocks:** any second-opinion call.
- **2.13 The pre-registered claims, verbatim, and how each is judged.** "wald ties the threshold at p = 1 without
  the second opinion, separates at p ≥ 3 and when the second opinion is priced near the stake, and beats the raw
  model throughout. A miss on any of these is a finding." Proposed tests use the paired per-question difference
  Δ on the test split, with SE as in 2.1:
  (i) *ties* at p = 1, c = ∞: |Δ(wald − threshold)| ≤ 2 SE;
  (ii) *separates at p ≥ 3*: Δ(wald − threshold) > 2 SE at p = 3 and at p = 10, with c = ∞;
  (iii) *separates near the stake*: Δ(wald − threshold) > 2 SE at some c in {0.5, 1, 2}, at every p;
  (iv) *beats the raw model throughout*: Δ(wald − raw) > 2 SE at every p and every c.
  A wald *below* a baseline beyond 2 SE is reported as that, not as a miss. **Blocks:** the verdict line.
- **2.14 Seeds and dollars (`split_seed`, `sampling_seed`, budget).** Seeds: proposed split 20260923, sampling 1.
  Whole run: 600 questions × (7 primary calls + 1 second opinion + 2 grades), since every observation is recorded
  on every question so that the price grid and every baseline read the same record:

  | primary | reasoning tokens per call | primary | second (`claude-opus-5`) | grader (`gemini-2.5-flash`) | total |
  |---|---|---|---|---|---|
  | `gpt-6-astra` | 0 | $7.98 | $0.57 | $3.01 | **$11.56** |
  | `gpt-6-astra` | 500 | $112.98 | $8.07 | $3.01 | **$124.06** |
  | `gpt-6-astra` | 2,000 | $427.98 | $30.57 | $3.01 | **$461.56** |
  | `gpt-5.5` | 0 / 500 / 2,000 | $4.20 / $67.20 / $256.20 | as above | $3.01 | $7.78 / $78.28 / $289.78 |

  This assumes 140 input tokens per answer call, 1,700 in and 800 out per grade, and list prices as of today. The
  dry run replaces the input-token assumptions with measured ones; reasoning tokens are the owner's ruling (2.3).
  Rule a budget ceiling; the runner refuses to start above it. **Blocks:** starting.

### Revision 2: brief 002 on wald 0.2 (2.15–2.24)

Brief 002's World and calibration are re-planned on wald 0.2.0. Items 2.1–2.10 and 2.12–2.14 stand as written
above; the World they feed is the one below. 2.11 (the Dirichlet fit) is withdrawn, replaced by 2.15 and 2.21. The
dry run (below the items) uses the proposals, labelled as proposals in `dryrun.toml`. Costs are measured on this
machine with wald 0.2.0.

- **2.15 The Globals' grids (`globals.*`) — load-bearing.** Each Global is a grid of named hypotheses. P(Global)
  is uniform over their product unless you rule otherwise, `elicited`.

  Proposed for the dry run:

  | Global | hypotheses |
  |---|---|
  | `calib` | ρ_b ∈ {1/10, 7/10} for each bucket: 2^|B| hypotheses |
  | `agree` | (a⁺, a⁻) ∈ {(4/5, 1/5), (1/2, 1/2)}: informative or not |
  | `second` | (σ, α, β) ∈ {(1/2, 4/5, 1/5), (1/10, 4/5, 1/2)}: a second opinion that rescues half the reads it doesn't share, or one that mostly shares the read's errors |
  | `grader` | γ ∈ {9/10, 1} |

  At four buckets that is 128 Global values and 2,560 states. wald is exact, so every value added multiplies the
  cost. Measured, with the load and declaration counted per pack, i.e. per (p, c):

  | ρ_b grid | Global values | states | load + declare | one episode, empty Counts | one episode, 140 records held | S15 |
  |---|---|---|---|---|---|---|
  | {1/10, 7/10} | 128 | 2,560 | 4 s | 0.3 s | 1.7 s | 2 s |
  | {1/10, 1/2, 9/10} | 648 | 12,960 | 79 s | 1.7 s | not measured | 12 s |

  Episodes slow as Counts grow, because the posterior is an exact rational: 144 calibration records gave a Score of
  38,000 digits. A truth that falls between grid points is found by E7 when no grid point reproduces its record
  law (C27). When one does, only S15 can show it. Rule the grid and the prior. **Blocks:** every pack.
- **2.16 Agreement's shape.** Proposed: the outcome is binary (all five samples match the read, or not), and its
  kernel reads `t` only. So, given whether the read is right, the samples are declared independent of the
  confidence bucket. The alternatives are three bins ({0–2, 3–4, 5}, as the first plan had) or a kernel that reads
  `b` too. Either multiplies the `agree` hypotheses. **Blocks:** the agreement act.
- **2.17 P(b), the bucket's own law.** Proposed: uniform, `elicited`. It never moves an act when wald takes
  `confidence` (free, and first), and it cannot be learned, since no Global governs it. Where wald skips
  `confidence`, the record sums over b under this uniform law. E7's `confidence` line will print the gap between
  uniform and the real bucket frequencies. That gap is a misdeclaration shown, not hidden. The alternative is a
  `bucket` Global on a grid. **Blocks:** the local prior.
- **2.18 PARTIAL and NOT_ATTEMPTED in the World.** A read graded PARTIAL or NOT_ATTEMPTED is `not` right. The World
  prices submitting it at −p, and the scoreboard at 0, as AA does. The error is one-sided: wald may abstain on a
  decline it could have submitted, and both realise 0. It never submits a decline expecting a gain. Confirm, or
  rule a fourth value of `t`. **Blocks:** the utilities.
- **2.19 A blind switch.** `answer_second` is a terminal. A World cannot make a terminal wait for an observation, so
  wald may fire it without `second_opinion`, and the World prices that at 0. The door then buys the second opinion
  and the scoreboard charges c. Proposed: accept, and print how often it happens and what it undercharged. The
  alternative puts −c in `answer_second`'s utility, which charges twice after a consult. **Blocks:** the terminals.
- **2.20 The plate's order (`plate_seed`).** What wald knows at question n depends on questions 1 to n − 1, so the
  test questions enter each plate in a seeded order, the same for every (p, c). Proposed: 20260925. **Blocks:**
  the test plates.
- **2.21 The calibration plate.** Proposed:
  - the calibration split is played once, under the test declaration's sibling: every observation priced 0, at
    p = 1 and c = 0, from the declared prior. Free observations do not guarantee all three are taken: wald buys
    only what can change its act;
  - its Counts are shipped, with their digest and Score, into every test pack at every (p, c);
  - the Score and digest come from the kit's reference, and wald recomputes both at declaration.

  Rule the sibling's p and prices, and whether one calibration plate serves every test plate. **Blocks:** the
  Counts.
- **2.22 "No second opinion" (c = none).** A declaration without `second_opinion` cannot condition on calibration
  records that use it (S13 refuses them PLATE). Proposed: drop `none` from 2.10's grid. The raw model and the
  threshold never buy a second opinion, and claim (i) of 2.13 is then tested at c = 2, the grid's top, with blind
  switches counted (2.19). The alternative is a second calibration plate declared without the act, for the `none`
  column. **Blocks:** 2.10's grid; claim (i).
- **2.23 Where E7 and the Score are computed.**
  - **E7 and the Score from the kit.** wald 0.2.0's eleven names give S15 (`Plate.disclosure()`), but not E7's
    lines or a Score for Counts a host writes. `wald.counts` has both, but it is not a host's to call (wald's
    API.md). Proposed: compute both with the kit's reference, `laws/counts_check.py`. The kit is fetched at the
    tag `wald.law` names (`kit-v0.12`) and verified against `arena/allowed_signers`, as wald's own cage does.
    wald recomputes the Score and digest at declaration, so the two implementations must agree.
  - **The 4,300-digit limit.** Python refuses integer literals over 4,300 digits by default, and a real Score is
    longer, so the runner lifts that limit (`sys.set_int_max_str_digits(0)`) before `load_pack`. Both points are
    worth raising with wald.

  **Blocks:** the scoreboard.
- **2.24 Compute, and the one-run maximiser.** The one-run maximiser of E7 (the exact plate value) is beyond the
  kit's size bound at this World's size, so the scoreboard says so and prints the realised values with and
  without Counts instead.

  At the proposed grid, 300 test episodes per plate take about 10 minutes once the Counts are large. With 2.10's
  grid less `none` (seven prices) at three penalties, that is 21 plates, about 3½ hours of CPU and no API spend.
  The dollar table of 2.14 stands: the baselines still need both answers graded on every question, and the
  After-act grades only answers already graded.

  Rule the grid knowing this, or rule fewer price points. **Blocks:** starting.

**Expected results, written before any spend** (for the frozen models, under the proposed numbers):
- **2.13's four claims stand as written.** Revision 2 changes how wald learns, not what it is claimed to do.
- **S15** discloses no class that settles an act for the proposed grid. Every Global is reached either by a graded
  end or by `s`, and the grader's γ is separated from ρ_b because an abstention's grade and an answer's grade read
  the same `t`.
- **E7's `confidence` line** prints the gap between the uniform P(b) and the real bucket frequencies (2.17). It is
  large, and it is not a reliability error.
- **E7's lines for the `grade` After-act** after `answer_primary`, and the plate's realised net with Counts
  against without, are the evidence that the Globals were learned. The line shrinks toward zero where some grid
  point lies near the truth, and holds at the distance to the nearest grid point where none does (C27).
- **Blind switches** (2.19) are rare at p ≥ 3: switching blind pays only when σ's hypothesis says the second
  opinion alone clears p/(1 + p).

## Ruled

- **Session 002 rulings:** λ_usd = 1. Models: contestant `claude-haiku-4-5`, friend `claude-sonnet-4-6`, audience = five
  independent `claude-haiku-4-5` samples at temperature 1, majority vote, calibrated as its own instrument. Price
  per call = the mean measured dollars per call in calibration, per instrument, a `data` cell with its count (no
  declared constant). Seeds: split 20260922, games 1. Unparseable replies: as proposed, their rate on the
  scoreboard, no retry. Phone and audience see the full question, never the reduced one; one calibration per
  instrument. Middle rungs confirmed. The direct-play prompt states the ladder, the lifelines held and the dollar
  cost of each call. Live calibration waits for the question-set pick and a dollar estimate for it and for 500 games.

- **2026-09-22, ladder:** the brief's ladder, not `proto.py`'s.
- **2026-09-22, prices:** phone and audience are charged their API cost × λ_usd plus their option value; 50:50 is
  free.
- **2026-09-22, the read:** the LLM read is the stage prior, taken at the start of every question and always paid;
  the stage menu is the three lifelines (`rulings.read_first`).
- **2026-09-22, the oracle plays:** the exact game is a fourth contestant, and the regret table goes on the
  scoreboard.

## Findings

### Why the per-question World is an approximation: lifelines are not additive

The per-question World (J1) prices each lifeline at its option value, V(r+1, L) − V(r+1, L∖{l}), and charges them
one at a time. That is exact only if lifelines are additive: if losing two costs the sum of losing each. They are
not. On the prototype's numbers at Q15:

| held on arrival at Q15 | V ($k) |
|---|---|
| none | 6,020.0 |
| phone | 6,020.0 |
| audience | 6,020.0 |
| phone + audience | 6,368.2 |
| fifty + phone + audience | 8,022.9 |

Phone and audience are **complements**. Each alone is worth nothing (V({phone}) = V({}) = $6,020k), but together
they are worth $348k, and with the 50:50 far more. So the sum of the individual option values (fifty 1,654.6 +
phone 322.5 + audience 234.0 = 2,211.1) exceeds the joint loss of all three (8,022.9 − 6,020.0 = 2,002.9). A stage
that would use several lifelines together is overcharged. At Q14, after the LLM reads A, the exact game calls the
audience and the approximation answers A.

This is the approximation's regret, measured by the oracle (`explainers/millionaire/oracle/game.py`, `regret_table`) at rung 1 with all
lifelines held:

| game | exact | wald estimate | wald realised | regret |
|---|---|---|---|---|
| prototype (proto's ladder and ρ, read on the menu), $k | 308.556 | 294.547 | 297.657 | 10.899 |
| brief ladder, read first, proto's illustrative ρ, $1/read, phone/audience free, $ | 38,110 | 36,507 | 37,050 | 1,060 |

The regret is positive at every rung but the last (where there is no future to misprice). It is the reason the
per-question World is an approximation and the oracle is carried alongside it: the scoreboard prints it on the
owner's fitted numbers.
