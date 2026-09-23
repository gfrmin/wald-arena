import json

import pytest

from explainers.millionaire.questions import TIERS, Question


def make_questions(per_tier: int) -> list[Question]:
    "A synthetic set: per_tier questions in each tier, the right answer cycling through A..D."
    return [Question(id=f"{TIERS[t]}-{i:04d}", text=f"Question {t}.{i}?",
                     options={x: f"option {x} of {t}.{i}" for x in "ABCD"}, answer="ABCD"[i % 4], tier=t)
            for t in range(3) for i in range(per_tier)]


def as_record(q: Question) -> dict:
    return {"id": q.id, "text": q.text, "options": dict(q.options), "answer": q.answer, "tier": TIERS[q.tier]}


@pytest.fixture
def questions():
    return make_questions(320)


@pytest.fixture
def question_file(tmp_path, questions):
    p = tmp_path / "questions.jsonl"
    p.write_text("".join(json.dumps(as_record(q)) + "\n" for q in questions))
    return p
