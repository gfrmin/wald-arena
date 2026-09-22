# wald-millionaire — brief 001: "Who Wants to Be a Millionaire", played by wald with an LLM as its knowledge

A new public repository, the first consumer of `wald` as a library (`wald==0.1.0`, `wald.law` = charter-v0.1 / surface-v0.1). The repo is judged by its own scoreboard and by wald's law: every World it plays is a pack `wald.load_pack` accepts, every number in a pack is housed and sourced, and no host code holds a probability (S1) — the LLM's reliabilities are `fitted` cells with held-out scores, never a float in Python.

**Done when** the scoreboard prints, for N games on a held-out question set: expected and realised winnings per game, dollars spent on instruments, lifeline use by rung, walk-away rungs — for the wald contestant, for the same LLM playing the game directly, and for "always answer" — and every pack the games used passes `wald.load_pack`.

**The owner's numbers** (you choose none; TBD ones are the owner's to rule before play):
- Ladder: TBD (the US 15-rung ladder $100 → $1,000,000 with safe havens at Q5 $1,000 and Q10 $32,000 is the prototype's).
- λ_usd: utility per dollar of instrument spend — TBD (the prototype charged $1 per LLM read).
- Models: the contestant's LLM (the `llm` instrument) and the "friend" (the `phone` instrument, a second model) — TBD.
- Question set: a labelled multiple-choice set with a difficulty tier per question, four options, one right — TBD (sourced by the owner; tiers may be assigned from a separate model's accuracy if the set carries none, said so in the pack's comment).
- Calibration: 200 questions per tier held out from play, tiers 3 (easy Q1–5, medium Q6–10, hard Q11–15).
- Games: 500 per contestant, questions sampled by tier from the held-out play set, seed in the scoreboard.

## The World

One **stage World per (rung r, lifelines held L)** — 15 × 8 packs, generated, never hand-written:

- Ω = {A, B, C, D}, the right option. Prior uniform (`elicited`).
- Terminal acts: `answer X` for each X — u(ω, answer X) = V(r+1, L) if X = ω else SAFE(r); `walk` — u = LADDER[r−1]. V is the value of the next rung's World with the lifelines held, computed backward from Q15 (V(15, ·) = the top prize); these cells are `fitted` (derived from the ladder and the fitted reliabilities by the generator), sourced as such, with the generator as their provenance.
- Observational acts, all `once`: `llm` — the contestant's model asked the question; kernel names the truth with ρ_t (fitted per tier), else one wrong option uniformly; price = cost per call × λ_usd. `fifty` — kernel exact: keeps the truth and one wrong option uniformly, outcome the pair. `phone` — the second model, ρ_p,t fitted. `audience` — TBD instrument (a third model or a poll of k weak reads), ρ_a,t fitted.
- **Lifeline prices are option values [J1]**: price(l at r, L) = V(r+1, L) − V(r+1, L∖{l}). Using a lifeline now costs what having it later was worth. This is an approximation of the full game (the exact treatment is a 15-stage decision problem); **J2**: the repo carries the exact game DP as an oracle (`oracle/game.py`, a stage tree per rung over the four instruments' outcome histories) and prints the wald contestant's regret against it. Prototype: both agree to the dollar at the rungs checked; the brief's first measurement is whether they agree everywhere.
- Horizon N = 4 (one read of each instrument at most), depth d = N: the stage World is small enough to solve exactly, so no floor and no think act. That's a finding to record, not a loss: the interesting prices here are the lifelines', not computation's.

## Calibration (before any game)

For each instrument and tier: run it on the calibration questions, count right/wrong, fit ρ as the posterior mean under Beta(1,1), score held out (log score on a further 100 questions per tier), write the six ρ cells with source `fitted` and their scores as `score(…, of=…)` — one scored table per instrument. The 50:50 kernel needs no calibration. Print the calibration table on the scoreboard. If a model's accuracy on a tier is below 1/4 + 0.05, its reads are worthless there and the generator must price the act above any gain (the World refuses nothing; the numbers decide).

## The contestants

1. **wald**: at each question, `wald.run` on the stage pack for (r, L) against a Door whose `outcome` fires the real instrument (an API call for `llm`/`phone`, the exact rule for `fifty`) and whose `fire` records the answer or the walk. Winnings realised by the game's rules.
2. **The LLM playing directly**: the same model prompted with the rules, the ladder, its remaining lifelines and the question, asked for one of {answer X, use lifeline l, walk}, in a loop. Same questions, same seed.
3. **Always answer**: read `llm` once, answer its report, never walk, never use a lifeline.

## Scoreboard

Per contestant: mean and distribution of realised winnings; expected winnings under the model (wald's V(1, all) beside the realised mean — a calibration check on the whole World); instrument spend per game; lifeline use by rung; walk-away rungs; wrong-answer rungs. Then wald's regret against the exact game DP (J2). Report the result as it is.

## What this teaches for the agent

The two hard parts of the QA-frontier result, in a legible setting: an LLM as a **calibrated instrument** (fitted ρ with held-out scores, per difficulty) and **priced information** (a lifeline's option value, a read's dollar cost). Both are reused as-is in the next brief.

Prototype (author-side, illustrative ρ, `proto.py`): wald $294.5k per game, always-answer $211.4k; first act at every rung `llm`, then walk or lifeline by the numbers; 50:50's option value grows from $72k at Q1 to $993k at Q13.
