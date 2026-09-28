"""AA-Omniscience-Public, pinned by hash, and a seeded draw and split stratified by domain."""
import csv
import hashlib
import random
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE / "data" / "AA-Omniscience_dataset_public.csv"
CSV_SHA256 = "1e04603dafa3bd0d16d8151f07a5eb74c43d90c3a85d2fca120da2359174d02f"


class QuestionSetError(ValueError):
    pass


@dataclass(frozen=True)
class Question:
    id: str
    domain: str
    topic: str
    subtopic: str
    text: str
    answer: str


def load(path: Path = CSV, sha256: str = CSV_SHA256) -> tuple[Question, ...]:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha256:
        raise QuestionSetError(f"{path}: sha256 differs from the pinned revision")
    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    qs = tuple(Question(r["question_id"], r["domain"], r["topic"], r["subtopic"], r["question"], r["answer"])
               for r in rows)
    if len({q.id for q in qs}) != len(qs):
        raise QuestionSetError(f"{path}: repeated question_id")
    return qs


def domains(qs) -> tuple[str, ...]:
    return tuple(sorted({q.domain for q in qs}))


def draw(qs, per_domain: int, seed: int) -> tuple[Question, ...]:
    "per_domain questions from each domain, drawn with the seed, in a fixed order."
    rng = random.Random(f"draw:{seed}")
    return tuple(q for d in domains(qs) for q in rng.sample([q for q in qs if q.domain == d], per_domain))


def split(qs, calibration_per_domain: int, seed: int) -> tuple[tuple[Question, ...], tuple[Question, ...]]:
    "(calibration, test): the first calibration_per_domain of each domain's seeded shuffle, and the rest."
    rng = random.Random(f"split:{seed}")
    cal, test = [], []
    for d in domains(qs):
        part = [q for q in qs if q.domain == d]
        rng.shuffle(part)
        cal += part[:calibration_per_domain]
        test += part[calibration_per_domain:]
    return tuple(cal), tuple(test)
