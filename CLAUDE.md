# wald-millionaire — how this repository works

This repository plays "Who Wants to Be a Millionaire" with a Bayesian decision-theoretic contestant whose knowledge is an LLM. The contestant's decisions are made by `wald` (github.com/gfrmin/wald), consumed as a library at a signed release; the law it decides under is in github.com/gfrmin/wald-charter (`CHARTER.md`, `CHARTER-v0.1.md`, `SURFACE.md`, `SURFACE-v0.1.md`). Read `briefs/001-millionaire.md` fully before anything else.

## Rules

1. **wald decides; nothing else does.** Every act the wald contestant takes comes from `wald.run` on a pack. No code in this repository ranks options, compares probabilities, or picks a lifeline on its own, except inside the two baselines, which are labelled as baselines and never called by the contestant.
2. **No probability outside a pack.** Reliabilities, priors, values of the ladder: cells in packs under `packs/`, each with a source (`data`, `elicited`, `fitted`) and, for `fitted`, its held-out score. Python holds counts (right/wrong) and dollars; it does not hold a `0.83`. Calibration writes packs; it does not keep floats for the contestant to read.
3. **Packs are generated, never edited.** `tools/make_stage_packs.py` writes all 120 stage packs from the ladder, the fitted reliabilities and the scored tables. A change to a pack is a change to the generator.
4. **wald is pinned.** `pyproject.toml` pins `wald` to a signed release tag (`v0.1.0` when it exists). Until it exists, nothing under `contestant/` is written; see the boundary below.
5. **Every spend is logged.** Each instrument call records model, tokens, dollars, latency, question id, tier. The scoreboard prices the act at the declared price, whether or not a cache served it.
6. **The owner's numbers are the owner's.** Ladder, λ_usd, models, question set, counts: from the brief, never chosen here. A missing number is a question in `QUESTIONS.md`, not a default.
7. **Report what it says.** The scoreboard prints the result as measured. Nothing is tuned to make wald look better; a baseline that wins is reported as winning.
8. **Keys from the environment**, never in the tree. `LLM_API_KEY` names; the loader fails loud without them.
9. **Layout.** `oracle/` the exact game DP (pure Python); `baselines/` the LLM-plays-directly and always-answer contestants; `calibration/` the instrument runs and their tables; `packs/` generated stage packs; `contestant/` the wald contestant and its Door; `tools/` generators and the scoreboard; `SCOREBOARD.md` the result; `QUESTIONS.md` what stopped you.

## The boundary while wald 0.1.0 is not yet released

Everything except `contestant/` and `tools/make_stage_packs.py` can be built and tested now: the oracle, the baselines, the calibration harness, the question-set loader, the scoreboard's tables. The oracle is the contract the contestant will be judged against, so write it first and prove it on the prototype's numbers (`proto.py` in this repository; its `stage_world` and `solve_game` give the shape).
