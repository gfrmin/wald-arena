# wald-arena — brief 002: AA-Omniscience, answered, switched or abstained by wald

The first showcase: wald entered on a public board. The board is AA-Omniscience (Artificial Analysis): short
factual questions with free-text answers, where a wrong answer costs and an abstention does not. wald is consumed
at `v0.2.1` (`wald.law` = charter-v0.2 / surface-v0.2 / kit-v0.13). Everything the contestant believes sits in
generated packs `wald.load_pack` accepts. What it learns about its instruments it learns inside the law, as Counts
on a plate. The host holds counts and dollars, never a probability.

**Revision 2 (2026-09-25): re-planned on wald 0.2.** CHARTER v0.2 lets a World learn across episodes. The
calibration script this brief first planned, a Dirichlet fit in Python written into two-stage packs as `fitted`
cells, is replaced by Globals learned from Counts, with the grader as the After-act. The first plan is in git
history (2ea36a4, def8698); the sections below supersede it.

**Done when** the scoreboard prints, for each penalty p and each second-opinion price point, on the sealed test
split: every contestant's score under p (the Omniscience Index generalised below), its coverage (share answered),
its accuracy and hallucination rate as AA defines them, its dollars per question by act, and wald's realised
utility, E7's lines and S15's disclosure for every plate, and the Score of the shipped calibration. Every pack passes
`wald.load_pack`; the four pre-registered claims (QUESTIONS.md, 2.13) are each marked **held** or **missed**. Nothing reaches a frozen model until the pre-registration is ruled (QUESTIONS.md).

**The owner's numbers** are the pre-registration in `QUESTIONS.md` (2.1–2.14, and 2.15–2.24 for revision 2). They are ruled there, written to
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

## The World (revision 2)

**Episode and plate.** Each question is one episode. Every test question, played under one declaration (one
penalty p and one second-opinion price c), is one plate: the Counts it writes persist from question to question,
and nothing else does (C2.S13). The plate starts from the calibration split's Counts, shipped in the pack (below).
Questions enter the plate in a seeded order (2.20), because what wald has learned by question n depends on which
questions came before it.

**Always paid, outside the World.** The primary reads the question with AA's prompt, then is asked its confidence
(2.5). The read is the answer AA's board would grade, and the raw model's act. Its bucket is served to the World by
a free act.

