"""An owner file, read. Each showcase keeps its own; a missing number is an error that names it, never a default."""
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping


class MissingOwnerNumber(KeyError):
    def __str__(self):
        return f"the owner file has no `{self.args[0]}`: it is the owner's number, not ours (see QUESTIONS.md)"


def load(path: Path) -> Mapping[str, Any]:
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


@dataclass(frozen=True)
class InstrumentSpec:
    name: str
    model: str
    usd_per_call: Decimal


def instrument(owner, name: str) -> InstrumentSpec:
    return InstrumentSpec(name, need(owner, f"instruments.{name}.model"),
                          Decimal(need(owner, f"instruments.{name}.usd_per_call")))
