import random
import statistics
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction as F

from explainers.millionaire.baselines import always_answer
from explainers.millionaire.owner import havens, ladder, load
from explainers.millionaire.questions import draw_game, split
from explainers.millionaire.oracle.game import Game, tiers_by_fives
from explainers.millionaire.oracle.host import Decision, GameLog, fifty_outcome, play, simulated_fire
from explainers.millionaire.oracle.prototype import RELIABILITY
from tests.conftest import make_questions

OWNER = load()
USD = {"llm": Decimal("0.01"), "phone": Decimal("0.02"), "audience": Decimal("0.03")}
LAM = F(100)  # test value: utility per dollar, so a read costs $1 of winnings
BRIEF = Game(ladder=ladder(OWNER), havens=havens(OWNER), reliability=RELIABILITY,
             price={"llm": F(1), "phone": F(2), "audience": F(3), "fifty": F(0)}, tiers=tiers_by_fives(15),
             read_first=True)
QUESTIONS = make_questions(320)
PLAY = split(QUESTIONS, seed=3, per_tier=200, held_out_per_tier=100).play


def scripted(outcomes):
    "Fire from a script: outcomes[(instrument, rung)] -> outcome."
    return lambda k, q, r: (outcomes[(k, r)], None)


def test_rules_right_answers_reach_the_top():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    log = play(lambda v: Decision(f"answer {v.question.answer}"), "oracle-of-truth", 0, qs, BRIEF,
               lambda k, q, r: (q.answer, None), read_first=True)
    assert log.winnings == 1_000_000 and log.wrong_at is None and log.walked_at is None
    assert all(q.events == (("llm", q_.answer),) for q, q_ in zip(log.questions, qs))


def test_rules_wrong_answer_keeps_the_haven_and_walk_keeps_the_prize():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    wrong_at_8 = lambda v: Decision(f"answer {v.question.answer if v.rung < 7 else next(x for x in 'ABCD' if x != v.question.answer)}")
    log = play(wrong_at_8, "x", 0, qs, BRIEF, lambda k, q, r: ("A", None), read_first=True)
    assert log.winnings == 1000 and log.wrong_at == 7
    walk_at_4 = lambda v: Decision(f"answer {v.question.answer}" if v.rung < 3 else "walk")
    log = play(walk_at_4, "x", 0, qs, BRIEF, lambda k, q, r: ("A", None), read_first=True)
    assert log.winnings == 300 and log.walked_at == 3
    wrong_at_1 = lambda v: Decision(f"answer {next(x for x in 'ABCD' if x != v.question.answer)}")
    assert play(wrong_at_1, "x", 0, qs, BRIEF, lambda k, q, r: ("A", None), read_first=True).winnings == 0


def test_lifelines_are_spent_once_and_illegal_acts_are_invalid_walks():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    seen = []

    def greedy(v):
        seen.append(v.remaining)
        if v.rung == 0 and "fifty" in v.remaining:
            return Decision("fifty")
        if v.rung == 1:
            return Decision("fifty", raw="use fifty")  # already spent at rung 0
        return Decision(f"answer {v.question.answer}")

    log = play(greedy, "x", 0, qs, BRIEF, lambda k, q, r: ("AB" if k == "fifty" else "A", None), read_first=True)
    assert log.lifeline_rungs == {"fifty": 0}
    assert log.walked_at == 1 and log.invalid == 1 and log.questions[-1].invalid == "use fifty"
    assert log.winnings == 100


def test_fifty_keeps_the_truth():
    q = QUESTIONS[0]
    for s in range(50):
        o = fifty_outcome(q, random.Random(s))
        assert q.answer in o and len(o) == 2


def test_game_log_round_trips_through_json():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    log = play(always_answer.contestant, always_answer.NAME, 3, qs, BRIEF, simulated_fire(BRIEF, random.Random(1), USD),
               read_first=True)
    assert GameLog.from_json(log.to_json()) == log
    assert log.spend_usd == Decimal("0.01") * len(log.questions)


def test_always_answer_expected_is_proto_A_on_the_prototype():
    from explainers.millionaire.oracle.prototype import GAME
    assert round(float(always_answer.expected(GAME)), 1) == 211.4


def test_always_answer_realised_mean_matches_its_expectation():
    "Simulated instruments: the realised mean utility is within 4 standard errors of the backward induction."
    rng = random.Random(2026)
    fire = simulated_fire(BRIEF, rng, USD)
    logs = [play(always_answer.contestant, always_answer.NAME, i, draw_game(PLAY, BRIEF.tiers, rng), BRIEF, fire, True)
            for i in range(4000)]
    u = [float(log.utility(LAM)) for log in logs]
    se = statistics.stdev(u) / len(u) ** 0.5
    assert abs(statistics.mean(u) - float(always_answer.expected(BRIEF))) < 4 * se
    assert all(log.lifeline_rungs == {} and log.walked_at is None for log in logs)
    assert [always_answer.realised(log) for log in logs[:5]] == [log.winnings for log in logs[:5]]
