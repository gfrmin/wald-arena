"""The four contestants on the test split, at one penalty and one second-opinion price, and what each scored.

Baselines 2-4 are labelled as baselines (rule 1): the threshold reads Dirichlet(1) means of the calibration split's
graded reads and compares, which only a baseline may do. wald's acts come from `Plate.run` on the generated pack,
behind `RecordedDoor`, which serves what was observed and never chooses.
"""
import math
import statistics
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping, Sequence

import wald

from arena.calibration import dirichlet1_mean

CONTESTANTS = ("raw model", "calibrated threshold", "better single model", "wald")
G = ("right", "zero", "wrong")


def grade_class(grade: str) -> str:
    "CORRECT scores +1, INCORRECT -p, PARTIAL_ANSWER and NOT_ATTEMPTED 0 (QUESTIONS.md 2.8); an ungraded reply is wrong."
    return {"CORRECT": "right", "PARTIAL_ANSWER": "zero", "NOT_ATTEMPTED": "zero"}.get(grade, "wrong")


def u(g: str, p: Fraction) -> Fraction:
    return {"right": Fraction(1), "zero": Fraction(0), "wrong": -p}[g]


@dataclass(frozen=True)
class Played:
    submitted: str          # primary | second | abstain
    agreement: bool
    consulted: bool         # the second opinion was bought: looked at, or fired blind
    blind: bool = False     # `answer_second` fired without `second_opinion`: priced exactly (QUESTIONS.md 2.19)
    overcharged: bool = False  # `answer_second` after `second_opinion`: the World charged c twice (2.19)


# ---------------------------------------------------------------- the baselines

def bucket_rates(cal_rows, buckets) -> dict:
    "BASELINE: per bucket, the Dirichlet(1) mean of the read's grade class on the calibration split."
    return {b: dirichlet1_mean({g: sum(r["b"] == b and r["g1"] == g for r in cal_rows) for g in G}) for b in buckets}


def raw(row, **_) -> Played:
    return Played("primary", False, False)


def threshold(row, rates, p, **_) -> Played:
    "BASELINE: answer the read iff its bucket's P(right) - p P(wrong) > 0."
    q = rates[row["b"]]
    return Played("primary" if q["right"] - p * q["wrong"] > 0 else "abstain", False, False)


def better_single(row, second_better: bool, **_) -> Played:
    "BASELINE: whichever model scored higher under p on calibration, answering raw; the second pays its price."
    return Played("second" if second_better else "primary", False, second_better)


def second_is_better(cal_rows, p: Fraction) -> bool:
    return sum(u(r["g2"], p) for r in cal_rows) > sum(u(r["g1"], p) for r in cal_rows)


BASELINES: Mapping[str, Callable] = {"raw model": raw, "calibrated threshold": threshold,
                                     "better single model": better_single}


# ---------------------------------------------------------------- wald, behind a door

class RecordedDoor(wald.Door):
    """Serves one question's recorded observations. The After-act's report is the grade of the answer the end
    submitted; on `abstain`, of the read (brief 002, revision 2). `fire` records the act and chooses nothing."""

    def __init__(self, row, samples: int):
        self.row, self.samples, self.fired = row, samples, None

    def outcome(self, act):
        if act == "confidence":
            return self.row["b"]
        if act == "agreement":
            return "all" if self.row["k"] == self.samples else "some"
        if act == "second_opinion":
            return self.row["s"]
        grade = self.row["grade2"] if self.fired == "answer_second" else self.row["grade1"]
        return "right" if grade == "CORRECT" else "not"

    def fire(self, act):
        self.fired = act


def played(result) -> Played:
    acts = result.acts
    end = acts[-1]
    looked = "second_opinion" in acts
    blind = end == "answer_second" and not looked
    return Played({"answer_primary": "primary", "answer_second": "second", "abstain": "abstain"}[end],
                  "agreement" in acts, looked or blind, blind, end == "answer_second" and looked)


def play_plate(world, rows: Sequence, samples: int, fresh: bool = False):
    """Every row as one episode of one plate, in the given order: (Played, Result) per row. With `fresh`, each
    episode is played from the declared prior on a plate of its own: the Counts never conditioned on (E7)."""
    plate = wald.plate(world)
    out = []
    for r in rows:
        res = (wald.plate(world) if fresh else plate).run(RecordedDoor(r, samples))
        if res.status not in ("TERMINAL",):
            raise RuntimeError(f"question {r['question_id']} ended {res.status}")
        out.append((played(res), res))
    return plate, out


# ---------------------------------------------------------------- scoring

def grade_of(row, submitted: str) -> str:
    return {"primary": row["grade1"], "second": row["grade2"], "abstain": "NOT_ATTEMPTED"}[submitted]


def answer_utility(row, pl: Played, p: Fraction) -> Fraction:
    return u(grade_class(grade_of(row, pl.submitted)), p)


def net_utility(row, pl: Played, p: Fraction, agreement: Fraction, c: Fraction) -> Fraction:
    return answer_utility(row, pl, p) - agreement * pl.agreement - c * pl.consulted


@dataclass(frozen=True)
class Line:
    contestant: str
    n: int
    score: float            # mean answer utility under p (x100 at p = 1 is the Omniscience Index)
    net: float              # score less what the contestant bought, in utility
    coverage: float
    accuracy: float
    hallucination: float    # AA's: incorrect / (partial + incorrect + abstained); an ungraded reply is incorrect
    consult_rate: float
    agreement_rate: float
    blind: int
    overcharged: int
    nets: tuple             # per question, for paired differences


def line(name: str, rows: Sequence, plays: Sequence[Played], p, agreement, c) -> Line:
    grades = [grade_of(r, pl.submitted) for r, pl in zip(rows, plays)]
    nets = tuple(float(net_utility(r, pl, p, agreement, c)) for r, pl in zip(rows, plays))
    right, wrong = grades.count("CORRECT"), grades.count("INCORRECT") + grades.count("UNGRADED")
    n = len(rows)
    return Line(name, n, statistics.mean(float(answer_utility(r, pl, p)) for r, pl in zip(rows, plays)),
                statistics.mean(nets), sum(pl.submitted != "abstain" for pl in plays) / n, right / n,
                wrong / (n - right) if n > right else math.nan, sum(pl.consulted for pl in plays) / n,
                sum(pl.agreement for pl in plays) / n, sum(pl.blind for pl in plays),
                sum(pl.overcharged for pl in plays), nets)


def paired(a: Line, b: Line, keep=None) -> tuple[float, float]:
    "Mean of a - b per question, and its standard error; with `keep`, only the questions it marks."
    d = [x - y for i, (x, y) in enumerate(zip(a.nets, b.nets)) if keep is None or keep[i]]
    return statistics.mean(d), (statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else math.nan)


def baselines(test_rows, cal_rows, buckets, p) -> dict[str, list[Played]]:
    ctx = dict(rates=bucket_rates(cal_rows, buckets), p=p, second_better=second_is_better(cal_rows, p))
    return {name: [f(r, **ctx) for r in test_rows] for name, f in BASELINES.items()}
