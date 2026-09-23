"""AA's grading prompt, run once per distinct (question, answer) and shared by every contestant.

The grades are memoised in a JSONL file, one row per grading call with the call logged beside it (rule 5); a
second request for an answer already graded is served from the file and costs nothing.
"""
import json
import re
from pathlib import Path

from arena.spend import read_rows
from arena.transports import Call, Instrument, call
from showcases.omniscience.questions import Question

TEMPLATE = (Path(__file__).resolve().parent / "prompts" / "grader.txt").read_text()
GRADES = {"A": "CORRECT", "B": "INCORRECT", "C": "PARTIAL_ANSWER", "D": "NOT_ATTEMPTED"}
UNGRADED = "UNGRADED"


def prompt(q: Question, answer: str) -> str:
    return TEMPLATE.replace("{question}", q.text).replace("{target}", q.answer).replace("{predicted_answer}", answer)


def parse_grade(text: str) -> str:
    m = re.fullmatch(r'\s*"?([ABCD])"?\s*', text)
    return GRADES[m.group(1)] if m else UNGRADED


class Grader:
    def __init__(self, instrument: Instrument, memo: Path, tier_of=lambda q: 0, before_each_call=lambda i: None):
        self.instrument, self.memo, self.tier_of, self.before = instrument, memo, tier_of, before_each_call
        self.graded = {(r["question_id"], r["answer"]): r["grade"] for r in read_rows(memo)}

    def __call__(self, q: Question, answer: str) -> str:
        key = (q.id, answer)
        if key not in self.graded:
            self.before(self.instrument)
            text, c = call(self.instrument, q.id, self.tier_of(q), "", prompt(q, answer), name="grader")
            self.graded[key] = parse_grade(text)
            with open(self.memo, "a") as f:
                f.write(json.dumps({"question_id": q.id, "answer": answer, "grade": self.graded[key],
                                    "call": c.to_json()}) + "\n")
        return self.graded[key]


def calls(memo: Path) -> list[Call]:
    return [Call.from_json(r["call"]) for r in read_rows(memo)]
