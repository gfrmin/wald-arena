"""The fitting math every showcase shares: the Beta(1,1) posterior mean of a count, and the held-out log score.

One scorer, so held-out numbers are comparable across showcases: the mean natural-log probability a fitted kernel
gave to what the held-out slice actually showed (higher is better; 0 is perfect). A showcase says what its cells
and outcomes are; this module only counts and scores.
"""
import math
from fractions import Fraction
from typing import Hashable, Iterable, Mapping, TypeVar

K = TypeVar("K", bound=Hashable)


def beta11_mean(right: int, wrong: int) -> Fraction:
    "Beta(1,1) posterior mean of a right/wrong count, exact."
    return Fraction(right + 1, right + wrong + 2)


def dirichlet1_mean(counts: Mapping[K, int]) -> dict[K, Fraction]:
    "Dirichlet(1,...,1) posterior mean over the given outcomes, exact: Beta(1,1) when there are two."
    n = sum(counts.values())
    return {k: Fraction(c + 1, n + len(counts)) for k, c in counts.items()}


def held_out_log_score(probabilities: Iterable[Fraction | float]) -> float:
    """Mean log of the probability the fitted kernel assigned to each held-out observation's actual outcome;
    nan on an empty slice."""
    ps = [float(p) for p in probabilities]
    return sum(math.log(p) for p in ps) / len(ps) if ps else math.nan


def uniform_log_score(k_outcomes: int) -> float:
    "The score of a kernel that carries no information over k outcomes."
    return math.log(1 / k_outcomes)
