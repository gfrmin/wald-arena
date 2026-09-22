"""Counts -> reliabilities. For each tier: rho = the Beta(1,1) posterior mean of the calibration counts, an exact
rational; its held-out log score on the held-out slice. No float leaves this module as a reliability.

    python -m calibration.fit --instrument llm     # calibration/llm.jsonl -> calibration/fitted/llm.json

The fitted file is what the pack generator reads: per tier the counts, rho as "p/q", and the held-out score.
An unparseable read counts as wrong, in the fit and in the score (QUESTIONS.md, 6); the score gives it the
wrong-option probability (1 - rho) / 3.
"""
import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

from calibration.run import HERE, read_rows, rows_path
from data.questions import TIERS


@dataclass(frozen=True)
class TierFit:
    tier: int
    right: int
    wrong: int
    held_right: int
    held_wrong: int

    @property
    def rho(self) -> Fraction:
        "Beta(1,1) posterior mean."
        return Fraction(self.right + 1, self.right + self.wrong + 2)

    @property
    def held_n(self) -> int:
        return self.held_right + self.held_wrong

    @property
    def log_score(self) -> float:
        "Mean natural-log score of the fitted kernel on the held-out slice (higher is better; 0 is perfect)."
        if not self.held_n:
            return math.nan
        r = self.rho
        return (self.held_right * math.log(r) + self.held_wrong * math.log((1 - r) / 3)) / self.held_n

    UNIFORM = math.log(1 / 4)  # the score of a read that carries no information


def fit(rows: Iterable[dict]) -> tuple[TierFit, ...]:
    rows = list(rows)
    count = lambda t, s, right: sum(r["tier"] == t and r["slice"] == s and r["right"] is right for r in rows)
    tiers = sorted({r["tier"] for r in rows})
    return tuple(TierFit(t, count(t, "calibration", True), count(t, "calibration", False),
                         count(t, "held_out", True), count(t, "held_out", False)) for t in tiers)


def fitted_path(instrument: str) -> Path:
    return HERE / "fitted" / f"{instrument}.json"


def document(instrument: str, fits: tuple[TierFit, ...], rows_file: Path) -> dict:
    return {
        "instrument": instrument, "source": "fitted", "method": "Beta(1,1) posterior mean of calibration counts",
        "rows": rows_file.name, "rows_sha256": hashlib.sha256(rows_file.read_bytes()).hexdigest(),
        "tiers": [{"tier": TIERS[f.tier], "right": f.right, "wrong": f.wrong, "rho": str(f.rho),
                   "held_out": {"n": f.held_n, "right": f.held_right, "wrong": f.held_wrong,
                                "log_score": f.log_score, "uniform_log_score": TierFit.UNIFORM}}
                  for f in fits],
    }


def reliability(path: Path) -> tuple[Fraction, ...]:
    "rho per tier from a fitted file, as Fractions; every tier must be present."
    doc = json.loads(path.read_text())
    by_tier = {t["tier"]: Fraction(t["rho"]) for t in doc["tiers"]}
    if missing := [t for t in TIERS if t not in by_tier]:
        raise ValueError(f"{path}: no fit for tiers {missing}")
    return tuple(by_tier[t] for t in TIERS)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--instrument", required=True, choices=("llm", "phone", "audience"))
    p.add_argument("--rows", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    rows_file = a.rows or rows_path(a.instrument)
    fits = fit(read_rows(rows_file))
    out = a.out or fitted_path(a.instrument)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document(a.instrument, fits, rows_file), indent=2) + "\n")
    for f in fits:
        print(f"{a.instrument} {TIERS[f.tier]:6s} {f.right}/{f.right + f.wrong} right, rho = {f.rho}, "
              f"held-out log score {f.log_score:.4f} (uniform {TierFit.UNIFORM:.4f})")


if __name__ == "__main__":
    main()
