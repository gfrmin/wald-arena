"""Millionaire's numbers, read from its own `owner.toml`: the ladder, havens, λ_usd and prices."""
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Mapping

from arena.config import InstrumentSpec, MissingOwnerNumber, instrument, need  # noqa: F401 (re-exported)
from arena.config import load as _load
from explainers.millionaire.oracle.game import Game, tiers_by_fives

ROOT = Path(__file__).resolve().parent
OWNER_TOML = ROOT / "owner.toml"


def load(path: Path = OWNER_TOML):
    return _load(path)


def ladder(owner) -> tuple[Fraction, ...]:
    return tuple(Fraction(p) for p in need(owner, "ladder.prizes"))


def havens(owner) -> tuple[int, ...]:
    "0-based rung indices of the safe havens (owner.toml holds 1-based question numbers)."
    return tuple(q - 1 for q in need(owner, "ladder.havens"))


def lambda_usd(owner) -> Fraction:
    return Fraction(Decimal(need(owner, "lambda_usd")))


def prices(owner) -> dict[str, Fraction]:
    """What each act is charged, in utility (= dollars of winnings): declared API cost x lambda_usd for the model
    calls, and the ruled price of the 50:50."""
    lam = lambda_usd(owner)
    calls = {k: Fraction(instrument(owner, k).usd_per_call) * lam for k in ("llm", "phone", "audience")}
    return calls | {"fifty": Fraction(Decimal(need(owner, "rulings.fifty_usd"))) * lam}


def game(owner, reliability: Mapping[str, tuple[Fraction, ...]]) -> Game:
    "The game played: the owner's ladder, havens, prices and read-first ruling, with the fitted reliabilities."
    prizes = ladder(owner)
    return Game(ladder=prizes, havens=havens(owner), reliability=dict(reliability), price=prices(owner),
                tiers=tiers_by_fives(len(prizes)), read_first=bool(need(owner, "rulings.read_first")))
