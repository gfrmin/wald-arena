"""The exact game: "Who Wants to Be a Millionaire" as one multi-stage decision problem, in exact rationals.

This is the oracle the wald contestant is judged against (brief 001, J2). At each rung the contestant faces a
stage tree over the outcomes of four instruments -- the LLM read (once per question), 50:50, phone and audience
(each once per game) -- and ends the stage by answering an option or walking. A right answer moves to the next
rung with whatever lifelines are still held; a wrong one keeps the last safe haven; walking keeps the last prize.

Rungs are 0-based, as in `proto.py`: `r = 0` is Q1, and `ladder[r]` is the prize held after answering rung r.

Three things are computed here, all by backward induction over `Fraction`s:

- `exact(game)`: the optimum of the whole game. A lifeline costs nothing but itself: using it shrinks the set
  carried into every later stage.
- `option_value(game)`: the per-stage approximation the wald contestant plays (J1). Each stage is solved alone;
  a right answer is worth V(r+1, held) whatever was used, and each lifeline is charged its option value
  V(r+1, held) - V(r+1, held - {l}). This reproduces `proto.py`'s `solve_game`.
- `policy_value(game, act)`: what a policy actually earns in the exact game. The approximation's regret is
  `exact` minus `policy_value` of the approximation's policy; that is non-negative by construction.

Menu order and tie-breaking follow the charter's reference solver (`spec_check.Ref`): answers A-D, then walk,
then instruments in the order llm, fifty, phone, audience; a later act replaces the incumbent only if strictly
better. The policy an approximation induces is therefore the one the wald kernel would pick.
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from math import prod
from typing import Callable, Mapping

OPTIONS = ("A", "B", "C", "D")
LIFELINES = ("fifty", "phone", "audience")
INSTRUMENTS = ("llm",) + LIFELINES
ALL_LIFELINES = frozenset(LIFELINES)

History = frozenset  # of (instrument, outcome) pairs observed in the current stage; order is irrelevant to belief
Kernel = Mapping[str, Mapping[str, Fraction]]  # truth -> outcome -> probability


def noisy(rho: Fraction) -> Kernel:
    "A report that names the truth with probability rho, else one of the three wrong options uniformly."
    return {w: {o: (rho if o == w else (1 - rho) / 3) for o in OPTIONS} for w in OPTIONS}


def fifty() -> Kernel:
    "Keeps the truth and one wrong option, uniformly; the outcome is the unordered pair, e.g. 'AC'."
    return {w: {"".join(sorted(w + x)): Fraction(1, 3) for x in OPTIONS if x != w} for w in OPTIONS}


def tiers_by_fives(rungs: int) -> tuple[int, ...]:
    "The brief's tiers: easy Q1-5, medium Q6-10, hard Q11-15 (and hard beyond)."
    return tuple(min(r // 5, 2) for r in range(rungs))


@dataclass(frozen=True)
class Game:
    """The rules and the instruments.

    ladder:      prize held after answering rung r right, r = 0 .. len(ladder)-1; the last is the top prize.
    havens:      rungs whose prize is kept after a later wrong answer (proto: (4, 9), i.e. after Q5 and Q10).
    reliability: for each noisy instrument ('llm', 'phone', 'audience'), its rho per tier.
    price:       what firing each instrument costs, in ladder units ('llm', 'fifty', 'phone', 'audience').
    tiers:       the tier of each rung.
    """
    ladder: tuple[Fraction, ...]
    havens: tuple[int, ...]
    reliability: Mapping[str, tuple[Fraction, ...]]
    price: Mapping[str, Fraction]
    tiers: tuple[int, ...]

    @property
    def rungs(self) -> int:
        return len(self.ladder)

    def walk(self, r: int) -> Fraction:
        "Walking at rung r keeps the previous rung's prize."
        return self.ladder[r - 1] if r > 0 else Fraction(0)

    def safe(self, r: int) -> Fraction:
        "A wrong answer at rung r keeps the highest haven below r."
        return max((self.ladder[h] for h in self.havens if h < r), default=Fraction(0))

    def kernel(self, instrument: str, r: int) -> Kernel:
        return fifty() if instrument == "fifty" else noisy(self.reliability[instrument][self.tiers[r]])


def lifelines_used(h: History) -> frozenset:
    return frozenset(k for k, _ in h if k in ALL_LIFELINES)


def posterior(kernels: Mapping[str, Kernel], h: History) -> dict[str, Fraction]:
    "Uniform prior over the right option, conditioned on every observation in h."
    like = {w: prod((kernels[k][w].get(o, Fraction(0)) for k, o in h), start=Fraction(1)) for w in OPTIONS}
    z = sum(like.values())
    return {w: p / z for w, p in like.items()}


def outcomes(b: Mapping[str, Fraction], kernel: Kernel) -> dict[str, Fraction]:
    "The predictive distribution of an instrument's outcome, restricted to outcomes of positive mass."
    push = {}
    for w, p in b.items():
        for o, q in kernel[w].items():
            push[o] = push.get(o, Fraction(0)) + p * q
    return {o: p for o, p in push.items() if p > 0}


@dataclass(frozen=True)
class Stage:
    "One rung with a given set of lifelines held on arrival: the instruments on offer and the terminal payoffs."
    game: Game
    r: int
    held: frozenset

    @property
    def kernels(self) -> dict[str, Kernel]:
        return {k: self.game.kernel(k, self.r) for k in INSTRUMENTS if k == "llm" or k in self.held}


def solve_stage(stage: Stage, correct: Callable[[History], Fraction], price: Callable[[str], Fraction]):
    """Exact solution of one stage tree. `correct(h)` is what a right answer is worth after history h; `price(k)`
    is what firing k is charged. Returns h -> (value, act), memoised."""
    kernels, wrong, walk = stage.kernels, stage.game.safe(stage.r), stage.game.walk(stage.r)

    @cache
    def solve(h: History) -> tuple[Fraction, str]:
        b, win = posterior(kernels, h), correct(h)
        best, arg = None, None
        for x in OPTIONS:
            v = b[x] * win + (1 - b[x]) * wrong
            if best is None or v > best:
                best, arg = v, f"answer {x}"
        if walk > best:
            best, arg = walk, "walk"
        used = {k for k, _ in h}
        for k in (k for k in kernels if k not in used):
            v = -price(k) + sum(p * solve(h | {(k, o)})[0] for o, p in outcomes(b, kernels[k]).items())
            if v > best:
                best, arg = v, k
        return best, arg

    return solve


@dataclass(frozen=True)
class Solution:
    """value(r, held): expected winnings from rung r holding `held`, under this solution's own model.
    act(r, held, h): the act it takes at the stage for (r, held) after observing history h."""
    value: Callable[[int, frozenset], Fraction]
    act: Callable[..., str]


def exact(game: Game) -> Solution:
    "The optimum of the whole game: lifelines are free in themselves and cost only their absence later."
    @cache
    def stage(r: int, held: frozenset):
        return solve_stage(Stage(game, r, held),
                           correct=lambda h: value(r + 1, held - lifelines_used(h)),
                           price=lambda k: game.price[k])

    @cache
    def value(r: int, held: frozenset) -> Fraction:
        return game.ladder[-1] if r == game.rungs else stage(r, held)(frozenset())[0]

    return Solution(value, lambda r, held, h=frozenset(): stage(r, held)(h)[1])


def option_value(game: Game) -> Solution:
    """The per-stage approximation (J1), as `proto.py`'s `solve_game`: a right answer is worth V(r+1, held) and
    lifeline l is charged its price plus its option value V(r+1, held) - V(r+1, held - {l})."""
    @cache
    def stage(r: int, held: frozenset):
        nxt = value(r + 1, held)
        charge = lambda k: game.price[k] + (nxt - value(r + 1, held - {k}) if k in ALL_LIFELINES else 0)
        return solve_stage(Stage(game, r, held), correct=lambda h: nxt, price=charge)

    @cache
    def value(r: int, held: frozenset) -> Fraction:
        return game.ladder[-1] if r == game.rungs else stage(r, held)(frozenset())[0]

    return Solution(value, lambda r, held, h=frozenset(): stage(r, held)(h)[1])


def policy_value(game: Game, act: Callable[[int, frozenset, History], str]) -> Callable[[int, frozenset], Fraction]:
    "What following `act` earns in the exact game, from (r, held): real prices, real lifelines carried forward."
    @cache
    def value(r: int, held: frozenset) -> Fraction:
        if r == game.rungs:
            return game.ladder[-1]
        stage = Stage(game, r, held)
        kernels, wrong = stage.kernels, game.safe(r)

        def follow(h: History) -> Fraction:
            a, b = act(r, held, h), posterior(kernels, h)
            if a == "walk":
                return game.walk(r)
            if a.startswith("answer "):
                x = a.removeprefix("answer ")
                return b[x] * value(r + 1, held - lifelines_used(h)) + (1 - b[x]) * wrong
            return -game.price[a] + sum(p * follow(h | {(a, o)}) for o, p in outcomes(b, kernels[a]).items())

        return follow(frozenset())

    return value


@dataclass(frozen=True)
class Regret:
    exact: Fraction        # the optimum of the whole game
    estimate: Fraction     # the approximation's own value (what wald believes it will earn)
    realised: Fraction     # what the approximation's policy earns in the exact game

    @property
    def regret(self) -> Fraction:
        "exact - realised: the approximation's regret, >= 0."
        return self.exact - self.realised

    @property
    def gap(self) -> Fraction:
        "exact - estimate: how far the approximation's self-assessment is from the optimum (either sign)."
        return self.exact - self.estimate


def regret(game: Game, r: int = 0, held: frozenset = ALL_LIFELINES) -> Regret:
    approx = option_value(game)
    return Regret(exact=exact(game).value(r, held),
                  estimate=approx.value(r, held),
                  realised=policy_value(game, approx.act)(r, held))
