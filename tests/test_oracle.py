"""The exact game (oracle/game.py), proved against the prototype and against itself."""
import os
import sys
from fractions import Fraction as F
from functools import cache
from itertools import combinations
from pathlib import Path

import pytest

from oracle.game import (ALL_LIFELINES, INSTRUMENTS, LIFELINES, OPTIONS, Game, exact, fifty, noisy, option_value,
                         policy_value, regret, tiers_by_fives)
from oracle.prototype import GAME

HELD_SETS = [frozenset(c) for n in range(4) for c in combinations(LIFELINES, n)]
CHARTER_LAWS = Path(os.environ.get("WALD_CHARTER_LAWS", Path.home() / "git/wald-charter/laws"))


def histories(game, r, held):
    "Every stage history reachable with positive mass, including the empty one."
    kernels = {k: game.kernel(k, r) for k in INSTRUMENTS if k == "llm" or k in held}
    out = {frozenset()}
    frontier = [frozenset()]
    while frontier:
        h = frontier.pop()
        used = {k for k, _ in h}
        for k in kernels:
            if k in used:
                continue
            for o in {o for w in OPTIONS for o in kernels[k][w]}:
                g = h | {(k, o)}
                if any(all(kernels[i][w].get(x, 0) > 0 for i, x in g) for w in OPTIONS) and g not in out:
                    out.add(g)
                    frontier.append(g)
    return out


def test_kernels_are_distributions():
    for K in (noisy(F(7, 10)), fifty()):
        assert all(sum(row.values()) == 1 for row in K.values())


def test_prototype_value_reproduced():
    assert round(float(option_value(GAME).value(0, ALL_LIFELINES)), 1) == 294.5


def test_exact_game_dominates_the_approximation_on_the_prototype():
    R = regret(GAME)
    print(f"\nexact ${float(R.exact):.3f}k, estimate ${float(R.estimate):.3f}k, realised ${float(R.realised):.3f}k, "
          f"regret ${float(R.regret):.3f}k, gap ${float(R.gap):.3f}k")
    assert R.exact >= R.estimate
    assert R.exact >= R.realised
    assert R.regret >= 0


def test_regret_nonnegative_everywhere_on_the_prototype():
    E, A = exact(GAME), option_value(GAME)
    P = policy_value(GAME, A.act)
    for r in range(GAME.rungs):
        for held in HELD_SETS:
            assert E.value(r, held) >= P(r, held)


def test_exact_policy_earns_its_value():
    E = exact(GAME)
    assert policy_value(GAME, E.act)(0, ALL_LIFELINES) == E.value(0, ALL_LIFELINES)


def test_lifelines_never_hurt():
    E = exact(GAME)
    for r in range(GAME.rungs):
        for a in HELD_SETS:
            for b in HELD_SETS:
                if a <= b:
                    assert E.value(r, a) <= E.value(r, b)


def test_always_answer_policy_matches_proto_A():
    "policy_value on the always-answer policy reproduces proto.py's A(r) = $211.4k."
    rho, c = GAME.reliability["llm"], GAME.price["llm"]

    @cache
    def A(r):
        if r == GAME.rungs:
            return GAME.ladder[-1]
        return rho[GAME.tiers[r]] * A(r + 1) + (1 - rho[GAME.tiers[r]]) * GAME.safe(r) - c

    act = lambda r, held, h: "llm" if not h else f"answer {dict(h)['llm']}"
    assert policy_value(GAME, act)(0, ALL_LIFELINES) == A(0)
    assert round(float(A(0)), 1) == 211.4


SINGLE_RUNG_GAMES = [
    Game(ladder=(F(1000),), havens=(), reliability={"llm": (rl,), "phone": (rp,), "audience": (ra,)},
         price={"llm": c, "fifty": F(0), "phone": F(0), "audience": F(0)}, tiers=(0,))
    for rl, rp, ra, c in [(F(95, 100), F(9, 10), F(9, 10), F(1)), (F(3, 10), F(1, 4), F(1, 2), F(0)),
                          (F(6, 10), F(5, 10), F(45, 100), F(50)), (F(1, 4), F(1, 4), F(1, 4), F(1, 1000))]
]


@pytest.mark.parametrize("game", SINGLE_RUNG_GAMES)
def test_single_rung_game_approximation_is_exact(game):
    E, A = exact(game), option_value(game)
    for held in HELD_SETS:
        assert E.value(0, held) == A.value(0, held)
        for h in histories(game, 0, held):
            assert E.act(0, held, h) == A.act(0, held, h)
    assert regret(game).regret == 0 and regret(game).gap == 0


def test_last_rung_of_prototype_approximation_is_exact():
    E, A = exact(GAME), option_value(GAME)
    for held in HELD_SETS:
        assert E.value(14, held) == A.value(14, held)


@pytest.mark.skipif(not (CHARTER_LAWS / "spec_check.py").exists(), reason="wald-charter laws not on disk")
def test_differential_against_charter_reference_on_every_stage():
    """Every one of the 120 stage Worlds proto.py builds, solved by the charter's reference solver, agrees with
    option_value's value and first act exactly -- so option_value is proto.py's solve_game, by induction."""
    sys.path.insert(0, str(CHARTER_LAWS))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import proto
    import spec_check as S
    A = option_value(GAME)
    rho, rho_p, rho_a = ({t: v for t, v in enumerate(GAME.reliability[k])} for k in ("llm", "phone", "audience"))
    for r in range(GAME.rungs):
        for held in HELD_SETS:
            w = proto.stage_world(r, held, rho, rho_p, rho_a, GAME.price["llm"], lambda L: A.value(r + 1, L))
            assert S.REF.solve(w["prior"], w, w["N"]) == (A.value(r, held), A.act(r, held))
