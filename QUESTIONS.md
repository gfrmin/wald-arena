# Questions for the owner

Numbers and rulings the brief leaves open. Nothing below is defaulted in code: `owner.toml` holds what has been
ruled, and a missing key fails loud where it is needed. Each open question blocks only what it names.

## Open

1. **Question set** (Millionaire): moot. Millionaire's live play is dropped (ruled 2026-09-25); the table that
   stood here is in git history.

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

**Revision 2, built and dry-run (2026-09-25, wald 0.2.0).** `world.py` generates the v0.2 pack. `board.py` holds
the Door and the baselines. `run.py` plays the calibration plate, ships its Counts, and plays one test plate per
(p, c) with `Plate.run`. `arena/kit.py` gives E7 and the Score from the verified kit. The two-stage packs and the
Dirichlet fit are removed.

The dry run replayed the recorded Haiku answers above (`--replay`, which refuses any call), so it made no API call
and spent nothing:
- the calibration plate took 186 s for 144 episodes and wrote 20 distinct records;
- each of the six test plates (p ∈ {1, 3, 10} × c ∈ {1/10, 1}) took 807–879 s for 150 questions, six in parallel
  on 8 cores, the declared-prior replay included;
- every pack shipping the Counts passed `wald.load_pack` and `wald.declare`, with wald recomputing the kit's Score
  and digest;
- the Counts moved the prior: `calib` from uniform to 0.65 on ρ = (1/10, 7/10, 7/10, 1/10), `agree` to the
  informative hypothesis, and `grader` to γ = 9/10. The first test question's acts differ with the Counts and
  without;
- S15: no class, at every plate. E7's lines run to 0.88 on a two-point grid, which cannot hold Haiku's rates. Its
  `confidence` line, 0.41, is 2.17's uniform P(b);
- 12 blind switches at p = 1, c = 1/10 (2.19).

`showcases/omniscience/SCOREBOARD.md` has the rest, including one finding: at p ≥ 3 wald realised less with the
Counts than from the declared prior, which abstains at once. The committed scoreboard is from the dry run before a review's
two fixes: its *realised, with Counts* column did not yet charge c for a blind switch. At p = 1 it overstates by
about 0.008 (c = 1/10, 12 switches) and 0.013 (c = 1, 2 switches), and the declared-prior column's blind switches were
not counted. The re-run with the fixes was stopped for low memory on this machine and has not been repeated:
`python -m showcases.omniscience.run --dry-run --budget-usd 3 --replay` (about 18 minutes, no API call) regenerates
it.

## Pre-registration: brief 002 (rule before any call to gpt-6-astra, gpt-5.5 or claude-opus-5-5)

**BLOCKING.** No call to `gpt-6-astra`, `gpt-5.5` or `claude-opus-5-5` (or `claude-opus-5`) may be made, by any script in any session,
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

### After the rulings of 2026-09-25

**Models, as listed** (`GET /v1/models` at each provider, 2026-09-25T14:39Z, no completion made):

| role | string | as listed |
|---|---|---|
| primary | `gpt-6-astra` | listed, created 2026-08-27; still an alias, with no dated snapshot. Two siblings are new since 2026-09-23: `gpt-6-luna` and `gpt-6-sol`, both created 2026-09-14 |
| primary, fallback | `gpt-5.5-2026-04-23` | a dated snapshot, listed beside the alias `gpt-5.5` |
| second opinion | `claude-opus-5-5` | listed, created 2026-09-21. It replaces `claude-opus-5`, which is still listed (created 2026-07-24) |
| grader, if 2.9 rules (a) | `gemini-2.5-flash` | listed, version 001 ("stable") |

`claude-opus-5-5` cannot turn thinking off. Its reasoning effort (default `medium`) is part of the instrument and
is not ruled (2.12, below). Its list price is $4 / $20 per million tokens, from Anthropic's price table as cached
on 2026-06-24.

