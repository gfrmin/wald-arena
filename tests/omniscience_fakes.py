"""A scripted board for the omniscience tests: synthetic questions and one fake model for every role."""
import re
import zlib

from arena.transports import Reply
from showcases.omniscience.observe import CONFIDENCE_SYSTEM
from showcases.omniscience.questions import Question

DOMAINS = tuple(f"Domain {i}" for i in range(6))


def questions(per_domain: int = 6) -> tuple[Question, ...]:
    return tuple(Question(f"{d[-1]}{i:02d}", d, "topic", "subtopic", f"What is item {d[-1]}{i:02d}?", f"answer {d[-1]}{i:02d}")
                 for d in DOMAINS for i in range(per_domain))


class Scripted:
    """Answers right on two thirds of the questions (by a hash of the id), states 90 when right and 30 when not,
    grades by exact match. Counts its calls."""
    def __init__(self, served: str = ""):
        self.calls, self.served = 0, served

    def __call__(self, model):
        return self.send

    def send(self, system, user):
        self.calls += 1
        if system == CONFIDENCE_SYSTEM:
            item = re.search(r"item (\w+)\?", user).group(1)
            return Reply("90" if f"answer {item}" in user else "30", 80, 1)
        if system.startswith("You are answering"):
            item = re.search(r"item (\w+)\?", user).group(1)
            right = zlib.crc32(item.encode()) % 3 != 0
            return Reply(f"answer {item}" if right else "no idea, maybe Paris", 60, 4)
        if user.startswith("You will be shown a question and several numbered answers"):
            answers = re.findall(r"^Answer \d+: (.*)$", user, re.M)
            names = {}
            classes = ["D" if a.startswith("no idea") else str(names.setdefault(a, len(names) + 1)) for a in answers]
            return Reply("\n".join(f"{i}: {c}" for i, c in enumerate(classes, 1)), 400, 12, model=self.served)
        gold = re.search(r"Gold target: (.*)", user.split("Here is a new example")[-1]).group(1).strip()
        pred = re.search(r"Predicted answer: (.*)", user.split("Here is a new example")[-1]).group(1).strip()
        return Reply("A" if gold == pred else "B", 1500, 1)
