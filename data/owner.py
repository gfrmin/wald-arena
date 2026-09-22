"""The owner's numbers, read from `owner.toml`. A missing number is an error that names it, never a default."""
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from oracle.game import Game, tiers_by_fives

ROOT = Path(__file__).resolve().parent.parent
OWNER_TOML = ROOT / "owner.toml"


class MissingOwnerNumber(KeyError):
    def __str__(self):
        return f"owner.toml has no `{self.args[0]}`: it is the owner's number, not ours (see QUESTIONS.md)"


def load(path: Path = OWNER_TOML) -> Mapping[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def need(owner: Mapping[str, Any], key: str) -> Any:
    "The value at a dotted key, e.g. 'instruments.llm.model'; MissingOwnerNumber if any part is absent."
    node: Any = owner
    for part in key.split("."):
        if not isinstance(node, Mapping) or part not in node:
            raise MissingOwnerNumber(key)
        node = node[part]
    return node


def ladder(owner) -> tuple[Fraction, ...]:
    return tuple(Fraction(p) for p in need(owner, "ladder.prizes"))


def havens(owner) -> tuple[int, ...]:
    "0-based rung indices of the safe havens (owner.toml holds 1-based question numbers)."
    return tuple(q - 1 for q in need(owner, "ladder.havens"))


def lambda_usd(owner) -> Fraction:
    return Fraction(Decimal(need(owner, "lambda_usd")))


@dataclass(frozen=True)
class InstrumentSpec:
    name: str
    model: str
    usd_per_call: Decimal


def instrument(owner, name: str) -> InstrumentSpec:
    return InstrumentSpec(name, need(owner, f"instruments.{name}.model"),
                          Decimal(need(owner, f"instruments.{name}.usd_per_call")))


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
