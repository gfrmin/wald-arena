"""The oracle plays: the exact game's optimal policy as a contestant (the owner's fourth contestant, 2026-09-22).

It sees what any contestant sees -- the LLM's read and whatever lifelines it fires -- and acts by the exact game's
backward induction over the fitted reliabilities. It is the ceiling the wald contestant's regret is measured
against, played on the same questions with the same instruments.
"""
from fractions import Fraction

from explainers.millionaire.oracle.game import ALL_LIFELINES, Game, exact
from explainers.millionaire.oracle.host import Contestant, Decision, View

NAME = "the oracle plays"


def contestant(game: Game) -> Contestant:
    solution = exact(game)
    return lambda view: Decision(solution.act(view.rung, view.held, view.observed))


def expected(game: Game) -> Fraction:
    return exact(game).value(0, ALL_LIFELINES)
