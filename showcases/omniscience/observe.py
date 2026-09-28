"""What the instruments are asked, and what is read off their replies: the read, its confidence, the agreement
samples and the second opinion. Every call goes through `arena.transports.call` and is logged (rule 5).

A `tier` in the spend log is the question's domain index; this board has no difficulty tiers.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from arena.transports import Call, Instrument, Truncated, call
from showcases.omniscience.questions import Question

PROMPTS = Path(__file__).resolve().parent / "prompts"
ANSWER_PROMPT = (PROMPTS / "answer.txt").read_text()
EQUIVALENCE_PROMPT = (PROMPTS / "equivalence.txt").read_text()
DECLINE = "D"
CONFIDENCE_SYSTEM = ("You will be shown a question and the answer you gave to it. Reply with only a whole number "
                     "from 0 to 100: how confident you are that your answer is correct.")
UNREAD = "unread"


def answer_system(q: Question) -> str:
    return ANSWER_PROMPT.replace("{domain}", q.domain).replace("{subtopic}", q.subtopic)


def normalise(text: str) -> str:
    t = re.sub(r"[^\w\s]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^(the|a|an) ", "", t)


def matches(a: str, b: str) -> bool:
    "Proposed in QUESTIONS.md 2.7: normalised exact match."
    return normalise(a) == normalise(b)


def equivalence_prompt(q: Question, answers: tuple[str, ...]) -> str:
    "QUESTIONS.md 2.7 as ruled: the read, the samples and the second opinion, numbered in that order."
    listed = "\n\n".join(f"Answer {i}: {a.strip() or '(no answer)'}" for i, a in enumerate(answers, 1))
    return EQUIVALENCE_PROMPT.replace("{question}", q.text).replace("{answers}", listed)


def parse_classes(text: str, n: int) -> tuple[str, ...] | None:
    """One class per answer, "D" or a positive whole number, from lines "<i>: <class>" for i = 1..n in order;
    None if the reply is not exactly that."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) != n:
        return None
    out = []
    for i, line in enumerate(lines, 1):
        m = re.fullmatch(rf"(?:Answer\s*)?{i}\s*:\s*(D|\d+)", line, re.IGNORECASE)
        if not m:
            return None
        out.append(m.group(1).upper())
    return tuple(out)


def parse_confidence(text: str) -> int | None:
    "The reply's first non-empty line, if it is a lone whole number 0-100; anything after it is ignored."
    first = next((line for line in text.splitlines() if line.strip()), "")
    m = re.fullmatch(r"\s*(\d{1,3})\s*%?\s*", first)
    return int(m.group(1)) if m and int(m.group(1)) <= 100 else None


def bucket_of(confidence: int | None, cuts: tuple[int, ...], unread: str = UNREAD) -> str:
    """cuts are the lower bounds of the buckets above the first, e.g. (50, 80, 95) -> b0 [0,50) b1 [50,80) ...;
    an unreadable confidence goes to `unread`, its own bucket or one of the others (QUESTIONS.md 2.15)."""
    if confidence is None:
        return unread
    return f"b{sum(confidence >= c for c in cuts)}"


def bucket_names(cuts: tuple[int, ...], unread: str = UNREAD) -> tuple[str, ...]:
    named = tuple(f"b{i}" for i in range(len(cuts) + 1))
    return named if unread in named else named + (unread,)


def domain_index(q: Question, domains: tuple[str, ...]) -> int:
    return domains.index(q.domain)


def ask(instrument: Instrument, q: Question, tier: int, name: str | None = None) -> tuple[str, Call]:
    return call(instrument, q.id, tier, answer_system(q), q.text, name=name)


def confidence(instrument: Instrument, q: Question, tier: int, answer: str) -> tuple[int | None, Call]:
    text, c = call(instrument, q.id, tier, CONFIDENCE_SYSTEM, f"Question: {q.text}\nYour answer: {answer}",
                   name=f"{instrument.name}.confidence")
    return parse_confidence(text), c


@dataclass(frozen=True)
class Seen:
    "Everything observed of one question, before grading. k and s are what the World's acts reveal."
    read: str
    confidence: int | None
    samples: tuple[str, ...]
    second: str
    calls: tuple[Call, ...]
    classes: tuple[str, ...] | None = None   # the equivalence call's classes, read first; None: none made, or unparsed

    @property
    def k(self) -> int:
        "Samples in the read's class (2.7 as ruled); by normalised exact match where there are no classes."
        if self.classes:
            return sum(c == self.classes[0] for c in self.classes[1:1 + len(self.samples)])
        return sum(matches(x, self.read) for x in self.samples)

    @property
    def s(self) -> str:
        if self.classes:
            return "same" if self.classes[-1] == self.classes[0] else "different"
        return "same" if matches(self.second, self.read) else "different"


def equivalence(instrument: Instrument, q: Question, tier: int, answers: tuple[str, ...]) -> tuple[tuple | None, Call]:
    text, c = call(instrument, q.id, tier, "", equivalence_prompt(q, answers))
    return parse_classes(text, len(answers)), c


def observe(primary: Instrument, second: Instrument, q: Question, tier: int, n_samples: int,
            before_each_call=lambda instrument: None, equivalent: Instrument | None = None,
            after_each_call=lambda call: None) -> Seen:
    """Every observation of one question, recorded once whatever any contestant later buys. With `equivalent`, one
    further call sorts the answers into classes, which k and s then read (2.7 as ruled)."""
    calls = []

    def paid(instrument, f, *args):
        before_each_call(instrument)
        try:
            out, c = f(instrument, q, tier, *args)
        except Truncated as e:
            after_each_call(e.call)
            raise
        calls.append(c)
        after_each_call(c)
        return out

    read = paid(primary, ask)
    conf = paid(primary, confidence, read)
    samples = tuple(paid(primary, lambda i, q, t: ask(i, q, t, name=f"{i.name}.sample")) for _ in range(n_samples))
    second_answer = paid(second, ask)
    classes = paid(equivalent, equivalence, (read, *samples, second_answer)) if equivalent else None
    return Seen(read, conf, samples, second_answer, tuple(calls), classes)
