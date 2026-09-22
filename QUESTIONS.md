# Questions for the owner

Numbers and rulings the brief leaves open. Nothing below is defaulted in code: `owner.toml` holds what has been
ruled, and a missing key fails loud where it is needed. Each open question blocks only what it names.

## Open

1. **λ_usd** (`lambda_usd`): utility per dollar of instrument spend. Blocks: every price, hence the stage packs,
   the oracle's play, the expected-winnings column and the regret table on real numbers.
2. **Models** (`instruments.{llm,phone,audience}.model`): the contestant's LLM, the friend, and the audience.
   The audience instrument is still "a third model or a poll of k weak reads"; the code treats it as one model
   call until ruled. Blocks: calibration, all play. If a model is not Anthropic's, it needs its own transport in
   `calibration/instruments.py` (only the Anthropic one exists).
3. **Declared price per call** (`instruments.*.usd_per_call`): rule 5 prices every act at its declared price,
   cached or not. One number per instrument, in dollars. (Token counts are logged too, so a per-token rate can
   be audited against it.)
4. **Question set** (`questions.path`): the owner's labelled set. The loader (`data/questions.py`) reads JSONL,
   one question per line:
   `{"id": "q0001", "text": "…", "options": {"A": "…", "B": "…", "C": "…", "D": "…"}, "answer": "C", "tier": "easy"}`
   with `tier` in `easy | medium | hard`. If the set carries no tiers, say so and name the model whose accuracy
   assigns them. Each tier needs at least 300 questions (200 calibration + 100 held-out) plus a play pool.
5. **Seeds**: `split_seed` (calibration / held-out / play split) and `games.seed` (question draw and 50:50 draws for
   the 500 games). The kickoff says the split seed is "in the brief"; the brief only says the game seed goes on
   the scoreboard.
6. **Unparseable replies.** An instrument reply that is not a single letter is recorded as `?`. In calibration it
   counts as wrong (conservative, and it is in the count the fit sees). In play it is an observation with no
   information: the belief stays where it was, and the act (and lifeline, if one was spent) is still paid.
   Always-answer, given `?`, answers A. Confirm, or rule otherwise.
7. **Phone and audience after a 50:50.** Are they shown the two remaining options? The oracle's kernel, like the
   brief's, has them report over all four options independently of the 50:50. If they see the reduced question,
   that is a different instrument and needs its own calibration.
8. **The ladder's intermediate rungs.** The brief names "the US 15-rung ladder, $100 → $1,000,000, havens $1,000 and
   $32,000"; `owner.toml` carries the classic values 100, 200, 300, 500, 1,000, 2,000, 4,000, 8,000, 16,000,
   32,000, 64,000, 125,000, 250,000, 500,000, 1,000,000. Confirm.
9. **What the LLM-plays-directly prompt says about cost.** It is told the rules, the ladder, its lifelines and the
   question (the kickoff's list), not that each decision and each phone/audience call is charged λ_usd × its
   price. Its utility is scored with those charges like everyone's. Should the prompt state them?

## Ruled

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

This is the approximation's regret, measured by the oracle (`oracle/game.py`, `regret_table`) at rung 1 with all
lifelines held:

| game | exact | wald estimate | wald realised | regret |
|---|---|---|---|---|
| prototype (proto's ladder and ρ, read on the menu), $k | 308.556 | 294.547 | 297.657 | 10.899 |
| brief ladder, read first, proto's illustrative ρ, $1/read, phone/audience free, $ | 38,110 | 36,507 | 37,050 | 1,060 |

The regret is positive at every rung but the last (where there is no future to misprice). It is the reason the
per-question World is an approximation and the oracle is carried alongside it: the scoreboard prints it on the
owner's fitted numbers.
