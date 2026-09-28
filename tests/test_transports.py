from decimal import Decimal
from types import SimpleNamespace

import pytest

from arena.config import instrument
from arena.transports import (TRANSPORTS, Call, Instrument, MissingKey, Reply, anthropic_transport, call, from_owner,
                              openai_reply, openai_transport)


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


def test_openai_transport_fails_loud_without_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingKey, match="OPENAI_API_KEY"):
        openai_transport("any-model")


def response(text="Paris", parts=("output_text",), incomplete=None):
    ns = SimpleNamespace
    return ns(output_text=text, incomplete_details=ns(reason=incomplete) if incomplete else None,
              output=[ns(type="reasoning"), ns(type="message", content=[ns(type=t) for t in parts])],
              usage=ns(input_tokens=30, output_tokens=4, output_tokens_details=ns(reasoning_tokens=3)),
              model="gpt-5.5-2026-04-23", reasoning=ns(effort="low"))


@pytest.mark.parametrize("r,text,truncated", [(response(), "Paris", False),
                                              (response(parts=("refusal",)), "", False),
                                              (response(incomplete="content_filter"), "", False),
                                              (response(incomplete="max_output_tokens"), "Paris", True)])
def test_openai_reply_is_empty_on_refusal_only_and_records_model_effort_and_truncation(r, text, truncated):
    assert openai_reply(r) == Reply(text, 30, 4, model="gpt-5.5-2026-04-23", reasoning_tokens=3, truncated=truncated,
                                    effort="low")


def test_a_truncated_reply_stops_an_instrument_ruled_never_to_truncate_and_carries_its_paid_call():
    from arena.transports import Truncated, call
    cut = lambda s, u: Reply("Par", 10, 16000, model="m", truncated=True)
    free = Instrument("primary", "m", None, cut, list_price=(Decimal(5), Decimal(30)))
    text, c = call(free, "q1", 0, "", "Q")
    assert c.truncated and c.usd == Decimal("0.48005")          # measured: 10 × $5 + 16,000 × $30 per million
    with pytest.raises(Truncated) as e:
        call(Instrument("primary", "m", None, cut, list_price=(Decimal(5), Decimal(30)), stop_on_truncation=True),
             "q1", 0, "", "Q")
    assert e.value.call.usd == Decimal("0.48005") and e.value.call.served_model == "m"


def test_from_owner_picks_the_provider_and_its_key(monkeypatch):
    made = []
    monkeypatch.setitem(TRANSPORTS, "openai", lambda model, key_env="OPENAI_API_KEY": made.append((model, key_env))
                        or (lambda s, u: Reply("x", 1, 1)))
    owner = {"instruments": {"primary": {"model": "gpt-x", "usd_per_call": "0.01", "provider": "openai",
                                         "key_env": "OPENAI_KEY_TWO"}}}
    inst = from_owner(owner, "primary")
    assert made == [("gpt-x", "OPENAI_KEY_TWO")] and inst.usd_per_call == Decimal("0.01")
    assert instrument({"instruments": {"llm": {"model": "m", "usd_per_call": "0"}}}, "llm").provider == "anthropic"


def test_unknown_provider_fails_loud():
    with pytest.raises(ValueError, match="provider = 'acme'"):
        from_owner({"instruments": {"x": {"model": "m", "usd_per_call": "0", "provider": "acme"}}}, "x")


def test_a_gemini_reply_counts_thinking_as_output_and_a_safety_stop_is_empty():
    from arena.transports import gemini_reply
    ok = {"candidates": [{"content": {"parts": [{"text": "A", "thought": False}]}, "finishReason": "STOP"}],
          "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 1, "thoughtsTokenCount": 5}}
    r = gemini_reply(ok)
    assert (r.text, r.input_tokens, r.output_tokens) == ("A", 10, 6)
    assert gemini_reply({"candidates": [{"finishReason": "SAFETY"}], "usageMetadata": {}}).text == ""
    assert gemini_reply({"promptFeedback": {"blockReason": "OTHER"}}).text == ""


def test_the_gemini_transport_fails_loud_without_a_key(monkeypatch):
    import pytest
    from arena.transports import MissingKey, gemini_transport
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingKey):
        gemini_transport("gemini-2.5-flash")


def test_the_sdk_clients_never_retry_on_their_own(monkeypatch):
    "A retry after the provider has billed a reply would pay twice and log once."
    import anthropic, openai
    made = {}
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: made.setdefault("anthropic", kw))
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: made.setdefault("openai", kw))
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    anthropic_transport("m"), openai_transport("m")
    assert made["anthropic"]["max_retries"] == 0 and made["openai"]["max_retries"] == 0
