"""The Millionaire read: a multiple-choice question put to an instrument, reported as a letter A-D or UNREAD."""
import re

from arena.transports import Call, Instrument, call
from explainers.millionaire.oracle.game import UNREAD
from explainers.millionaire.questions import Question

READ_SYSTEM = ("You are answering a multiple-choice quiz question. Exactly one option is right. "
               "Reply with exactly one letter, A, B, C or D, and nothing else.")


def question_text(q: Question) -> str:
    return q.text + "\n\n" + "\n".join(f"{k}. {v}" for k, v in q.options.items())


LETTER = re.compile(r"\s*([ABCD])\s*")


def parse_letter(text: str) -> str:
    "The report: a lone letter A-D, or UNREAD for anything else."
    m = LETTER.fullmatch(text)
    return m.group(1) if m else UNREAD


def read(instrument: Instrument, q: Question) -> tuple[str, Call]:
    "Ask the instrument the question; the report is a letter or UNREAD."
    text, c = call(instrument, q.id, q.tier, READ_SYSTEM, question_text(q))
    return parse_letter(text), c
