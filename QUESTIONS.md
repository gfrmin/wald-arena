# Questions for the owner

Numbers and rulings the brief leaves open. Nothing below is defaulted in code: `owner.toml` holds what has been
ruled, and a missing key fails loud where it is needed. Each open question blocks only what it names.

## Open

1. **Question set** (Millionaire): moot. Millionaire's live play is dropped (ruled 2026-09-25); the table that
   stood here is in git history.
2. **The lookahead memo** (AA-Omniscience): `board.forget_lookahead` drops wald's `World.work()` memo between a
   learning plate's episodes by reaching into a private attribute of the pinned wald. It stays until wald rules on
   the memo: wald's brief 010 ("the plate owns the lookahead's memo", written 2026-10-01, `gfrmin/wald` `3a0b104`).
   When the builder's PR is merged and a signed release names it, the pin is bumped and the call deleted. See the Finding "wald's episode cost grows with the Counts".

## Status: brief 002, as of 2026-09-25 (wald 0.1.0)

**Brief 002 is played to its verdicts** (2026-10-01, PR #4, `51f5adc`): the board is
`showcases/omniscience/runs/run/SCOREBOARD-stage2.md`, and "Stage 2's test half", below, holds the verdicts, the
audit and the dollars. The status that follows is as of 2026-09-25 and is kept as the record.

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

**Ruled, every item** (2026-09-25, 2026-09-27, 2026-09-28; see `## Ruled`). `owner.toml` now names the
instruments. What keeps a frozen model uncalled is:
- each instrument's `listed`, which stays empty until its model string is verified against the provider's list on
  the day;
- the stages (`--stage pilot-calibration`, then `pilot-test` and `stage2`);
- the owner's `go.pilot_test` and `go.stage2`, which the runner requires before those stages.

The items below are kept as they were proposed, and the rulings stand beside them.

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

**Nothing is open for brief 002.** Both goes were given and both halves played (below). What waits is wald's: the
lookahead memo (Open, 2).

### Stage 2's test half (2026-09-30 – 10-01): played, audited, the verdicts printed

The owner kept the cut at 90 and gave `go.stage2_test` (ruled 2026-09-30, below).

**The calls** (10:26–11:40, steel, Gemini over IPv6). All 300 test questions answered and graded: the pilot's 50
and stage 2's 250, 600 records in all. Two stops, each resumed without loss.
- 10:59, Gemini `HTTP 503` ("high demand"): temporary, not billed.
- 11:08, OpenAI `429 credit_balance_exhausted`: the owner topped up.

Dollars by the log: $38.40 for the whole run (gpt-5.5 $31.97, Opus $4.12, Gemini $2.31). The test half cost $16.65
against $15.41 projected; the difference is the questions in flight at each stop, asked again. The wallet is about
$2 above the log: calls cut off at a stop are held at their worst case, as the pilot's timed-out call was.

**The plates.** No paid call; they replay the records. Three attempts on steel (31 GB) failed on memory.
- 12:10: Claude Code's low-memory reaper killed the run, with another session's evaluation beside it.
- 14:48: at 6 workers the machine went into swap, so I stopped it myself.
- 15:25: at 3 workers the reaper killed it again.

A plate's memory grew with every episode, by about 0.1–0.25 GB each. The owner approved a DigitalOcean droplet:
`wald-plates`, g5-32vcpu-256gb, $1.94/h, on the tailnet as `tag:do`, public SSH closed, no API key on it, the
plates run with `--replay`. The first droplet run reached 96 GB in 21 minutes and was stopped. My first fix was to keep
only `acts`, `paid` and `status` of each episode's `Result` (`board.Ended`), not its `final` belief. It was right
to do but was not the cause: the rerun from 17:20 grew as fast (101 GB at 17:46). The cause is wald's lookahead
memo, `World.work()`. It holds the values found, keyed by the belief they were found at (exact rationals over every
state), for the World's whole life. On a plate that learns, no episode's prior recurs, because the Counts grow, so
the memo only grows, by about 0.25 GB an episode. The harness now drops it after each episode of a learning plate
(`board.forget_lookahead`); fresh episodes keep it, since their prior recurs. A dropped value is found again,
the same value; a test plays a plate both ways and gets the same acts, prices and Counts. It reaches into a private
attribute of the pinned wald, and it stays only until wald rules on it (the finding below). Restarted 17:56. The droplet is deleted once the plates'
results are back on steel (the owner, 2026-09-30).

**Played.** The 21 plates ran on the droplet from 17:56 to 22:04, 2.6–4.2 hours each, at 1.4 GB a plate once the
lookahead memo was dropped between episodes. The run replayed the records and changed none of them: records, calls,
grades, the wallet's log, Counts, posterior, disclosure, cuts and estimate all came back identical to steel's
copies. A second replay on the same droplet (21:33–01:00, the owner's go), from a fresh clone at the commit that
saves the plates' results, gave a byte-identical scoreboard, `e7.txt`, audit sample, Counts and posterior. So the
plates are deterministic, with the memo dropped and 21 played at once. Its `plates.pkl` re-rendered the board after
the audit without playing a plate again (kept in the run directory, not in git: it is a pickle, and this repository
is public). The droplet was deleted 2026-10-01 05:40, and its tailnet device removed. It ran about 13.3 hours, about
$26 at $1.94/h, against $8–15 estimated. The difference is the two stopped runs (memory), the second replay, and
about 4.5 idle hours overnight between the replay's end and its deletion. A 32-vCPU, 64 GB droplet (about $1.00/h)
would have been enough once memory was fixed.

**The verdicts** (on the 250 unseen; all 300 beside):

| claim | Δ, 250 unseen (± 2 SE) | verdict | Δ, all 300 |
|---|---|---|---|
| (i) ties the threshold at p = 1 | −0.020 ± 0.041 | held | −0.018 ± 0.035 |
| (ii) separates from the threshold at p = 3 | +0.168 ± 0.108 | held | +0.203 ± 0.104 |
| (ii) separates from the threshold at p = 10 | −0.028 ± 0.279 | missed | +0.029 ± 0.244 |
| (iii) separates near the stake at p = 1 (best c = 1/2) | −0.020 ± 0.041 | missed | −0.018 ± 0.035 |
| (iii) separates near the stake at p = 3 | +0.168 ± 0.108 | held | +0.203 ± 0.104 |
| (iii) separates near the stake at p = 10 | −0.028 ± 0.279 | missed | +0.029 ± 0.244 |
| (iv) beats the raw model throughout (weakest p = 1, c = 1/4) | +0.148 ± 0.061 | held | +0.148 ± 0.054 |

p = 10 was stated in advance to be underpowered. On the board's own metrics at p = 1, c = 2, the better-single-model
baseline beats wald (Omniscience Index +56.7 against +36.0), as the scoreboard prints.

**The owner's hand audit (2.9), 2026-09-30.** 60 grades, 10 per domain from all 300, graded blind: the page showed
the question, the gold target and the answer, never the grader's grade. First pass: 53 of 60 agree with
gemini-3.8-flash. I then showed the owner the seven disagreements, and that AA's rubric (its example 4) grades a
hedged guess ("I'm not certain … my best recollection is X") NOT_ATTEMPTED. The owner regraded those three
(questions 98, 172, 149) from partial to not attempted, "according to rubric". Final: 56 of 60. Four remain:
question 104 (owner partial, grader correct), 390 (partial, incorrect), 495 (partial, incorrect) and 455
(incorrect, correct). The second pass was not blind for those three.

**The time.** An episode of stage 2's first plate episodes took 22–30 s, on steel and on the droplet alike (an EPYC
9555P, per core about steel's Ryzen 5600X). The 5.3 s measured on steel on 2026-09-29 was on the pilot's 50
calibration records; stage 2's plates start from 300 and grow to 600. See the finding "wald's episode cost grows
with the Counts", below.

### Stage 2's calibration half (2026-09-30): run; stopped for the owner's cut and `go.stage2_test`

Run on steel, 08:55–10:18 (calls to 09:40, then the Counts, the posterior and S15), Gemini over IPv6. 250 new
calibration questions observed and graded; no test question called. Checked: every call's served model is its pinned
one; none truncated; every live grader and equivalence call at thinking `low` (681 and 350).

**Dollars.** Log $21.747 for the whole run so far (stage 2's calibration half about $15.5); the wallet $22.254, the
$0.507 above the log being the pilot's timed-out call reserved at its worst case (the OpenAI timeout, ruled earlier).
Measured on 300: per question primary $0.0515, second $0.0066, equivalence $0.0006, grader $0.0030. Projected:
stage 2's test half $15.41, whole run $37.67, under the $80 cap.

**The gate** passes at the ruled cut 90: b0 98 of 300 (32.7%), b1 202 (67.3%).

**The cut table** (all 300 calibration records; unread → b0; none unread):

| cut | b0 records | b0 read right | b1 records | b1 read right | gap |
|---|---|---|---|---|---|
| 70 | 18 (6%) | 1 (6%) | 282 (94%) | 194 (69%) | 63 pts; fails the gate |
| 80 | 40 (13%) | 4 (10%) | 260 (87%) | 191 (73%) | 63 pts; fails the gate |
| 85 | 51 (17%) | 7 (14%) | 249 (83%) | 188 (76%) | 62 pts; fails the gate |
| **90 (ruled)** | 98 (33%) | 32 (33%) | 202 (67%) | 163 (81%) | 48 pts |
| 95 | 147 (49%) | 63 (43%) | 153 (51%) | 132 (86%) | 43 pts |

Of the cuts that pass the gate (a fifth in each bucket), 90 separates the buckets most. The cuts below 90 separate
more but leave b0 under a fifth. Whether another cut is "clearly better" is the owner's ruling (2026-09-28).

**The Counts**: 300 records, 24 distinct, sha256 `6b5180da20cecb5795a7135a5aa761732cfad0d5c406ca6ea489ffd7ab668b9b`,
committed with this section.

**P(Global | Counts)** (marginals summed from `wald.report`, for display): ρ b0 = 7/20 and ρ b1 = 17/20 (each
100.0%); agree (4/5, 1/5) 100.0%; second (σ 1/2, β 1/5) with α 9/10 65.2% and α 4/5 34.7% (19/20 ≈ 0); grader
γ 9/10 100.0%; corr 0 100.0%. **S15**: at every (p, c), no class of inseparable Global values settles anything an act
can feel.

**Ruled 2026-09-30:** keep 90, and go. (Was wanted: the cut, then `go.stage2_test` for `--stage stage2` (the 250 test
questions, about $15.41, then the 21 plates on all 300, about 4 hours at 6 workers).)

### Stage 2, built (2026-09-29, on steel): two halves, calls at once, the verdict on the 250

- **Two halves.** `--stage stage2-calibration` (needs `go.stage2`) observes and grades the 250 new calibration
  questions only, then on all 300: the gate, a cut table (cuts 70, 80, 85, 90, 95 and the ruled one: each bucket's
  records and reads right), the Counts, P(Global | Counts) and S15, and stops. The owner looks at the cut
  (the ruling of 2026-09-28: stop and ask if another separates clearly better); the Counts are committed; then
  `--stage stage2` (needs `go.stage2_test`, and refuses to start until every stage-2 calibration record exists) plays
  the 250 test questions and the 21 plates.
- **Calls at once** (ruled 2026-09-29): `calls.workers = 4` questions observed, and answers graded, at once. The
  wallet counts every open reservation at its worst case, so calls in flight together never pass a cap; near a cap
  the run stops up to four worst cases early (about $2 at gpt-5.5's $0.50). The first failure in any worker stops
  the wallet, so no new call starts; calls already in flight finish and are logged. Records land in the order they
  finish, and every stage reads them back in the split's order, so the Counts do not depend on it (the pilot's
  digest is unchanged, `0aba0eb7…d5db194`; a test builds the same Counts with 4 workers as with 1).
- **The verdict on the 250** (ruled 2026-09-29): claims (i)–(iv) are judged on stage 2's 250 test questions; Δ on
  all 300 is printed beside each; the by-penalty tables stay on all 300 and say so; the hand audit draws its 60 from
  all 300. The p = 10 power bound is restated at 250 (0.696). `[board] changes` states it on the board.
- **Gemini over IPv6** (2026-09-30, the owner: "keep mullvad, but route gemini calls around it"). The first
  stage-2 run stopped at its first equivalence call on `HTTP 403`: Google's HTML "unusual traffic" page, served by
  its front door on IP reputation before the key or the billing is read. steel's IPv4 leaves through the tailnet's
  exit node (Mullvad, CH, AS51852), which Google now refuses; its IPv6 goes direct and is served. `GEMINI_IP_FAMILY=6`
  in the environment makes the Gemini transport connect over IPv6 only (never falling back to IPv4); nothing else
  about the call changes (model, thinking level, prompts, price). Checked on steel: the model's metadata endpoint
  through the transport's path, 403 without it, 200 with it. The stop cost 22 logged calls ($0.15), kept; the four
  questions in flight are asked again on resume (about $0.15).
- **Measured on steel**, at 1,152 Global values: 5.3 s an episode (thinkpad 9.9), 146 s to declare a plate
  (226), 1.4 GB a worker. Stage 2's plates: about an hour each, 21 of them at 6 workers about 4 hours. The calls:
  250 questions a half at 4 at once, about 1–1.5 hours each. Dollars unchanged: whole run projected about $37.

**Previously open (now done: funded, pinned 2026-09-28T11:21Z, pilot-calibration run):**
- Funding: the OpenAI account and the Gemini project (2026-09-28T07:25Z: no credit on either).
- On the day: verify and pin each model string and list price in `owner.toml` (`listed`); settle Gemini's thinking
  setting (item 6 of "The pilot, built", above).
- Then `--stage pilot-calibration`, which stops at the gate and the re-estimate. `pilot-test` and `stage2` each wait
  for the owner's go.

### α's grid widened (ruled 2026-09-29): the pilot's posterior under it, and stage 2's time

The World now has 1,152 Global values (was 384). `owner.toml` `[board] changes` states the change, and the
scoreboard prints it under the header.

**The pilot's 50 calibration records under the new grid** (P(Global | Counts), wald's; marginals summed for display):

| Global | posterior |
|---|---|
| α (Opus same \| gpt-5.5 right) | 4/5: 7.5%; **9/10: 41.9%**; **19/20: 50.6%** |
| (σ, α, β) | (1/2, 19/20, 1/5): 50.4%; (1/2, 9/10, 1/5): 41.7%; (1/2, 4/5, 1/5): 7.4%; σ = 1/10: 0.4% |
| ρ_b0 | 7/20: 97.9%; 13/20: 2.1% |
| ρ_b1 | 13/20: 31.4%; 17/20: 67.1%; 19/20: 1.5% |
| agree | (4/5, 1/5): 98.9% |
| γ | 9/10: 39.3%; 1: 60.7% |
| κ | 0: 28.0%; 1/2: 72.0% |

**Stage 2's time, measured on the new World:** declaring a plate 226 s (was about 40 s); an episode 9.9 s (was
about 6 s); 1.4 GB per worker. Each plate plays its 300 test questions twice (with the Counts and from the declared
prior), so about 1.7 hours a plate, and the 21 plates at 3 workers about 12 hours. The calls themselves, 500 questions
one call at a time at about 6 s, take about 7.5 hours before that. No change to the dollars (projected whole run
about $37).

**Still to rule:** whether the verdict covers stage 2's 250 unseen test questions only, with all 300 reported beside
it, since the pilot's 50 were seen before α was widened (the ruling of 2026-09-28 says all 300).

### The pilot's test half (2026-09-29): played; stopped for the owner's go on stage 2

`--stage pilot-test` on the owner's go of 2026-09-29: 50 test questions, 21 plates (3 penalties × 7 prices), the
scoreboard in `runs/run/SCOREBOARD-pilot-test.md`. A replay of every plate reproduced it exactly.

- **Spend:** the pilot, $6.61 of its $15 (1,044 calls; $6.11 logged, and $0.50 for one gpt-5.5 call that hung and
  timed out after the SDK's 600 s, counted at its worst case since it may have been billed). Whole run projected about
  $37. No truncation; every call served the pinned model. The OpenAI timeout is now 120 s (the slowest of 500 calls
  took 28.5 s).
- **Omniscience Index (p = 1):** raw gpt-5.5 +24, calibrated threshold +40, wald +48 (70% coverage, 23.8%
  hallucination rate), better single model (Opus 5.5 alone) +68.
- **wald against the threshold**, net per question, c = 2 (± 2 SE): p = 1 +0.056 ± 0.096; p = 3 +0.377 ± 0.302;
  p = 10 +0.317 ± 0.444. Against the raw model it is ahead at every (p, c). No verdict: the pilot writes none.
- **Opus alone beats wald at p = 1 when the second opinion is free or cheap** (net +0.680 vs +0.534 at c = 0; +0.630
  vs +0.496 at c = 1/20), roughly ties it at p = 3, c = 0 (+0.520 vs +0.514), and loses at p = 10 and wherever c is
  large. wald almost never answers with the second opinion: one switch in all 21 plates.

**A question for the owner before stage 2: α's grid.** The World's (σ, α, β) grid (2.15) offers α = P(the second
opinion gives the same answer | the primary is right) = 4/5 only. On the calibration split, when gpt-5.5 was right
(31), Opus gave the same answer 28 times (0.90); on the test half, 30 of 30. So when the two differ the World thinks
gpt-5.5 is still often right, and wald keeps its answer or abstains. On the calibration split they differed 18 times:
gpt-5.5 right 3, Opus right 9. On the test half they differed 16 times: gpt-5.5 right 0, Opus 8. The grid is
pre-registered and the owner's; widening it after the pilot is a change to the pre-registration, and this note does
not make it. Options: keep the grid for stage 2 as registered (and report this); or add α values (e.g. 9/10, 19/20)
before stage 2, stated on the board as a post-pilot change. Stage 2's 250 new calibration records would then fit α.

### The pilot's calibration Counts, under the rulings of 2026-09-28 (the cut at 90; Gemini at `low`)

**Done, and stopped for the owner's go on the pilot's test half.** No test question has been drawn or played.

- **Re-sorted and re-graded at `low`:** 50 equivalence calls ($0.031) and 98 grades ($0.155). The 148 Gemini calls
  made under "off" stay in `calls.jsonl`, marked `superseded`; the old grade memo is `grades.superseded.jsonl`; each
  record keeps its old classes, k, s and equivalence call under `superseded`. Every grade came back the same at
  `low` as under "off", and one record's k changed (1 → 0).
- **Spend so far:** $3.2032 (wallet and call log agree), of which $0.1904 is the superseded grading. Projected: pilot
  test $3.01, stage 2 $30.13, whole run $36.34.
- **Gate at cut 90:** b0 18 of 50 (36%), b1 32 (64%): passes.
- **Counts:** 50 records, 15 distinct, sha256 `0aba0eb73f3f204016fae623c1110ec86ad299553d7c4824d0950190ad5db194`
  (`runs/run/calibration_counts.json`).

**P(Global | Counts)**, wald's (`wald.counts.posterior_global`, rendered by `wald.report`; the full joint over the
384 Global values, exact, is `runs/run/posterior.json`). Each marginal below is that text's rationals summed, for the
owner to read; no contestant reads it. The prior is uniform over every grid.

| Global | posterior |
|---|---|
| ρ_b0, P(primary right \| 0–89) | 7/20: 96.8%; 13/20: 3.2%; 17/20 and 19/20: under 0.1% |
| ρ_b1, P(primary right \| 90–100) | 13/20: 24.3%; 17/20: 72.0%; 19/20: 3.8%; 7/20: under 0.1% |
| agree (a⁺, a⁻) | (4/5, 1/5): 99.1%; (1/2, 1/2): 0.9% |
| second (σ, α, β) | (1/2, 4/5, 1/5): 99.3%; (1/10, 4/5, 1/2): 0.7% |
| grader γ | 9/10: 45.0%; 1: 55.0% (barely moved: the Counts say little about the grader until the audit) |
| κ (2.25) | 0: 23.4%; 1/2: 76.6%; 9/10: 0.1% |

The most probable joint value is ρ = (7/20, 17/20), agree (4/5, 1/5), second (1/2, 4/5, 1/5), γ = 1, κ = 1/2, at
29.0%.

**S15's disclosure** (`Plate.disclosure()`, with the Counts shipped), the same at all 21 (p, c) declarations:
*no class of inseparable Global values settles anything an act can feel* (`runs/run/disclosure.txt`).

### The pilot's calibration stage (2026-09-28): the gate fired; two rulings wanted

`--stage pilot-calibration` ran on the models pinned at 11:21Z: 50 questions, 448 calls, **$3.0142**
(the call log and the wallet agree to the cent). No test question was drawn or played. Served models never changed;
no reply was truncated; every equivalence reply parsed.

**Measured, per question:** primary $0.0503 (5 calls, 304 reasoning tokens per call on average, max 1,468), second
opinion $0.0062 (0 reasoning tokens), equivalence $0.0006, grades $0.0032 (1.96 per question). **Projected:** pilot
test $3.01, stage 2 $30.14, whole run **$36.17**, against the $80 cap; the pilot, $6.03 against $15.

**The gate fired (2.15 as ruled: cut 80, unread → low).** b0 holds 5 of 50 (10%), b1 45 (90%). The run stopped
there, as ruled. gpt-5.5's stated confidences, with the grade of its read:

| confidence | records | correct | incorrect | not attempted |
|---|---|---|---|---|
| 0–79 | 5 | 1 | 3 | 1 |
| 80–89 | 13 | 5 | 8 | 0 |
| 90–94 | 7 | 6 | 1 | 0 |
| 95 | 17 | 13 | 4 | 0 |
| 96–100 | 8 | 6 | 2 | 0 |

No confidence was unread. Cuts that put a fifth or more in each bucket, on these 50:
- **cut 90:** b0 18 (36%), 6 correct (33%); b1 32 (64%), 25 correct (78%).
- **cut 95:** b0 25 (50%), 12 correct (48%); b1 25 (50%), 19 correct (76%).
- cut 85 fails the gate too: b0 6 (12%).

**Ruling wanted (a): the cut.** The owner's, from these data (2.15). Nothing more is called until it is ruled; the
pilot's records are kept, and the Counts are built from them under whichever cut is ruled.

**Ruling wanted (b): Gemini's thinking.** `gemini-3.8-flash` accepted a thinking budget of 0 without error, but
thought anyway on 104 of its 148 calls (up to 985 thinking tokens). The API did not refuse "off"; it did not honour it
either. 2.9 as ruled says "reasoning off if the API allows, else fixed low and recorded". My reading: "off" is not
available, so thinking level `low` from here. That leaves the pilot's 98 grades and 50 equivalence calls made under
an unhonoured "off". Options: keep them, recorded as such; or re-grade and re-sort those 50 questions at `low`
(about $0.20, the same answers, no new primary or Opus calls).

### The pilot, built (2026-09-28): the equivalence prompt, the re-estimate, and what the owner should confirm

**Not yet funded.** At 2026-09-28T07:25Z the Gemini project's prepaid credit is used up, and the OpenAI account has
no credit (`credit_balance_exhausted`). Nothing was called.

**The equivalence prompt** (2.7 as ruled; `prompts/equivalence.txt`). It is sent to `gemini-3.8-flash` as the user
turn, with no system prompt. The answers are numbered in a fixed order (the read, the three samples, the second
opinion), so the model is not told which is the read. An empty reply is shown as "(no answer)".

```
You will be shown a question and several numbered answers to it. Sort the answers into classes: two answers belong to the same class if a grader would accept them as the same answer to the question, whatever their wording, spelling or level of detail. An answer that declines to answer (it says it does not know, cannot answer, or gives no answer at all) belongs to the class D, whatever its wording. Number the other classes 1, 2, 3 and so on.

Question: {question}

{answers}

Reply with one line per answer, in the order given, each in the form "<answer number>: <class>", and nothing else.
```

A reply is read if it has exactly one line per answer, in order, each "<i>: <class>" with the class D or a whole
number. k is the number of samples in the read's class, and s is "same" if the second opinion is in the read's class.

**Proposed by the repository while building; confirm or rule otherwise:**
1. **An unreadable equivalence reply.** k and s fall back to normalised exact match for that question, and the
   scoreboard counts such questions. The alternative is to stop the run.
2. **The agreement act's price.** It is three sample calls plus the equivalence call. The equivalence call is what
   reads k. It also gives s, but the second opinion's price is 2.10's grid, which is hypothetical, so nothing more
   is charged there.
3. **Measured prices.**
   - Every call is priced at list price from its tokens.
   - The packs declare the mean per call on the calibration split (2.12, as for Millionaire), per stage: the pilot's
     50 records, then all 300.
   - List prices sit in `owner.toml` and are re-verified on the day with the models.
4. **The caps.**
   - Before each call the wallet reserves the most that call can cost: list price for 4,000 tokens in and the
     instrument's whole max_tokens out ($0.50 for gpt-5.5, $0.34 for Opus 5.5, $0.007 for gemini-3.8-flash).
     *Changed 2026-09-28 after review, from "the most a call has cost so far", which could let one long call pass a
     cap; see `## Ruled`.*
   - It stops if that could take the stage's spend or the whole run's past its cap.
   - After each call it settles the reservation at the call's measured price. A call cut off counts at its
     reservation.
5. **Truncation and the served model.**
   - Every frozen instrument has a large max_tokens: 16,000 for the primary and the second opinion, 1,024 for the
     grader and the equivalence call.
   - The run stops on a truncated reply, as the earlier 2.3 ruled.
   - Each call records the model the provider says served it, and its reasoning tokens and effort. The run stops if
     an instrument is served a different model mid-run. That was the earlier 2.3, kept as a guard with the snapshot.
6. **Reasoning settings.**
   - `claude-opus-5-5` runs at the provider's default effort, since 2.12 sets none.
   - `gemini-3.8-flash` is sent a thinking budget of 0 ("disabled"). If the API refuses that, it is sent thinking
     level "low", as 2.9 rules, and `owner.toml` records which.
7. **The gate** applies at each stage to that stage's calibration split: the pilot's 50 records, then all 300 (the
   pilot's 50 and stage 2's 250, shipped as one set of Counts; confirmed 2026-09-28).
8. **The audit sample.** 10 graded answers per domain (the read's or the second opinion's) are drawn with the split
   seed from the whole 300-question test split, the pilot's 50 included (confirmed 2026-09-28), and written once to `audit.csv`, whose `owner_grade` column is for the owner to
   fill. The verdict column reads "withheld" until all 60 are filled, and then the agreement is printed.

**Re-estimate, with the ruled settings.** Each question takes 5 primary calls (the answer, the confidence, 3
samples), 1 second opinion, 1 equivalence call, and 1.93 grades on average.
- Tokens per call are the mixed dry run's measured means. The equivalence call's are estimated: 560 in, 30 out.
- R, R2 and T are reasoning tokens per call for gpt-5.5 at low effort, for Opus 5.5, and for Gemini if its
  thinking cannot be turned off. The pilot measures all three.
- List prices: gpt-5.5 $5 / $30 (re-verify on the day), claude-opus-5-5 $4 / $20, gemini-3.8-flash $0.75 / $3.75.

| R | R2 | T | per question | pilot, 100 (cap $15) | stage 2, 500 | whole, 600 (cap $80) |
|---|---|---|---|---|---|---|
| 200 | 200 | 0 | $0.049 | $4.91 | $24.56 | $29.47 |
| 200 | 1,000 | 200 | $0.067 | $6.73 | $33.65 | $40.38 |
| 500 | 200 | 0 | $0.094 | $9.41 | $47.06 | $56.47 |
| 500 | 1,000 | 200 | $0.112 | $11.23 | $56.15 | $67.38 |
| 1,000 | 200 | 0 | $0.169 | $16.91 | $84.56 | $101.47 |
| 1,000 | 1,000 | 200 | $0.187 | $18.73 | $93.65 | $112.38 |

- The pilot's cap is reached if gpt-5.5 at low effort reasons for more than about 760–880 tokens a call, and the
  whole run's above about 650–770.
- `pilot-calibration` prints the measured cost per question and the projection for the pilot's test half, stage 2
  and the whole run, then the gate, and stops.

### The ruled grid, timed, and the real run's dollars (2026-09-28)

**One plate at the ruled grid.** The grid is 2.15 × 2.25's κ ∈ {0, 1/2, 9/10}: 384 Global values, 3,840 states.
- The plate ran at p = 1, c = 1/10, replaying the mixed dry run's records, with no call. It shipped the 144
  calibration records, then played 150 test questions with the Counts and again from the declared prior.
- It took 1,835 s, or 12.2 s a question. The same plate without κ took 480 s in the mixed run, so κ makes it
  3.8 times as slow.
- S15 at declaration: "no class of inseparable Global values settles anything an act can feel".
- Extrapolated, not measured: the real run's 21 plates (2.10's seven prices × three penalties) of 300 test
  questions, shipping 300 calibration records, take about 60–80 minutes a plate, since episodes slow as Counts grow.
  That is about 21–28 hours of CPU, or 7–10 hours on the three cores this machine's memory allows. No API spend.

