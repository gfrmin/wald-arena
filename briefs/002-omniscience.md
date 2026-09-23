# wald-arena — brief 002: AA-Omniscience, answered, switched or abstained by wald

The first showcase: wald entered on a public board. The board is AA-Omniscience (Artificial Analysis): short
factual questions with free-text answers, where a wrong answer costs and an abstention does not. wald is consumed
at `wald==0.1.0` (`wald.law` = charter-v0.1 / surface-v0.1 / kit-v0.10). Everything the contestant believes sits in
generated packs `wald.load_pack` accepts, with every kernel `fitted` and scored on held-out questions. The host
holds counts and dollars, never a probability.

**Done when** the scoreboard prints, for each penalty p and each second-opinion price point, on the sealed test
split: every contestant's score under p (the Omniscience Index generalised below), its coverage (share answered),
its accuracy and hallucination rate as AA defines them, its dollars per question by act, and wald's realised
utility beside the utility its packs expected. The calibration table carries its held-out scores; every pack
passes `wald.load_pack`; the four pre-registered claims (QUESTIONS.md, 2.13) are each marked **held** or
**missed**. Nothing reaches a frozen model until the pre-registration is ruled (QUESTIONS.md).

**The owner's numbers** are the pre-registration in `QUESTIONS.md` (2.1–2.14). They are ruled there, written to
`showcases/omniscience/owner.toml`, and never chosen here. Until then that file holds no instrument, so no code can
reach the frozen models.

## The board, as measured on 2026-09-23

- **Questions.** `ArtificialAnalysis/AA-Omniscience-Public` on Hugging Face, revision
  `e4883edbb9f5ccf2b2a8fdc6fb65e01a58e99849` (2026-08-24). Apache-2.0. 600 rows,
  `AA-Omniscience_dataset_public.csv` (sha256 `1e04603d…d02f`), 100 per domain (Finance, Health, Humanities and
  Social Sciences, Law, Science Engineering and Mathematics, Software Engineering), with fields `domain`, `topic`,
  `subtopic`, `question_id`, `question`, `answer`. Answers are short: dates, names, numbers, identifiers. The public
  set is AA's 10% sample of 6,000; AA calls it "sufficient to get an indication of overall model performance …
  results at domain or category level should not be considered reliable".
- **Answering.** AA's answer prompt tells the model to answer "with JUST the answer (no explanation)", and that
  if it does not know, "it is better that you say this than get the wrong answer". The README gives the
  placeholders as `{domain}`/`{subtopic}`; the paper (arXiv 2511.13029, App. A.1) gives them as
  `{topic}`/`{category}`. See 2.4.
- **Grading.** A model grades each answer against the gold target as CORRECT, INCORRECT, PARTIAL_ANSWER or
  NOT_ATTEMPTED, using a published prompt with seven worked examples (README, and paper App. A.2).
  **The Index**: OI = 100·(c − i)/(c + p + i + a). PARTIAL and NOT_ATTEMPTED count in the denominator only.
  Accuracy = c/n. Hallucination rate = i/(p + i + a).
- **AA's grader cannot be called any more.** AA graded with Google's `gemini-2.5-flash-preview-09-2025` (with
  reasoning). That model is not in Google's model list today. `gemini-2.5-flash` (GA) is. AA publishes the prompt
  and runs no grading service. So no score produced now is graded the way the published board was graded. Any
  comparison with the board's published numbers holds only through a grader we name; that is 2.9, and it is the
  owner's ruling.
- **Models on the APIs today** (listed, 2026-09-23T03:02Z, with no completion made): `gpt-6-astra` (an alias with
  no dated snapshot listed), `gpt-5.5` (with `gpt-5.5-2026-04-23`), `claude-opus-5`, `claude-haiku-4-5-20251001`,
  `gemini-2.5-flash`. List prices per million tokens, input/output: `gpt-6-astra` $10/$50; `gpt-5.5` $5/$30;
  `claude-opus-5` $5/$25; `claude-haiku-4-5` $1/$5; `gemini-2.5-flash` $0.30/$2.50 (thinking billed as output).

## The score under a penalty

A question's utility is +1 for a CORRECT answer, −p for an INCORRECT one, and 0 for an abstention. PARTIAL
counts 0, as in the Index (2.8 asks the owner to confirm this at every p). At p = 1 the mean utility × 100 *is*
the Omniscience Index. At p = 3 and p = 10 a hallucination costs three and ten times a right answer. The stake is
that ratio: a second opinion "priced near the stake" costs about as much, in utility, as one right answer.
Utility is dimensionless per question. Dollars enter through λ_usd (2.10): an act's price is its declared dollars
per call × λ_usd.

## The World

Two stages per question, generated per (confidence bucket b, penalty p, second-opinion price point c). This is
the stage chain brief 001 used for rungs, now for one decision that may continue.

**The read (always paid, before any World).** The primary instrument answers with AA's prompt, then is asked its
confidence in that answer (2.5), which falls in bucket b. Its answer is the one AA's board would have graded. If
it declines (NOT_ATTEMPTED), b is the bucket `declined` and `answer primary` is not an act.

