"""Transports, instruments, and the record of every call (rule 5), shared by every showcase.

A transport sends (system, user) to a model and returns its text and token counts. The models are the owner's to
name, in each showcase's owner file; keys come from the environment (rule 8).

Every call is priced at the instrument's DECLARED price per call, whatever the tokens were and whether or not a
cache served it; the tokens are logged beside it so the declaration can be audited.

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
    output_tokens: int


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
    usd: Decimal        # the declared price of the call
    latency_s: float
    reply: str

    def to_json(self) -> dict:
        return asdict(self) | {"usd": str(self.usd)}

    @staticmethod
    def from_json(d: dict) -> "Call":
        return Call(**(d | {"usd": Decimal(d["usd"])}))


@dataclass(frozen=True)
class Instrument:
    name: str
    model: str
    usd_per_call: Decimal
    transport: Transport


def call(instrument: Instrument, question_id: str, tier: int, system: str, user: str,
         clock: Callable[[], float] = time.monotonic, name: str | None = None) -> tuple[str, Call]:
    t0 = clock()
    reply = instrument.transport(system, user)
    return reply.text, Call(instrument=name or instrument.name, model=instrument.model, question_id=question_id,
                            tier=tier, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
                            usd=instrument.usd_per_call, latency_s=clock() - t0, reply=reply.text)


class MissingKey(RuntimeError):
    pass


def require_env(name: str) -> str:
    if not (value := os.environ.get(name)):
        raise MissingKey(f"{name} is not set; keys come from the environment (CLAUDE.md rule 8)")
    return value


def anthropic_transport(model: str, key_env: str = "LLM_API_KEY", max_tokens: int = 16000) -> Transport:
    key = require_env(key_env)
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("the Anthropic transport needs the SDK: `uv sync --extra llm`") from e
    client = anthropic.Anthropic(api_key=key)

    def send(system: str, user: str) -> Reply:
        r = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": user}])
        text = "" if r.stop_reason == "refusal" else "".join(b.text for b in r.content if b.type == "text")
        return Reply(text, r.usage.input_tokens, r.usage.output_tokens)

    return send


def from_owner(owner, name: str, transport: Callable[[str], Transport] = anthropic_transport) -> Instrument:
    from arena.config import instrument
    spec = instrument(owner, name)
    return Instrument(name=name, model=spec.model, usd_per_call=spec.usd_per_call, transport=transport(spec.model))