**Dollars for the real run** (superseded by the re-estimate in "The pilot, built", above, after 2.3 and 2.6 were
ruled again). 600 questions (2.1: 300 calibration, 300 test). Each question takes 7 primary calls
(the answer, the confidence, 5 samples), 1 second opinion, and on average 1.93 grades, since grading is memoised
per distinct (question, answer).
- Tokens per call are the mixed dry run's measured means:
  - answer: 130 in, 51 out;
  - confidence: 150 in, 48 out;
  - sample: 130 in, 51 out;
  - second opinion: 171 in, 29 out;
  - grade: 1,641 in, 4 out.
- R is the reasoning tokens per primary and second-opinion call, which 2.3 and 2.12 set. `claude-opus-5-5` cannot
  turn thinking off, so its R is above 0.
- List prices per million tokens (input / output):
  - `gpt-6-astra`: $10 / $50, and `gpt-5.5-2026-04-23`: $5 / $30, both as listed 2026-09-23 and to be re-verified
    when the account is live;
  - `claude-opus-5-5`: $4 / $20;
  - `gemini-3.8-flash`: $0.75 / $3.75 through 2026-12-31, then $1.50 / $7.50 (Google's pricing page, 2026-09-28);
  - `claude-sonnet-4-6`: $3 / $15.
- These are list-price estimates from measured tokens. OpenAI's tokenizer counts differently, and the declared
  prices the budget reserves are upper bounds above these.

| primary | R | primary | second (`claude-opus-5-5`) | grader `gemini-3.8-flash`, no thinking | the same, 500 thinking tokens a grade | grader `claude-sonnet-4-6`, thinking off |
|---|---|---|---|---|---|---|
| `gpt-6-astra` | 0 | $16.20 | $0.75 | **$18.40** | **$20.57** | **$22.72** |
| `gpt-6-astra` | 500 | $121.20 | $6.75 | **$129.40** | **$131.57** | **$133.72** |
| `gpt-6-astra` | 2,000 | $436.20 | $24.75 | **$462.40** | **$464.57** | **$466.72** |
| `gpt-5.5-2026-04-23` | 0 / 500 / 2,000 | $9.16 / $72.16 / $261.16 | as above | $11.36 / $80.36 / $287.36 | $13.53 / $82.53 / $289.53 | $15.68 / $84.68 / $291.68 |

- The grader costs $1.44–$5.77 whichever is chosen. The primary's reasoning sets the bill.
- The pre-registered primary is `gpt-6-astra`.
- Whether `gemini-3.8-flash` can turn thinking off is not on its pricing page, and the Gemini account has no credit
  to try it.

### The second dry run: a different model in each role (2026-09-27)

This run exists because the all-Haiku dry run cannot test independence.

**Setup.**
- Settings: `dryrun-mixed.toml`, run directory `runs/dry-run-mixed/`, with its own `SCOREBOARD.md`.
- Instruments:
  - primary: `claude-haiku-4-5-20251001`;
  - second opinion: `claude-sonnet-5`, thinking off;
  - grader: `claude-sonnet-4-6`, thinking off.
- Models were checked against the providers' lists at 2026-09-27T19:44Z.
- The same 294 questions as the first dry run: seed 1, 49 per domain.
- Declared spend $5.79 of a $6.00 cap; $3.80 at list price from the tokens used. No frozen model was called.

**Why the grader is a third Anthropic model.** No other provider could be called on 2026-09-27:
- the OpenAI account has no credit (429 `credit_balance_exhausted`);
- the Gemini project's prepaid credit is used up;
- `gemini-2.5-flash` is listed but refused to new users (404: "no longer available to new users … use
  models/gemini-3.8-flash");
- the OpenRouter key is unknown (401).

This blocks the real run as proposed. 2.3's primary is an OpenAI model, and 2.9's proposed grader cannot be called
by this account. A Gemini transport (standard library only) is in `arena/transports.py`, unexercised past the 404.

**The gate** was waived here too, stated in the report: b1 holds 19 of 144 records (13.2%). The primary is the same
Haiku the waiver was ruled for.

**Net utility per question** (Δ wald − threshold ± 2 SE):

| p | c | wald | threshold | raw | better single | Δ | blind switches | switches after consulting |
|---|---|---|---|---|---|---|---|---|
| 1 | 1/10 | +0.018 | −0.007 | −0.047 | −0.013 | +0.025 ± 0.057 | 1 | 0 |
| 1 | 1 | +0.023 | −0.007 | −0.047 | −0.913 | +0.030 ± 0.052 | 0 | 0 |
| 3 | 1/10 | −0.017 | +0.000 | −0.473 | −0.473 | −0.017 ± 0.065 | 0 | 0 |
| 3 | 1 | +0.000 | +0.000 | −0.473 | −0.473 | +0.000 ± 0.000 | 0 | 0 |
| 10 | 1/10 | −0.110 | +0.000 | −1.967 | −1.967 | −0.110 ± 0.192 | 0 | 0 |
| 10 | 1 | +0.000 | +0.000 | −1.967 | −1.967 | +0.000 ± 0.000 | 0 | 0 |

**What the records say about independence** (a display of counts, not a fit). The table crosses unanimous agreement
(all five samples match the read) with whether the second opinion matches the read, and splits by the grader's
verdict on the read:

| read | all & same | all & different | some & same | some & different |
|---|---|---|---|---|
| right | 11 | 2 | 8 | 27 |
| not right | 4 | 5 | 3 | 234 |

- When the read is not right, the second opinion matches it in 4 of 9 unanimous cases, against 3 of 237 others.
- When the read is right: 11 of 13, against 8 of 35.
- Today's World says these are equal given t (2.25).
- Caveats: the split is by the grader's verdict, not by t, and "not right" pools t = second (where the match is
  impossible) with t = neither.
- Unanimity is rare (22 of 294). The samples are compared as strings (2.7), so they seldom match exactly, and the
  "all" cells are small.
- It is evidence for 2.25, not a test of it.

**E7 at p = 10, c = 1/10** is in the run's scoreboard, each line with its draw count.
- The largest lines rest on 1–3 draws: 0.62 on 2 draws, 0.47 on 3.
- Of the lines with many draws, the worst are:
  - `agreement` after b0: 0.39 on 254 draws;
  - `confidence`: 0.36 on 294, where P(b) is uniform and b1 holds 13%;
  - `grade` after b0 → some → different → `answer_second`: 0.21 on 59;
  - `second_opinion` after b0 → some: 0.15 on 121.
- The second opinion's line after b0 → all is 0.26 on 6 draws.

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

- **2.25 Can the agreement and the second opinion be wrong together?** (proposed 2026-09-27; the owner rules)

  **Today's World cannot say so.** Given which answer is right (t), and given the Globals, it treats the bucket,
  the agreement and the second opinion as independent:
  - the agreement kernel reads only t and (a⁺, a⁻);
  - whether the second opinion matches the read depends only on t and (σ, α, β).

  So when the primary is wrong, unanimous samples and a second opinion repeating the same wrong answer are, to the
  World, two independent pieces of evidence. The all-Haiku dry run cannot test this, since one model in every role
  is correlated with itself by construction. Two lawful ways to let the World say it follow. Each adds one Global
  component that the calibration records' joint draws can teach, since every record draws all three observations.

  **A. A correlation Global κ.** This is built, and off unless an owner file names a grid: `Grids.corr`,
  `world.py`. With probability κ the instruments are tied: all five samples match exactly when the second opinion
  matches the read. Otherwise they behave as today:

      P(all | t, s, a, κ) = (1 − κ) · a_t + κ · [s = same],   where a_t = a⁺ if t = primary, else a⁻.

  - κ = 0 is today's World, so the grid nests it, and the Counts can push the posterior back to 0.
  - The agreement kernel reads (t, s, agree, corr). Nothing else changes: no local is added, the utilities and the
    grade are untouched, and the calibration Counts ship as they are.
  - κ > 0 makes "all agree and the second repeats the read" more likely together than apart for every t. When t is
    `neither`, that is the case of being wrong together.
  - Proposed grid: κ ∈ {0, 1/2}. A three-point grid {0, 1/4, 1/2} costs half as much again.

  **B. A shared local "difficulty" d ∈ {easy, hard}.** P(hard) = η is a new Global.
  - An easy question is today's World.
  - On a hard question the primary is right with probability ρ_b / 2. The factor 1/2 is fixed and elicited; letting
    it be learned needs another Global. The samples are unanimous, and the second opinion repeats the read unless
    the second is the one that is right.
  - So hard questions are where both instruments are confidently wrong together, and they also lower the read's
    reliability. A adds no local; B does, and so has more states per Global value.
  - Proposed grid: η ∈ {0, 1/4}, or {0, 1/4, 1/2}.
  - B is less general than A in one respect: it ties the samples and the match to each other and to accuracy
    through one switch. It is more literal in another: "hard" names a property of the question, which a later board
    could observe.

  **Cost.** Measured 2026-09-27 on this machine, one process. The Haiku dry run's 144 calibration records were
  shipped; 20 test episodes were played in plate order at p = 10, c = 1/10. "Pack" is the time to generate the pack,
  its Score included; "declare" is wald's check of it.

  | World | Global values | states | pack | declare | seconds per episode (mean of 20) |
  |---|---|---|---|---|---|
  | today | 128 | 1,280 | 6 s | 12 s | 2.1 |
  | A, κ ∈ {0, 1/2} | 256 | 2,560 | 15 s | 26 s | 4.2 |
  | A, κ ∈ {0, 1/4, 1/2} | 384 | 3,840 | 24 s | 41 s | 6.8 |
  | B, η ∈ {0, 1/4} | 256 | 3,328 | 19 s | 33 s | 5.8 |
  | B, η ∈ {0, 1/4, 1/2} | 384 | 5,376 | 35 s | 57 s | 9.0 |

  Episode time grows with the states, and with the Counts a plate has gathered (2.24). For the real run's 21 plates
  of 300 test questions, today's World needs about 7 hours of CPU, extrapolated: 2–3 hours on three cores. A with
  two values of κ doubles that, and B with two values of η is about 2.7 times it. No API spend either way.

  **Proposed: A with κ ∈ {0, 1/2}.** It nests today's World, adds no local, costs the least, and speaks to exactly
  the question asked. Whatever is ruled goes on the scoreboard with E7's second-opinion lines. Those lines are
  where the independent World fits worst in the all-Haiku dry run (0.33 after b0 → all, against 0.10 after
  b0 → some, at p = 10, c = 1/10), and they are where a correlation would show. **Blocks:** the World.

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

- **2026-09-30, stage 2's plates:** play them on a DigitalOcean droplet (the owner's "go"), and delete it when
  they are finished. Gemini's calls route over IPv6 around the tailnet's Mullvad exit ("keep mullvad, but route
  gemini calls around it somehow").

- **2026-09-30, stage 2's cut and go:** the cut stays at 90, seen on all 300 calibration records; go on stage 2's
  test half (`go.stage2_test`).

- **2026-09-29, stage 2:** the verdict reads stage 2's 250 unseen test questions, with all 300 reported beside it; the
  60-grade audit still draws from all 300. Stage 2's frozen-model calls run a few questions at once. Development of
  the three wald repos moved to steel.

- **2026-09-29, α's grid:** widen it. The second opinion's (σ, α, β) grid keeps the two registered (σ, β) pairs and
  crosses each with α ∈ {4/5, 9/10, 19/20}: six values, and 1,152 Global values in all. It is a change made after
  the pilot, stated on the board, and justified by the pilot's calibration records (Opus matched a right gpt-5.5 28
  times in 31); the pilot's test half showed the same (30 of 30), and the board says so.

