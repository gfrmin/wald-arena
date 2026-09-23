"""The four contestants on the test split, at one penalty and one second-opinion price, and what each scored.

Baselines 2-4 are labelled as baselines (rule 1): the threshold reads the fitted prior and compares, which only a
baseline may do. wald's acts come from `packs.Board.play`, which is `wald.run` on the generated packs.
"""
import math
import statistics
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping, Sequence

from showcases.omniscience.fit import grade_class
from showcases.omniscience.packs import Board, Path_, Prices, u

CONTESTANTS = ("raw model", "calibrated threshold", "better single model", "wald")


@dataclass(frozen=True)
class Played:
    submitted: str          # primary | second | abstain
    agreement: bool
    consulted: bool


def raw(row, **_) -> Played:
    return Played("primary", False, False)


def threshold(row, f, pr: Prices, **_) -> Played:
    "BASELINE: answer the read iff its bucket's fitted P(right) - p P(wrong) > 0."
    q = f["g1"][row["b"]]
    return Played("primary" if q["right"] - pr.p * q["wrong"] > 0 else "abstain", False, False)


def better_single(row, pr: Prices, second_better: bool, **_) -> Played:
    "BASELINE: whichever model scored higher under p on calibration, answering raw; the second pays its price."
    use_second = second_better and pr.consult is not None
    return Played("second" if use_second else "primary", False, use_second)


def wald_plays(row, board: Board, **_) -> Played:
    path: Path_ = board.play(row["b"], row["k"], row["s"])
    return Played(path.submitted, path.agreement, path.consulted)


PLAYERS: Mapping[str, Callable] = dict(zip(CONTESTANTS, (raw, threshold, better_single, wald_plays)))


def grade_of(row, submitted: str) -> str:
    return {"primary": row["grade1"], "second": row["grade2"], "abstain": "NOT_ATTEMPTED"}[submitted]


def answer_utility(row, played: Played, p: Fraction) -> Fraction:
    return u(grade_class(grade_of(row, played.submitted)), p)


def net_utility(row, played: Played, pr: Prices) -> Fraction:
    return answer_utility(row, played, pr.p) - pr.agreement * played.agreement - (pr.consult or 0) * played.consulted


def second_is_better(cal_rows, p: Fraction) -> bool:
    return sum(u(r["g2"], p) for r in cal_rows) > sum(u(r["g1"], p) for r in cal_rows)


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
    nets: tuple             # per question, for paired differences


def line(name: str, rows: Sequence, plays: Sequence[Played], pr: Prices) -> Line:
    grades = [grade_of(r, pl.submitted) for r, pl in zip(rows, plays)]
    nets = tuple(float(net_utility(r, pl, pr)) for r, pl in zip(rows, plays))
    c, i = grades.count("CORRECT"), grades.count("INCORRECT") + grades.count("UNGRADED")  # scored wrong, counted so
    n = len(rows)
    return Line(name, n, statistics.mean(float(answer_utility(r, pl, pr.p)) for r, pl in zip(rows, plays)),
                statistics.mean(nets), sum(pl.submitted != "abstain" for pl in plays) / n, c / n,
                i / (n - c) if n > c else math.nan, sum(pl.consulted for pl in plays) / n,
                sum(pl.agreement for pl in plays) / n, nets)


def paired(a: Line, b: Line) -> tuple[float, float]:
    "Mean of a - b per question, and its standard error."
    d = [x - y for x, y in zip(a.nets, b.nets)]
    return statistics.mean(d), (statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else math.nan)


def play_all(test_rows, cal_rows, f, board: Board) -> dict[str, Line]:
    pr = board.pr
    ctx = dict(f=f, pr=pr, board=board, second_better=second_is_better(cal_rows, pr.p))
    return {name: line(name, test_rows, [player(r, **ctx) for r in test_rows], pr) for name, player in PLAYERS.items()}
