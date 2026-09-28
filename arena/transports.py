"""Transports, instruments, and the record of every call (rule 5), shared by every showcase.

A transport sends (system, user) to a model and returns its text and token counts: Anthropic's (key `LLM_API_KEY`)
and OpenAI's (key `OPENAI_API_KEY`), each through its official SDK (`uv sync --extra llm`). The models are the owner's
to name, in each board's owner file, with `provider` and optionally `key_env` beside them; keys come from the
environment (rule 8).

Every call is priced at the instrument's DECLARED price per call, whatever the tokens were and whether or not a
cache served it; the tokens are logged beside it so the declaration can be audited. An empty system prompt
is sent as none.

Refusals are recorded as an empty reply (hence unparseable), not retried on another model: a fallback model would
be a different instrument from the one calibrated.
"""
import os
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Callable


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int
    output_tokens: int                  # billed output, reasoning included
    model: str = ""                     # the model the provider says served the call
    reasoning_tokens: int = 0           # of output_tokens, where the provider reports them apart
    truncated: bool = False             # stopped by max_tokens
    effort: str = ""                    # the reasoning effort the provider reports, where it does


Transport = Callable[[str, str], Reply]  # (system, user) -> Reply


@dataclass(frozen=True)
class Call:
    "One instrument call, as rule 5 requires it logged."
    instrument: str
    model: str
    question_id: str
    tier: int
    input_tokens: int
    output_tokens: int
    usd: Decimal        # the declared price of the call, or its list price from the tokens (`measured`)
    latency_s: float
    reply: str
    served_model: str = ""
    reasoning_tokens: int = 0
    effort: str = ""
    truncated: bool = False

    def to_json(self) -> dict:
        return asdict(self) | {"usd": str(self.usd)}

    @staticmethod
    def from_json(d: dict) -> "Call":
        return Call(**(d | {"usd": Decimal(d["usd"])}))


@dataclass(frozen=True)
class Instrument:
    name: str
    model: str
    usd_per_call: Decimal | None        # None: priced at list price from the tokens (`measured`)
    transport: Transport
    list_price: tuple[Decimal, Decimal] | None = None   # $ per million tokens, (input, output)
    stop_on_truncation: bool = False
    effort: str | None = None           # the reasoning effort asked for, for the board's wording
    max_output: int | None = None       # the output cap sent to the provider, reasoning included; bounds a call's cost

    def list_usd(self, input_tokens: int, output_tokens: int) -> Decimal | None:
        if self.list_price is None:
            return None
        return (input_tokens * self.list_price[0] + output_tokens * self.list_price[1]) / Decimal(10 ** 6)


class Truncated(RuntimeError):
    "A reply stopped by max_tokens, from an instrument ruled never to truncate. `call` is logged and paid."
    def __init__(self, call: "Call"):
        super().__init__(f"{call.instrument} ({call.model}) was truncated at {call.output_tokens} output tokens on "
                         f"question {call.question_id}; the run stops (max_tokens is ruled never to truncate)")
        self.call = call


def call(instrument: Instrument, question_id: str, tier: int, system: str, user: str,
         clock: Callable[[], float] = time.monotonic, name: str | None = None) -> tuple[str, Call]:
    t0 = clock()
    reply = instrument.transport(system, user)
    usd = instrument.usd_per_call if instrument.usd_per_call is not None else \
        instrument.list_usd(reply.input_tokens, reply.output_tokens)
    c = Call(instrument=name or instrument.name, model=instrument.model, question_id=question_id, tier=tier,
             input_tokens=reply.input_tokens, output_tokens=reply.output_tokens, usd=usd, latency_s=clock() - t0,
             reply=reply.text, served_model=reply.model, reasoning_tokens=reply.reasoning_tokens, effort=reply.effort,
             truncated=reply.truncated)
    if reply.truncated and instrument.stop_on_truncation:
        raise Truncated(c)
    return reply.text, c


class MissingKey(RuntimeError):
    pass


def require_env(name: str) -> str:
    if not (value := os.environ.get(name)):
        raise MissingKey(f"{name} is not set; keys come from the environment (CLAUDE.md rule 8)")
    return value


def anthropic_transport(model: str, key_env: str = "LLM_API_KEY", max_tokens: int = 16000,
                        thinking: str | None = None, effort: str | None = None) -> Transport:
    """`thinking`: the request's thinking type ("disabled", "adaptive"), or None to send none and take the model's
    default. A model that thinks by default spends a short max_tokens on thinking and can return no text."""
    key = require_env(key_env)
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("the Anthropic transport needs the SDK: `uv sync --extra llm`") from e
    client = anthropic.Anthropic(api_key=key, max_retries=0)    # a silent retry could pay twice and log once

    def send(system: str, user: str) -> Reply:
        r = client.messages.create(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": user}],
                                   **({"system": system} if system else {}),
                                   **({"thinking": {"type": thinking}} if thinking else {}),
                                   **({"output_config": {"effort": effort}} if effort else {}))
        text = "" if r.stop_reason == "refusal" else "".join(b.text for b in r.content if b.type == "text")
        return Reply(text, r.usage.input_tokens, r.usage.output_tokens, model=r.model,
                     truncated=r.stop_reason == "max_tokens", effort=effort or "")

    return send