**Stage 1**, Ω₁ = the primary answer's grade g₁ ∈ {right, zero, wrong}. Here *zero* is PARTIAL (or
NOT_ATTEMPTED on the declined bucket), and utility is +1 / 0 / −p.
- Prior P(g₁ | b): `fitted`.
- Terminal acts: `answer primary` (u = +1, 0 or −p by g₁); `abstain` (u = 0); and `consult second`. That last one
  is worth V₂(g₁) − c: the value of the stage-2 World, solved by the generator, conditional on g₁, minus the price.
  Its cells are `fitted`, derived from the joint kernel, with the generator as provenance — the J1 of brief 001, and
  exact here, because stage 2 ends the question. **[J1]**
- Observational act `agreement` (`once`): five more samples of the primary instrument (2.6). The outcome is
  k ∈ {0, …, 5}, the number that match the read's answer (2.7). Kernel P(k | g₁, b) is `fitted`. Price: 2.6.

**Stage 2** (after `consult second`). The second opinion answers the same question under the same prompt and is
graded like any answer. Ω₂ = (g₁, g₂), both answers' grades. Terminal acts `answer primary` (u by g₁),
`answer second` (u by g₂), `abstain` (0). The prior is P(g₁, g₂ | b, s[, k]), where s ∈ {same, different,
declined} says whether the second answer matched the first. It is `fitted` from the **joint** table of the two
instruments' graded outcomes, never from two accuracies multiplied (2.12). `agreement` is still offered if it was
not bought in stage 1.

This is the owner's Ω with the grades kept. When the second answer is the same, g₁ = g₂ and the acts collapse to
`answer`/`abstain` over {right, wrong}: brief 001's binary World. When it differs, the states that carry mass are
the owner's three — primary right, second right, neither — plus "both right, worded differently", which the grader
can find and a string match cannot. A threshold on confidence can only lower coverage. `answer second` is the act
it does not have.

**Two assumptions, each measured rather than assumed silently:**
- Within a stage the kernels multiply. The World treats k and s as independent given (g₁, g₂, b). The fit scores
  that product against the joint table directly, on held-out questions, and prints the difference. **[J2]**
- The two-stage split is exact only if stage 1's value of consulting is the stage-2 World's value. The generator
  solves both, and the exact joint decision (both observations, every order) is solved alongside as an oracle, as
  in brief 001. wald's regret against it is printed.

**The second-opinion price grid is a re-solve, not a re-run.** Every calibration and test question has its second
opinion and its agreement samples recorded once, at the real declared price. Each price point c in the grid is a
set of generated packs over the same fitted kernels. Evaluating wald at c charges c for each consult it chooses,
and makes no new call. A grid of ten prices costs what one does.

Horizon: at most two observations and one continuation, solved exactly: no floor, no think act.

## Calibration (before any frozen-model spend on the test split)

On the calibration split, per bucket, count the joint table over (g₁, k, s, g₂) from the recorded reads, samples,
second opinions and grades. Fit every kernel cell as a Beta(1,1)-smoothed count (Dirichlet-smoothed, one
pseudo-count per outcome, for multi-outcome kernels; 2.11). Cells thinner than the owner's minimum count
collapse bucket first, then k to {0–2, 3–4, 5} (2.11). Each backed-off cell is printed. Score held-out with
`arena.calibration.held_out_log_score`: the same function that scores Millionaire's reliabilities, by k-fold within
the calibration split (2.1), so the numbers compare. Write every cell `fitted` with its score. **The test split is
sealed until the fit is written and committed**, and the standard errors in 2.1 are then recomputed from the fitted
kernels before it is opened.

## The contestants

1. **wald**: per question, `wald.run` on the stage-1 pack for (b, p, c), and on consulting, the stage-2 pack for
   what was seen. The Door's `outcome` serves the recorded agreement samples and second opinion; its `fire`
   submits the chosen answer or the abstention.
2. **The raw model**: the primary's read as AA would score it — its answer, or its own abstention.
3. **The calibrated threshold**: answer the primary's read iff its bucket's fitted P(right) clears p's break-even,
   p/(1 + p) (PARTIAL at 0). It uses the same read and the same fitted table, and buys nothing.
4. **The better single model**: whichever of the primary and the second opinion scored higher under p on the
   calibration split, answering raw on the test split, at its own read's price.

Contestants 2–4 are baselines, and nothing of theirs reaches wald (rule 1).

## Scoreboard

Per p × c × contestant: score under p (and the Index at p = 1), coverage, accuracy, hallucination rate, dollars
per question by act (read, agreement, second opinion, grading), and wald's expected utility beside its realised.
Then the calibration table with held-out scores and the J2 independence contrast, wald's regret against the exact
joint decision, and the grader line: which model graded, and that it is not AA's. Every call is at its declared
price. Grading is one call per distinct (question, answer), shared by all four contestants and counted once.

## What this teaches for the agent

Calibration is a purchase under a stake. The confidence read decides whether the answer is worth giving. A
correlated second opinion is priced by what it changes jointly, not by its own accuracy. And the one act that
beats a threshold is switching answers, which only a World that holds both answers can take.

Prototype (dry run, `claude-haiku-4-5-20251001` in every role, self-graded, degenerate): see SCOREBOARD.md's
omniscience section. It proves the plumbing and nothing about the fit.
