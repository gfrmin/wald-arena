"""The owner's question set: loading, validation, and the split into calibration / held-out-score / play.

The set's shape is the owner's (QUESTIONS.md, open question 4). Until it is known, the loader reads JSONL, one
question per line:

    {"id": "q0001", "text": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
     "answer": "C", "tier": "easy"}

Validation is strict: a malformed line is an error naming the line, never a skipped question.
"""
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from explainers.millionaire.oracle.game import OPTIONS

TIERS = ("easy", "medium", "hard")  # tier 0, 1, 2: questions 1-5, 6-10, 11-15


class QuestionSetError(ValueError):
    pass


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: Mapping[str, str]  # A..D -> option text
    answer: str                 # the right option's letter
    tier: int                   # 0 easy, 1 medium, 2 hard


def parse(record: Mapping, where: str = "record") -> Question:
    def fail(why):
        raise QuestionSetError(f"{where}: {why}")

    if not isinstance(record, Mapping):
        fail("not an object")
    if missing := {"id", "text", "options", "answer", "tier"} - set(record):
        fail(f"missing {sorted(missing)}")
    options = record["options"]
    if not isinstance(options, Mapping) or tuple(sorted(options)) != OPTIONS:
        fail(f"options must have exactly the keys {OPTIONS}")
    if not all(isinstance(v, str) and v.strip() for v in options.values()):
        fail("every option must be non-empty text")
    if record["answer"] not in OPTIONS:
        fail(f"answer {record['answer']!r} is not one of {OPTIONS}")
    if record["tier"] not in TIERS:
        fail(f"tier {record['tier']!r} is not one of {TIERS}")
    if not (isinstance(record["id"], str) and record["id"]) or not (isinstance(record["text"], str) and record["text"]):
        fail("id and text must be non-empty strings")
    return Question(id=record["id"], text=record["text"], options={k: options[k] for k in OPTIONS},
                    answer=record["answer"], tier=TIERS.index(record["tier"]))


def load(path: Path) -> tuple[Question, ...]:
    with open(path) as f:
        questions = tuple(parse(json.loads(line), f"{path}:{n}") for n, line in enumerate(f, 1) if line.strip())
    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids):
        raise QuestionSetError(f"{path}: duplicate ids {sorted({i for i in ids if ids.count(i) > 1})}")
    return questions


@dataclass(frozen=True)
class Split:
    calibration: tuple[Question, ...]  # fit the reliabilities
    held_out: tuple[Question, ...]     # score the fit
    play: tuple[Question, ...]         # the games


def split(questions: Iterable[Question], seed: int, per_tier: int, held_out_per_tier: int) -> Split:
    """Per tier: order by id, shuffle with the seed, take `per_tier` for calibration, the next `held_out_per_tier`
    for the held-out score, and the rest for play. Deterministic in (question ids, seed)."""
    rng = random.Random(seed)
    cal, held, play = [], [], []
    for tier in range(len(TIERS)):
        pool = sorted((q for q in questions if q.tier == tier), key=lambda q: q.id)
        if len(pool) < per_tier + held_out_per_tier:
            raise QuestionSetError(f"tier {TIERS[tier]} has {len(pool)} questions; "
                                   f"calibration needs {per_tier} + {held_out_per_tier} before any are left to play")
        rng.shuffle(pool)
        cal += pool[:per_tier]
        held += pool[per_tier:per_tier + held_out_per_tier]
        play += pool[per_tier + held_out_per_tier:]
    return Split(tuple(cal), tuple(held), tuple(play))


def draw_game(play: Sequence[Question], tiers: Sequence[int], rng: random.Random) -> tuple[Question, ...]:
    "One game's questions: for each rung, a play question of that rung's tier, none repeated within the game."
    pools = {t: sorted((q for q in play if q.tier == t), key=lambda q: q.id) for t in set(tiers)}
    need = {t: list(tiers).count(t) for t in pools}
    if short := {TIERS[t]: len(pools[t]) for t in pools if len(pools[t]) < need[t]}:
        raise QuestionSetError(f"play pool too small for one game: {short}")
    drawn = {t: rng.sample(pools[t], need[t]) for t in sorted(pools)}
    return tuple(drawn[t].pop() for t in tiers)
