# Session 1 — kickoff (paste as the opening message)

Read `CLAUDE.md`, then `briefs/001-millionaire.md`, then `proto.py`. wald 0.1.0 is not released yet, so this session builds everything on the near side of the boundary in `CLAUDE.md` and nothing on the far side.

Deliverables, in this order, each its own commit with tests:

1. **`oracle/game.py` — the exact game.** A 15-stage decision problem: at each rung, a stage tree over the four instruments' possible outcomes (the LLM read, 50:50, phone, audience; each at most once per game for the lifelines, once per question for the read), with terminal acts answer/walk and the ladder's rules (safe havens). Exact rationals (`fractions.Fraction`), no floats. Inputs: ladder, reliabilities per tier per instrument, instrument prices. Output: the expected winnings from any (rung, lifelines held) and the optimal act at the root of any stage given the outcome history. Prove it against `proto.py`: with the prototype's illustrative reliabilities the per-stage wald value at rung 1 with all lifelines is $294.5k; the exact game's value must be ≥ that (it is the optimum), and the difference is the option-value approximation's regret — print it. Then a test that at a single-rung game the two coincide exactly.

2. **`baselines/always_answer.py`** — read the LLM once, answer its report, never walk, never use a lifeline. Expected winnings by backward induction as `proto.py`'s `A(r)`; realised winnings from a game log.

3. **`baselines/llm_direct.py`** — the same model prompted with the rules, ladder, remaining lifelines and the question, asked for exactly one of `answer X` / `use fifty|phone|audience` / `walk`, looped until the game ends. Parse strictly; an unparseable reply is a walk and is counted. Log every call (rule 5).

4. **`calibration/run.py`** — for one instrument and one tier: ask each calibration question, record right/wrong, write `calibration/<instrument>.jsonl` with question id, tier, report, truth, tokens, dollars. Then `calibration/fit.py`: counts → Beta(1,1) posterior mean as an exact rational, held-out log score on the held-out slice, and an output the pack generator will read. No float leaves `fit.py` as a reliability: `Fraction` in, `Fraction` out. Dry-run mode that replays a recorded jsonl without calling any API, for tests.

5. **`data/questions.py`** — the loader for the owner's question set (`QUESTIONS.md` if its shape is unknown): id, text, four options, the right one, tier; the split into calibration / held-out-score / play, by a seed in the brief.

6. **`tools/scoreboard.py`** — the table skeleton from the brief's Scoreboard section, filled by whatever contestants exist; the wald rows print "not yet".

Stop after 1 and show me the regret number before building 2–6. Where the brief is silent on a number, ask in `QUESTIONS.md` and continue with the rest. Do not write anything under `contestant/` and do not add `wald` to `pyproject.toml` in this session.
