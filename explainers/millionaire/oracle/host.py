"""The host: runs one game by the rules, fires the instruments a contestant asks for, and logs everything.

A contestant is a function from what it can see (`View`) to a `Decision`: an act, plus any model calls it made in
deciding (the LLM-plays-directly baseline decides by calling a model; the others decide without one). The host
enforces the rules, so a contestant cannot cheat and cannot crash a game:

- with `read_first` (the owner's ruling) the host fires the LLM read at the start of every question and charges it;
- a lifeline may be used only if held; using it spends it for the rest of the game;
- `answer X` ends the question; a wrong answer ends the game at the last safe haven;
- `walk` ends the game at the last prize;
- anything else (an unparseable reply, a lifeline not held) is recorded as invalid and ends the game as a walk.
"""
import random
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Callable, Mapping, Sequence

from arena.transports import Call, Instrument
from explainers.millionaire.calibration.reading import read
from explainers.millionaire.questions import Question
from explainers.millionaire.oracle.game import ALL_LIFELINES, LIFELINES, OPTIONS, Game

ANSWERS = tuple(f"answer {x}" for x in OPTIONS)
INVALID = "invalid"


@dataclass(frozen=True)
class View:
    rung: int
    held: frozenset                  # lifelines held on arrival at this question
    question: Question
    history: tuple = ()              # (instrument, outcome) this question, in order

    @property
    def observed(self) -> frozenset:
        return frozenset(self.history)

    @property
    def remaining(self) -> frozenset:
        return self.held - {k for k, _ in self.history}


@dataclass(frozen=True)
class Decision:
    act: str
    calls: tuple = ()                # model calls made in deciding, logged under rule 5
    raw: str | None = None           # the reply the act was parsed from, when there was one


Contestant = Callable[[View], Decision]
Fire = Callable[[str, Question, int], tuple[str, Call | None]]  # (instrument, question, rung) -> (outcome, call)


@dataclass(frozen=True)
class QuestionLog:
    rung: int
    question_id: str
    tier: int
    events: tuple                    # (instrument, outcome), in order
    final: str                       # the act that ended the question
    right: bool | None               # None when the question ended without an answer
    invalid: str | None = None       # the raw reply, when the act was invalid


@dataclass(frozen=True)
class GameLog:
    contestant: str
    game: int
    winnings: Fraction
    questions: tuple
    calls: tuple = field(default=())

    @property
    def spend_usd(self) -> Decimal:
        return sum((c.usd for c in self.calls), Decimal(0))

    @property
    def lifeline_rungs(self) -> dict[str, int]:
        return {k: q.rung for q in self.questions for k, _ in q.events if k in LIFELINES}

    @property
    def walked_at(self) -> int | None:
        last = self.questions[-1]
        return last.rung if last.right is None else None

    @property
    def wrong_at(self) -> int | None:
        last = self.questions[-1]
        return last.rung if last.right is False else None

    @property
    def invalid(self) -> int:
        return sum(q.invalid is not None for q in self.questions)

    def utility(self, lambda_usd: Fraction) -> Fraction:
        return self.winnings - lambda_usd * Fraction(self.spend_usd)

    def to_json(self) -> dict:
        return {"contestant": self.contestant, "game": self.game, "winnings": str(self.winnings),
                "spend_usd": str(self.spend_usd),
                "questions": [{"rung": q.rung, "question_id": q.question_id, "tier": q.tier,
                               "events": [list(e) for e in q.events], "final": q.final, "right": q.right,
                               "invalid": q.invalid} for q in self.questions],
                "calls": [c.to_json() for c in self.calls]}

    @staticmethod
    def from_json(d: dict) -> "GameLog":
        return GameLog(contestant=d["contestant"], game=d["game"], winnings=Fraction(d["winnings"]),
                       questions=tuple(QuestionLog(rung=q["rung"], question_id=q["question_id"], tier=q["tier"],
                                                   events=tuple(tuple(e) for e in q["events"]), final=q["final"],
                                                   right=q["right"], invalid=q["invalid"]) for q in d["questions"]),
                       calls=tuple(Call.from_json(c) for c in d["calls"]))


def fifty_outcome(q: Question, rng: random.Random) -> str:
    "The exact 50:50: keep the right option and one wrong one, uniformly."
    keep = rng.choice([x for x in OPTIONS if x != q.answer])
    return "".join(sorted(q.answer + keep))


def instruments_fire(instruments: Mapping[str, Instrument], rng: random.Random) -> Fire:
    "Real instruments: a model call for llm/phone/audience, the exact rule for the 50:50."
    def fire(k: str, q: Question, r: int):
        return (fifty_outcome(q, rng), None) if k == "fifty" else read(instruments[k], q)
    return fire


def simulated_fire(game: Game, rng: random.Random, usd: Mapping[str, Decimal]) -> Fire:
    """Instruments drawn from the game's own kernels -- for testing the host and checking a World against itself,
    never for a scoreboard result."""
    def fire(k: str, q: Question, r: int):
        kernel = game.kernel(k, r)[q.answer]
        outcomes = sorted(kernel)
        o = rng.choices(outcomes, weights=[float(kernel[x]) for x in outcomes])[0]
        c = None if k == "fifty" else Call(k, "simulated", q.id, q.tier, 0, 0, usd[k], 0.0, o)
        return o, c
    return fire


def play(contestant: Contestant, name: str, index: int, questions: Sequence[Question], game: Game,
         fire: Fire, read_first: bool) -> GameLog:
    held, calls, logs = ALL_LIFELINES, [], []

    def end(winnings: Fraction) -> GameLog:
        return GameLog(name, index, winnings, tuple(logs), tuple(calls))

    for r, q in enumerate(questions):
        arrival, history = held, []

        def observe(k):
            o, c = fire(k, q, r)
            history.append((k, o))
            calls.extend([c] if c else [])

        if read_first:
            observe("llm")
        while True:
            d = contestant(View(r, arrival, q, tuple(history)))
            calls.extend(d.calls)
            if d.act in held:
                held = held - {d.act}
                observe(d.act)
                continue
            if d.act in ANSWERS:
                right = d.act[-1] == q.answer
                logs.append(QuestionLog(r, q.id, q.tier, tuple(history), d.act, right))
                if not right:
                    return end(game.safe(r))
                break
            invalid = None if d.act == "walk" else (d.raw if d.raw is not None else d.act)
            logs.append(QuestionLog(r, q.id, q.tier, tuple(history), d.act, None, invalid))
            return end(game.walk(r))
    return end(game.ladder[-1])
