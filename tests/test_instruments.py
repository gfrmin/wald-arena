from decimal import Decimal

import pytest

from calibration.instruments import (Call, Instrument, MissingKey, Reply, anthropic_transport, parse_letter, read)
from tests.conftest import make_questions


@pytest.mark.parametrize("text,report", [("B", "B"), (" C\n", "C"), ("b", "?"), ("B.", "?"), ("The answer is B", "?"),
                                         ("", "?"), ("AB", "?")])
def test_parse_letter_is_strict(text, report):
    assert parse_letter(text) == report


def test_read_logs_the_call_at_the_declared_price():
    q = make_questions(1)[0]
    inst = Instrument("phone", "friend-model", Decimal("0.004"), lambda s, u: Reply("D", 120, 1))
    report, c = read(inst, q)
    assert report == "D"
    assert (c.instrument, c.model, c.question_id, c.tier, c.input_tokens, c.output_tokens, c.usd) == \
           ("phone", "friend-model", q.id, 0, 120, 1, Decimal("0.004"))
    assert Call.from_json(c.to_json()) == c


def test_transport_fails_loud_without_a_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(MissingKey, match="LLM_API_KEY"):
        anthropic_transport("any-model")
