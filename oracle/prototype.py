"""The prototype's game, from `proto.py`: its ladder (in $k), havens, and ILLUSTRATIVE reliabilities.

These numbers are author-side illustrations used only to prove the oracle against the prototype. They are not
the owner's numbers and no contestant reads them; the real reliabilities are fitted cells in packs (rule 2).

Run `python -m oracle.prototype` to print the exact game's value, the approximation's, and the regret.
"""
from fractions import Fraction as F

from oracle.game import ALL_LIFELINES, Game, regret, tiers_by_fives

LADDER = tuple(F(x) for x in ("0.5", 1, 2, 3, 5, 7, 10, 20, 30, 50, 100, 250, 500, 1000, 10000))
HAVENS = (4, 9)
RELIABILITY = {
    "llm": (F(95, 100), F(80, 100), F(60, 100)),
    "phone": (F(9, 10), F(7, 10), F(5, 10)),
    "audience": (F(9, 10), F(75, 100), F(45, 100)),
}
PRICE = {"llm": F(1, 1000), "fifty": F(0), "phone": F(0), "audience": F(0)}  # $1 per LLM read; lifelines free

GAME = Game(ladder=LADDER, havens=HAVENS, reliability=RELIABILITY, price=PRICE, tiers=tiers_by_fives(len(LADDER)))

if __name__ == "__main__":
    R = regret(GAME, 0, ALL_LIFELINES)
    k = lambda x: f"${float(x):,.3f}k"
    print("prototype game, rung 1, all lifelines held ($k):")
    print(f"  exact game optimum                     {k(R.exact)}")
    print(f"  option-value approximation, estimate   {k(R.estimate)}")
    print(f"  approximation's policy, in exact game  {k(R.realised)}")
    print(f"  regret  (exact - realised)             {k(R.regret)}   = {R.regret}")
    print(f"  gap     (exact - estimate)             {k(R.gap)}   = {R.gap}")
