"""The scoreboard's formatting toolkit: dollars, Markdown tables, quantiles, and sections joined into a report."""
import statistics
from typing import Sequence

NOT_YET = "not yet"


def usd(x) -> str:
    x = float(x)
    return f"${x:,.0f}" if abs(x) >= 100 or x == int(x) else f"${x:,.2f}"


def table(header: Sequence[str], body: Sequence[Sequence]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(str(c) for c in r) + " |" for r in body])


def quantile(xs: Sequence[float], q: float) -> float:
    return statistics.quantiles(xs, n=100, method="inclusive")[int(q * 100) - 1] if len(xs) > 1 else xs[0]


def join_sections(sections: Sequence[str]) -> str:
    return "\n\n".join(sections) + "\n"