**The local**, drawn afresh each episode from P(local | Global):
- `b`, the read's confidence bucket (2.5), with `unread` for an unparseable confidence.
- `t`, which answer is right: `primary` (the read; when the second opinion agrees, both are), `second` (the
  second opinion's answer and not the read), or `neither`. This is the owner's three-way Ω. A read graded
  PARTIAL or NOT_ATTEMPTED is not right, so it falls under `second` or `neither` (2.18).
- `s`, whether the second opinion's answer matches the read (2.7): `same` or `different`. It is `different`
  whenever `t = second`, since two matching answers are both right or both not.

P(local | Global) = P(b) · P(t | b, Global) · P(s | t, Global), where
P(t = primary | b) = ρ_b, P(t = second | b) = (1 − ρ_b)·σ, P(s = same | t = primary) = α and
P(s = same | t = neither) = β. P(b) is declared, not learned (2.17).

**The Globals**, each a declared grid of named hypotheses (2.15), with P(Global) uniform over the product
unless the owner rules otherwise:
- `calib`: the primary's reliability given its confidence, ρ_b for every bucket.
- `agree`: what the agreement samples say, a⁺ = P(all five match the read | the read is right) and
  a⁻ = the same given it is not.
- `second`: the second opinion's reliability *jointly with the primary's*. σ is how often it is right when the read
  is not. α and β are how often it matches the read when the read is right and when both are wrong. β is the
  correlated-error channel that brief 002's J2 was about. Here it is a Global the plate learns, not a fit's
  assumption.
- `grader`: γ = P(the grader's verdict is right). A grader assumed perfect can hide a misdeclaration from every
  record-reading check (C27; appendices J and K). With γ a Global, S15 shows any confound between the grader and
  an instrument that a second grid point reproduces.

No utility reads a Global (C2.S11).

**Acts.** N = 3, d = 3, every act `once`:
- `confidence`: `point(b)`, price 0, because its call is paid outside the World.
- `agreement`: five more samples of the primary. Outcome `all` (all five match the read) or `some`, with
  kernel a⁺ or a⁻ by `t`. Price: 5 × the primary's declared price × λ_usd (2.6).
- `second_opinion`: the second instrument answers with AA's prompt. `point(s)`, price c.
- terminals: `answer_primary` (+1 if `t = primary`, −p otherwise), `answer_second` (+1 if `t = second`, or
  `t = primary` and `s = same`, −p otherwise) and `abstain` (0).

**The grader is the After-act** (`grade`, C2.S12). It is taken at the end of every episode, whenever declared, at
the grader's declared price × λ_usd. It grades the answer the end submitted, and on `abstain` it grades the read,
since an abstention is an end like any other (S12). It reports `right` (CORRECT) or `not` (anything else) with
reliability γ. It changes no earned utility and adds no value to any act (S12). What it buys is what the plate
learns, and a check on the model.

**Where this is an approximation, each named for the owner:**
- `answer_second` can be fired without `second_opinion`, and the World prices it at 0. The door then buys the
  second opinion, and the scoreboard charges c for it. wald's blind switches are counted and their undercharge
  printed (2.19).
- Agreement is binary (all five match or not), and its kernel reads `t` alone. Given `t`, the agreement samples
  are declared independent of the bucket (2.16).
- The episode decomposition (C2.J21): wald maximises within a question, never acts in order to learn. E7 prints
  that price where the kit's size bound admits it. At this World's size it does not, and the scoreboard says so.

## Calibration: shipped Counts (revision 2)

No reliability is fitted in Python. The calibration Counts are constructed from the calibration split, as ruled
(2.21). There is one record per question, with every instrument drawn:
`confidence`, `agreement`, `second_opinion`. Then comes an end, and the grade of the answer that end submits. The end
reads only what the record shows, never a grade, so the design is ignorable (C2 §4). When the two answers match, the
end submits the read. When they differ, the records alternate in question order between submitting the read and
submitting the second opinion. Declaring a pack that ships them checks that every record is realisable under the
test declaration and the whole multiset possible under some Global value (S13): wald refuses it `PLATE` otherwise.

Every test pack ships the same Counts inline (V2.6), with their digest (V2.13) and their Score (C2.S14, V2.8). The
Score is the leave-one-out predictive probability of the shipped records. The Score and the digest are wald's own,
`wald.score` and `wald.digest` (v0.2.1); the Score comes back as text, as the pack writes it, however many digits.
wald recomputes both at declaration, and a pack whose numbers differ is refused `UNSCORED` or `PLATE`.

**Before any test question is played**, the runner prints the calibration split's confidence histogram and each
bucket's share of the calibration records. It stops for the owner if a bucket holds under a fifth of them (2.15 as
ruled).

**The test split is sealed until the calibration Counts are written and committed**, and the SE of 2.1 is
recomputed from them before the test plate opens (2.1).

## The contestants

1. **wald**: per question, `Plate.run` on the test pack for (p, c), behind a Door. The Door's `outcome` serves the
   bucket, the agreement samples' match (`all` when k = 5), the second opinion's match, and the grade of the
   fired answer. Its `fire` submits the chosen answer or the abstention.
2. **The raw model**: the primary's read as AA would score it — its answer, or its own abstention.
3. **The calibrated threshold**: answer the read iff its bucket's P(right) − p · P(wrong) > 0, where P is the
   Dirichlet(1) mean of that bucket's graded reads (right, partial or declined, wrong) on the calibration split.
   It uses the same read and buys nothing.
4. **The better single model**: whichever of the primary and the second opinion scored higher under p on the
   calibration split, answering raw on the test split, at its own read's price.

Contestants 2–4 are baselines. They compute their numbers in Python, labelled as baselines, and nothing of theirs
reaches wald (rule 1).

## Scoreboard (revision 2)

For each p × c and each contestant: the score under p (and the Index at p = 1), coverage, accuracy,
hallucination rate, net utility, and the paired Δ against wald. Dollars per question by act: read, agreement,
second opinion, grading. Then, per plate:
- **S15's disclosure**, as `Plate.disclosure()` gives it. It is printed at declaration, before any result.
- **E7**:
  - every draw's line, grouped by the history in its episode that led to it. Each line is the total variation
    between the empirical law of its outcome and its posterior predictive, as an exact rational with a decimal
    display, as `wald.e7` writes it;
  - the plate's realised net utility with its Counts, and the same questions played from the declared prior with
    Counts never conditioned on;
  - the one-run maximiser's value, or the statement that the kit's size bound does not admit it;
  - the Score of the shipped Counts.
- **What the Counts moved**: wald's first act on the first test question with and without them, and how many test
  episodes took a different act. wald hands a host no P(Global | Counts), so the Global marginals are not printed
  (they were the kit's display before v0.2.1).
- **Every approximation named above, measured**: blind switches and their undercharge.
- The grader line: which model graded, and that it is not AA's.

## What this teaches for the agent

Calibration is a purchase under a stake. The confidence read decides whether the answer is worth giving. A
correlated second opinion is priced by what it changes jointly, not by its own accuracy. And the one act that
beats a threshold is switching answers, which only a World that holds both answers can take.

Prototype (dry run, `claude-haiku-4-5-20251001` in every role, self-graded, degenerate):
`showcases/omniscience/SCOREBOARD.md`. It proves the plumbing and nothing about the fit.