- **2026-09-28, the pilot's calibration stage:**
  - **(a) The cut is 90:** b0 = 0–89 or unread, b1 = 90–100. On the pilot's 50 records both buckets pass the gate and
    the accuracy gap is largest (33% vs 78%). The gate and the cut are rechecked on stage 2's 300 calibration records
    before any stage-2 test question; if a different cut then separates the buckets clearly better, stop and ask.
  - **(b) Gemini's thinking is fixed at `low`**, recorded per call. The pilot's 50 calibration questions are re-graded
    and re-sorted at `low` (no new primary or Opus calls), so every grade comes from one grader configuration. The
    unhonoured-"off" records stay in the log, marked superseded.
  - Then build the pilot's calibration Counts under these rulings, show the posterior over the Globals and S15's
    disclosure, and stop for the owner's go on the pilot's test half.

- **2026-09-28, "The pilot, built", items 1–8:** confirmed as proposed, with two clarifications.
  - **7:** stage 2's calibration is all 300 records, the pilot's 50 and stage 2's 250, shipped as one set of Counts;
    the stage-2 gate reads all 300.
  - **8:** the verdict covers the whole 300-question test split, pilot included, so the 60-grade audit is drawn from
    all 300 (10 per domain).
  - The code already did both (stage 2 reads the pilot's records from the same run directory); a test now pins it.
- **2026-09-28, after review of PR #1, before any frozen call** (not the owner's ruling; recorded for the owner):
  - **Item 4 tightened.** The confirmed rule reserved the most a call had cost so far, which a single long call
    (up to max_tokens) could exceed, so a cap could be passed by up to one call's worst case. The wallet now reserves
    the worst case, so 2.14's "stop if either cap would be exceeded" holds exactly. It stops up to $0.50 short of a cap.
  - Every call is written to `calls.jsonl` the moment it returns, so a question cut off by a cap, a truncation or a
    changed model still has its paid calls logged (rule 5).
  - The Anthropic and OpenAI clients no longer retry on their own; a failure surfaces, and its reservation stands.
  - A go or a `listed` must be a non-empty string: `false` or `0` is refused.

- **2026-09-28, the rest of the pre-registration** (the later rulings of the day supersede the earlier 2.3 and 2.14):
  - **2.3:** the primary is `gpt-5.5-2026-04-23`, the dated snapshot, pinned by exact string after verifying it
    against OpenAI's list on the day. Low reasoning effort, recorded per call. The board says "gpt-5.5 at low
    reasoning effort".
  - **2.9:** the grader is `gemini-3.8-flash`, with AA's grading prompt verbatim. Reasoning is off if the API
    allows it; otherwise it is fixed at low, and that is recorded. The board says "re-scored with gemini-3.8-flash,
    not AA's grader". The owner hand-audits 60 grades, 10 per domain, before the verdict line is written.
  - **2.7:** one equivalence call per question to the grader model. It sorts the read, the samples and the second
    opinion into classes, with "decline" as its own class, and k and s read those classes. The prompt is fixed in
    the pre-registration (below).
  - **2.6:** three agreement samples. Agreement is "all three in the read's class, or not", and the World stays as
    ruled in 2.16 and 2.25.
  - **2.5:** a separate confidence call, as proposed. The buckets are as ruled in 2.15: cut at 80, unread → low.
  - **2.11:** applies to the threshold baseline only.
  - **2.12:** the second opinion is `claude-opus-5-5`, verified against the list on the day. Key
    `ANTHROPIC_API_KEY`.
  - **2.13:** the claims as written. The board states in advance that p = 10 is underpowered at 300 test questions.
  - **2.14:** two stages.
    - Stage 1 is a pilot of 100 questions (50 calibration, 50 test), capped at $15.
    - Stage 2 is the remaining 500, only on the owner's go after the owner has seen the pilot.
    - The whole run is capped at $80, and it stops if either cap would be exceeded.
    - The pilot takes 8 or 9 per domain, the two extras chosen by the seed, drawn from 2.1's 300/300 split, so
      stage 2 plays the other 500.
    - Seeds as proposed.
  - **2.1, 2.2, 2.4, 2.8, 2.10:** as proposed.
  - **When the accounts are funded:** verify and pin every model string with the date; draw the calibration split;
    print its confidence histogram and bucket shares (the gate); re-estimate the dollars with the equivalence
    calls. Then stop for the owner's go.

- **2026-09-28:**
  - **2.25:** option A. κ ∈ {0, 1/2, 9/10}, uniform, `elicited` (`owner.toml` `globals.corr`), learned from the
    calibration records. S15's disclosure and E7's lines are printed for the World that carries it.
  - **Providers:** the owner funds the OpenAI account; the pre-registered primary stands. When the account is live,
    every model string is verified against the providers' lists and pinned with the date. A Gemini grader, if
    proposed instead, is named `gemini-3.8-flash` by exact string.
  - **The waiver** of the bucket gate for both dry runs was right.
  - **Nothing frozen is called until the owner says go.**

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

### wald's episode cost grows with the Counts (stage 2, 2026-09-30)

wald v0.2.1 computes exactly. An episode's prior is P(Global | Counts) P(local | Global), with P(Global | Counts)
proportional to the prior times each Global's likelihood of every record in the Counts: products of rationals
raised to the records' multiplicities. Numerators and denominators lengthen roughly in proportion to the number of
records. Big-integer multiplication costs more than linearly in length, so an episode costs more as a plate's
Counts grow.

Measured, 1,152 Global values:

| Counts at the episode | seconds an episode | where |
|---|---|---|
| 50–100 records (the pilot) | 5.3 | steel, alone |
| about 300 records (stage 2's first 25) | 22–30 | droplet, 21 at once; steel, 3 at once |
| about 575–600 records (stage 2's last 25) | about 41 | droplet, 21 at once |

A whole learning plate of 300 episodes took 2.5–4.2 hours. Episodes from the declared prior with no Counts took
under a tenth of a second each (300 in 15–40 s).

Memory goes the same way. The lookahead memo (`World.work()`) is kept for a World's life, keyed by exact beliefs.
On a plate that learns, no key recurs, and it grew about 0.25 GB an episode, past 250 GB for 21 plates. The harness
drops it between episodes, which is not a wald API. **For wald:** should a plate own the memo, or clear it when its
Counts change, since then no earlier key can recur? Nothing here bends a rule. Every act still comes from `Plate.run`,
exactly. It bears on wald's scale: boards far past 600 records at this many Globals will want something from
wald, for example a sufficient-statistic form of the Counts' likelihood or a bound on its size. That is wald's to
decide, and this board only reports it.

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
