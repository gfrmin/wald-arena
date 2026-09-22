import random
from decimal import Decimal
from fractions import Fraction as F

import pytest

from baselines import llm_direct
from calibration.instruments import Instrument, Reply
from data.questions import draw_game
from oracle.host import INVALID, View, play
from tests.test_host_and_always_answer import BRIEF, PLAY


@pytest.mark.parametrize("text,act", [
    ("answer B", "answer B"), ("  Answer c \n", "answer C"), ("use fifty", "fifty"), ("USE Phone", "phone"),
    ("use audience", "audience"), ("walk", "walk"),
    ("answer B.", INVALID), ("I will answer B", INVALID), ("use 50:50", INVALID), ("answer E", INVALID),
    ("answer B\nwalk", INVALID), ("", INVALID), ("B", INVALID),
])
def test_parse_is_strict(text, act):
    assert llm_direct.parse(text) == act


def test_prompt_carries_rules_ladder_lifelines_and_question():
    q = PLAY[0]
    system = llm_direct.rules(BRIEF)
    assert "$1,000,000" in system and "Q5: $1,000  (safe haven)" in system and "Q10: $32,000  (safe haven)" in system
    v = View(rung=6, held=frozenset({"fifty", "phone"}), question=q, history=(("fifty", "AC"), ("phone", "?")))
    s = llm_direct.situation(BRIEF, v)
    assert "Question 7 of 15, for $4,000" in s and "keeps $2,000" in s and "leaves you with $1,000" in s
    assert "Lifelines left: none." in s
    assert "A and C remain" in s and "friend gave no clear answer" in s
    assert all(f"{k}. {t}" in s for k, t in q.options.items())


def script(replies):
    it = iter(replies)
    return Instrument("llm", "scripted", Decimal("0.01"), lambda system, user: Reply(next(it), 500, 3))


def test_loop_uses_lifelines_then_answers_and_logs_every_call():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    replies = ["use fifty", "use phone", f"answer {qs[0].answer}", "walk"]
    fire = lambda k, q, r: (("AB", None) if k == "fifty" else ("C", None))
    log = play(llm_direct.contestant(script(replies), BRIEF), llm_direct.NAME, 0, qs, BRIEF, fire, read_first=False)
    assert log.questions[0].events == (("fifty", "AB"), ("phone", "C"))
    assert log.walked_at == 1 and log.winnings == 100 and log.invalid == 0
    assert len(log.calls) == 4 and all(c.instrument == "llm_direct" for c in log.calls)
    assert log.spend_usd == Decimal("0.04")


def test_unparseable_reply_is_a_counted_walk():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    replies = [f"answer {qs[0].answer}", "Hmm, I think it is probably B"]
    log = play(llm_direct.contestant(script(replies), BRIEF), llm_direct.NAME, 0, qs, BRIEF,
               lambda k, q, r: ("A", None), read_first=False)
    assert log.winnings == 100 and log.walked_at == 1
    assert log.invalid == 1 and log.questions[-1].invalid == "Hmm, I think it is probably B"


def test_using_a_spent_lifeline_is_a_counted_walk():
    qs = draw_game(PLAY, BRIEF.tiers, random.Random(0))
    replies = ["use fifty", f"answer {qs[0].answer}", "use fifty"]
    log = play(llm_direct.contestant(script(replies), BRIEF), llm_direct.NAME, 0, qs, BRIEF,
               lambda k, q, r: ("AB", None), read_first=False)
    assert log.invalid == 1 and log.walked_at == 1 and log.questions[-1].invalid == "use fifty"
