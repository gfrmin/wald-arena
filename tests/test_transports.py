from decimal import Decimal

import pytest

from arena.transports import Call, Instrument, MissingKey, Reply, anthropic_transport, call


def test_call_logs_at_the_declared_price():
    inst = Instrument("phone", "friend-model", Decimal("0.004"), lambda s, u: Reply("D", 120, 1))
    text, c = call(inst, "q7", 2, "system", "user")
    assert text == "D"
    assert (c.instrument, c.model, c.question_id, c.tier, c.input_tokens, c.output_tokens, c.usd) == \
           ("phone", "friend-model", "q7", 2, 120, 1, Decimal("0.004"))
    assert Call.from_json(c.to_json()) == c


def test_transport_fails_loud_without_a_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(MissingKey, match="LLM_API_KEY"):
        anthropic_transport("any-model")