def openai_reply(r) -> Reply:
    "A Responses API response as a Reply; a refusal or a content-filtered stop is an empty reply, as for Anthropic."
    refused = (getattr(r.incomplete_details, "reason", None) == "content_filter"
               or any(part.type == "refusal" for item in r.output if item.type == "message" for part in item.content))
    details = getattr(r.usage, "output_tokens_details", None)
    return Reply("" if refused else r.output_text, r.usage.input_tokens, r.usage.output_tokens, model=r.model or "",
                 reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0,
                 truncated=getattr(r.incomplete_details, "reason", None) == "max_output_tokens",
                 effort=getattr(getattr(r, "reasoning", None), "effort", None) or "")


def openai_transport(model: str, key_env: str = "OPENAI_API_KEY", max_tokens: int = 16000,
                     effort: str | None = None) -> Transport:
    key = require_env(key_env)
    try:
        import openai
    except ImportError as e:
        raise ImportError("the OpenAI transport needs the SDK: `uv sync --extra llm`") from e
    client = openai.OpenAI(api_key=key, max_retries=0)          # a silent retry could pay twice and log once

    def send(system: str, user: str) -> Reply:
        return openai_reply(client.responses.create(model=model, input=user, max_output_tokens=max_tokens,
                                                    **({"instructions": system} if system else {}),
                                                    **({"reasoning": {"effort": effort}} if effort else {})))

    return send


def gemini_reply(r: dict) -> Reply:
    """A generateContent response as a Reply. A blocked prompt or a safety stop is an empty reply, as for Anthropic.
    Output tokens include the thinking tokens, which are billed as output."""
    usage = r.get("usageMetadata", {})
    cands = r.get("candidates") or []
    blocked = "blockReason" in r.get("promptFeedback", {}) or not cands or cands[0].get("finishReason") in (
        "SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION")
    text = "" if blocked else "".join(part.get("text", "") for part in cands[0].get("content", {}).get("parts", [])
                                      if not part.get("thought"))
    return Reply(text, usage.get("promptTokenCount", 0),
                 usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0),
                 model=r.get("modelVersion", ""), reasoning_tokens=usage.get("thoughtsTokenCount", 0),
                 truncated=bool(cands) and cands[0].get("finishReason") == "MAX_TOKENS")


def gemini_transport(model: str, key_env: str = "GEMINI_API_KEY", max_tokens: int = 16000,
                     thinking: str | None = None) -> Transport:
    """Google's Gemini API over HTTPS with the standard library. `thinking = "disabled"` sets a thinking budget of
    0; "minimal", "low" or "high" set the thinking level, for models that take a level instead (the Gemini 3 family)."""
    key = require_env(key_env)
    import json
    import urllib.error
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def send(system: str, user: str) -> Reply:
        config = {"maxOutputTokens": max_tokens} | (
            {"thinkingConfig": {"thinkingBudget": 0}} if thinking == "disabled" else
            {"thinkingConfig": {"thinkingLevel": thinking}} if thinking else {})
        body = {"contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": config} | (
            {"systemInstruction": {"parts": [{"text": system}]}} if system else {})
        req = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return gemini_reply(json.load(resp))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"gemini {model}: HTTP {e.code}: {e.read().decode(errors='replace')[:500]}") from e

    return send


TRANSPORTS: dict[str, Callable[..., Transport]] = {"anthropic": anthropic_transport, "openai": openai_transport,
                                                    "gemini": gemini_transport}


def from_owner(owner, name: str, transport: Callable[[str], Transport] | None = None) -> Instrument:
    "The named instrument from an owner file, on its provider's transport unless one is given (tests pass fakes)."
    from arena.config import instrument
    spec = instrument(owner, name)
    if transport is None:
        if spec.provider not in TRANSPORTS:
            raise ValueError(f"instruments.{name}.provider = {spec.provider!r}; known: {', '.join(TRANSPORTS)}")
        factory = TRANSPORTS[spec.provider]
        kwargs = {k: v for k, v in (("key_env", spec.key_env), ("max_tokens", spec.max_tokens),
                                    ("thinking", spec.thinking), ("effort", spec.effort)) if v is not None}
        transport = lambda m: factory(m, **kwargs)
    return Instrument(name=name, model=spec.model, usd_per_call=spec.usd_per_call, transport=transport(spec.model),
                      list_price=spec.list_price, stop_on_truncation=spec.stop_on_truncation, effort=spec.effort,
                      max_output=spec.max_tokens)
