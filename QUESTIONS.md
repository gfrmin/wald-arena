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

This is the approximation's regret, measured by the oracle (`oracle/game.py`, `regret_table`) at rung 1 with all
lifelines held:

| game | exact | wald estimate | wald realised | regret |
|---|---|---|---|---|
| prototype (proto's ladder and ρ, read on the menu), $k | 308.556 | 294.547 | 297.657 | 10.899 |
| brief ladder, read first, proto's illustrative ρ, $1/read, phone/audience free, $ | 38,110 | 36,507 | 37,050 | 1,060 |

The regret is positive at every rung but the last (where there is no future to misprice). It is the reason the
per-question World is an approximation and the oracle is carried alongside it: the scoreboard prints it on the
owner's fitted numbers.