**How the calibration ends are chosen (2.21, my reading, for you to confirm).** "Chosen for what its grade teaches"
could be read as choosing each end by the question's grades. That would bias the Counts. The record keeps only the
chosen end's grade, and the likelihood treats the end as a design choice. If the end depended on the other,
unrecorded grade (say, grading the second opinion only when the read was wrong), the Counts would over-represent
right reads among graded reads, and ρ would be learned too high. So the end reads only what the record shows:
- the read, when the two answers match, since one grade then teaches both;
- when they differ, the records alternate in question order between grading the read and grading the second
  opinion.

On the dry run's 144 calibration questions that gave 17 distinct records. The code is `run.calibration_end`.

**Measured at the ruled grid** (two buckets, 4² × 2 × 2 × 2 = 128 Global values, 1,280 states), on the dry run's
calibration questions only, so no test question was played:

| what | cost |
|---|---|
| a pack without Counts: generate, then load and declare | 0.05 s + 1.4 s (1.1 MB) |
| the kit's Score and digest of the 144 constructed records | 3.0 s; the Score has 80,623 digits |
| a pack shipping the Counts: load and declare, wald recomputing the Score | 11.5 s |
| one episode from the declared prior | 0.18 s |
| episodes from the 144 shipped records | 1.9 s at the first, 2.9 s after 144 more; 343 s for 144 |
| S15; E7 over 288 records | 1.4 s; 1.4 s |

Extrapolated, not measured, for 300 calibration and 300 test questions: about 3–5 s an episode, so about 20
minutes a plate, or 7 hours of CPU for 21 plates. That is 2–3 hours on three cores, which is what this machine's
memory allows. It ran out of memory with six plates in parallel on 2026-09-25.

**The gate stops the dry run.** Haiku's calibration confidences, by tens: 0–9: 2, 10–19: 42, 20–29: 51, 30–39: 1,
40–79: 10 (all 70–79), 80–89: 12, 90–100: 6, unread: 20. With the cut at 80 and unread in b0, b1 holds 18 of 144
(12.5%), under a fifth. So the dry run on constructed Counts has not played a test question. Haiku is not the
frozen primary, whose histogram will differ, but the gate applies to it as ruled. For the dry run, a cut at 70
gives b1 28 of 144 (19.4%), still under a fifth. A cut at 30 gives 29 of 144 (20.1%). Moving unread to b1 with
the cut at 80 gives 38 of 144 (26.4%).

