"""BASELINE -- always answer: read the LLM once per question, answer its report, never walk, never use a lifeline.

This is a baseline, labelled as one (CLAUDE.md rule 1). The wald contestant never calls it.
"""
from fractions import Fraction
from functools import cache

from explainers.millionaire.oracle.game import OPTIONS, Game
from explainers.millionaire.oracle.host import Decision, GameLog, View

NAME = "always answer"


def expected(game: Game, r: int = 0) -> Fraction:
    """Expected utility from rung r by backward induction, as proto.py's A(r): pay the read, then the report is
    right with the tier's reliability (go on) or wrong (keep the safe haven)."""
    rho, c = game.reliability["llm"], game.price["llm"]

    @cache
    def A(r: int) -> Fraction:
        if r == game.rungs:
            return game.ladder[-1]
        p = rho[game.tiers[r]]
        return p * A(r + 1) + (1 - p) * game.safe(r) - c

    return A(r)


def contestant(view: View) -> Decision:
    "Answer the LLM's report. Given an unparseable read it still answers, and answers A (QUESTIONS.md, 6)."
    report = dict(view.history).get("llm")
    return Decision(f"answer {report if report in OPTIONS else 'A'}")


def realised(log: GameLog) -> Fraction:
    "Realised winnings from a game log."
    return log.winnings