Ruled 2026-09-27: the gate is waived for this Haiku dry run only (`dryrun.toml`'s `confidence.gate = "waived"`),
and the dry-run scoreboard says so. It stands for the real run: `owner.toml` says `gate = "stands"`, and the runner
refuses `waived` outside `--dry-run` before any call.

**The dollar estimate.** 600 questions, each with 7 primary calls, 1 second-opinion call and at most 2 grades.
Input tokens are the dry run's measured means: an answer 130, a confidence call 150, a grade 1,658. Visible
output is 51 tokens an answer, as measured (Haiku explains its answer; a frozen model may write less). R is the
reasoning tokens per primary and second-opinion call, which 2.3 and 2.12 set. The grader is `gemini-2.5-flash` with
800 output tokens a grade, as 2.14 assumed. Prices: OpenAI and Google as listed on 2026-09-23 (brief 002),
Anthropic as above.

| primary | R = 0 | R = 500 | R = 2,000 |
|---|---|---|---|
| `gpt-6-astra` ($10 / $50) | $16.20 + $0.92 + $3.00 = **$20.12** | $121.20 + $6.92 + $3.00 = **$131.12** | $436.20 + $24.92 + $3.00 = **$464.12** |
| `gpt-5.5-2026-04-23` ($5 / $30) | **$13.08** | **$82.08** | **$289.08** |

Each total is primary + second opinion (`claude-opus-5-5`) + grader.

**Still open, blocking any frozen-model call:**
- 2.1: the split.
- 2.2: the data revision.
- 2.3: accept `gpt-6-astra` as an alias, recording each response's model field, or use `gpt-5.5-2026-04-23`;
  reasoning effort; max output tokens.
- 2.4: the answer prompt's placeholders.
- 2.5: how confidence is elicited. The cut is ruled.
- 2.6: agreement sampling.
- 2.7: what "matches" means.
- 2.8: penalties, and PARTIAL scoring 0.
- 2.9: the grader.
- 2.10: λ_usd and the second-opinion price grid.
- 2.12: `claude-opus-5-5`'s reasoning effort and max tokens, and whether its key becomes `ANTHROPIC_API_KEY`.
- 2.13: the claims.
- 2.14: seeds and the budget ceiling.
- The reading of 2.21, above.

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
  **Revised 2026-09-27:** the alternative. `answer_second` costs c in every state, so a blind switch is priced
  exactly; a switch after `second_opinion` is overcharged by c, and the scoreboard prints how often and what it cost.
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

  **Superseded 2026-09-27 by wald v0.2.1**, which answers both points: `wald.digest`, `wald.score` and `wald.e7`
  are public, and `load_pack` reads long literals itself. The fetched kit (`arena/kit.py`, `kit.lock`,
  `fetch_kit.sh`) is gone, and so is the runner's lift of the digit limit, which had changed it for the whole
  process. The Score is text now, and the scoreboard reads its size and log from the text. wald hands a host no
  P(Global | Counts), so the Global marginals the kit gave are no longer printed; what the Counts moved shows in the
  acts and in E7.
- **2.24 Compute, and the one-run maximiser.** The one-run maximiser of E7 (the exact plate value) is beyond the
  kit's size bound at this World's size, so the scoreboard says so and prints the realised values with and
  without Counts instead.

  Measured in the dry run at the proposed grid: 144 calibration episodes in 186 s, and 150 test questions in
  807–879 s per plate (each plate plays every question twice, with the Counts and from the declared prior), six
  plates in parallel on 8 cores. Episodes slow as Counts grow, so 300 test questions per plate will take more than
  twice as long; this is extrapolated, not measured. With 2.10's grid less `none` (seven prices) at three
  penalties, that is 21 plates: several hours of CPU, and no API spend.
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

- **2026-09-27, 2.19 revised:** `answer_second` is charged its consulting cost c in every state, so a blind switch
  is priced exactly. A switch after `second_opinion` is then overcharged by c; the scoreboard prints how often that
  happens and the total overcharge.

- **2026-09-27, the bucket gate:** waived for the Haiku dry run only, and said plainly in its report. The gate
  stands for the real run: once the frozen model's calibration split is drawn, its histogram and bucket shares are
  printed before any test question is played, and if either bucket holds under a fifth of its records the run stops
  for the owner to rule the cut again from that model's calibration data. Cut 80, unread → b0, stand for now.

- **2026-09-25, brief 002 revision 2:**
  - **2.15:** two confidence buckets, cut at 80 (b0 = 0–79, b1 = 80–100). An unreadable confidence joins b0. Each
    ρ_b is on {7/20, 13/20, 17/20, 19/20}, which straddles p/(1 + p) at p = 1, 3, 10. The other grids are as
    proposed, and P(Global) is uniform, `elicited`. Before any test question is played, the runner prints the
    calibration split's confidence histogram and each bucket's share, and stops for a new ruling if either bucket
    holds under a fifth of the calibration records.
  - **2.21:** no calibration plate. The calibration Counts are constructed directly: every instrument drawn on
    every calibration question, graded, one record per question, each record's end chosen for what its grade
    teaches. Each record's realisability, and the digest and Score, are checked with the kit's reference. The same
    Counts ship into every test pack.
  - **2.19:** accepted. The scoreboard prints the number of blind switches and their total undercharge.
  - **Models:** every string is verified against the providers' current lists and pinned with the date;
    `claude-opus-5` becomes `claude-opus-5-5` if the list shows it (it does: "Models, as listed", below).
  - **2.16, 2.17, 2.18, 2.20, 2.22, 2.23, 2.24:** accepted as proposed.
  - **Open 1:** moot.

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
