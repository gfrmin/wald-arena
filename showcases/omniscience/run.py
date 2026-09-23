"""The AA-Omniscience pipeline, end to end: draw, observe, grade, fit, generate packs, play, score.

    python -m showcases.omniscience.run --dry-run --budget-usd 3

Without --dry-run the numbers come from `owner.toml`, which names no instrument until QUESTIONS.md's
pre-registration is ruled, so the run stops at the first missing number and calls nothing. With --dry-run they come
from `dryrun.toml` (proposals, not rulings), and every instrument must be one of DRY_RUN_MODELS.

Spend is budget-first. The number of questions is set so that every call, at its declared price, fits the budget;
before each call its declared price is reserved and written to `reserved.jsonl`, and the run stops rather than
exceed the budget. Records are appended one question at a time, so an interrupted run resumes; the calls of a
question cut off mid-way are made again, but the wallet remembers their reservations, so the budget still holds.
"""
import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from arena.config import load, need
from arena.spend import append_new, read_rows
from arena.transports import Call, Instrument, from_owner
from showcases.omniscience import board as B
from showcases.omniscience import fit as FIT
from showcases.omniscience import observe as OBS
from showcases.omniscience import questions as QS
from showcases.omniscience.grader import Grader
from showcases.omniscience.grader import calls as grading_calls
from showcases.omniscience.packs import Board, Prices, provenance

HERE = Path(__file__).resolve().parent
OWNER = HERE / "owner.toml"
DRY_RUN = HERE / "dryrun.toml"
DRY_RUN_MODELS = ("claude-haiku-4-5-20251001",)
ROLES = ("primary", "second", "grader")


class BudgetExceeded(RuntimeError):
    pass


class NotADryRunModel(RuntimeError):
    pass


class Budget:
    """Every call's declared price is reserved, and written to `log`, before the call is made. The wallet starts from
    that log, so a run cut off mid-question resumes knowing what it already paid."""
    def __init__(self, limit: Decimal, log: Path | None = None):
        self.limit, self.log = limit, log
        self.spent = sum((Decimal(r["usd"]) for r in read_rows(log)), Decimal(0)) if log else Decimal(0)

    def reserve(self, instrument: Instrument):
        if self.spent + instrument.usd_per_call > self.limit:
            raise BudgetExceeded(f"the next {instrument.name} call (${instrument.usd_per_call}) would take the "
                                 f"declared spend past ${self.limit} (spent ${self.spent})")
        self.spent += instrument.usd_per_call
        if self.log:
            with open(self.log, "a") as f:
                f.write(json.dumps({"instrument": instrument.name, "usd": str(instrument.usd_per_call)}) + "\n")


@dataclass(frozen=True)
class Settings:
    lambda_usd: Fraction
    penalties: tuple[Fraction, ...]
    grid: tuple[Fraction | None, ...]
    split_seed: int
    sampling_seed: int
    cuts: tuple[int, ...]
    samples: int
    min_count: int
    folds: int

    @property
    def buckets(self):
        return OBS.bucket_names(self.cuts)


def settings(owner) -> Settings:
    grid = tuple(None if c == "none" else Fraction(c) for c in need(owner, "second_price_grid"))
    if need(owner, "agreement.price") != "per_call":
        raise ValueError("agreement.price: only 'per_call' is built; a declared batch price needs its own cell")
    return Settings(Fraction(need(owner, "lambda_usd")), tuple(Fraction(p) for p in need(owner, "penalties")), grid,
                    need(owner, "split_seed"), need(owner, "sampling_seed"), tuple(need(owner, "confidence.cuts")),
                    need(owner, "agreement.samples"), need(owner, "fit.min_count"), need(owner, "fit.folds"))


def instruments(owner, dry_run: bool, transport=None) -> dict[str, Instrument]:
    out = {}
    for role in ROLES:
        model = need(owner, f"instruments.{role}.model")
        if dry_run and model not in DRY_RUN_MODELS:
            raise NotADryRunModel(f"instruments.{role}.model = {model!r}: a dry run may call only {DRY_RUN_MODELS}")
        out[role] = from_owner(owner, role, transport)
    return out


def per_question_usd(inst, s: Settings) -> Decimal:
    "Declared dollars for one question: read, confidence and samples; the second opinion; two grades."
    return (2 + s.samples) * inst["primary"].usd_per_call + inst["second"].usd_per_call \
        + 2 * inst["grader"].usd_per_call


def plan(budget: Decimal, inst, s: Settings, n_domains: int, domain_size: int) -> tuple[int, int]:
    "(questions per domain, of which calibration): as many as the budget allows at declared prices, half and half."
    per_domain = min(int(budget / (per_question_usd(inst, s) * n_domains)), domain_size)
    return per_domain, per_domain // 2


def record(q: QS.Question, split: str, tier: int, seen: OBS.Seen, cuts) -> dict:
    return {"question_id": q.id, "split": split, "domain": q.domain, "tier": tier, "read": seen.read,
            "confidence": seen.confidence, "b": OBS.bucket_of(seen.confidence, cuts), "samples": list(seen.samples),
            "second": seen.second, "k": seen.k, "s": seen.s, "calls": [c.to_json() for c in seen.calls]}


def spent(run_dir: Path) -> list[Call]:
    return [Call.from_json(c) for r in read_rows(run_dir / "records.jsonl") for c in r["calls"]] + \
        grading_calls(run_dir / "grades.jsonl")


@dataclass
class Outcome:
    settings: Settings
    rows: list
    fitted: dict
    held_out: dict
    lines: dict            # (p, c) -> {contestant: Line}
    model: dict            # (p, c) -> {"wald_expected": float, "exact": float}
    calls: list
    instruments: dict
    budget: Decimal
    per_domain: tuple


def run(owner, run_dir: Path, budget: Decimal, dry_run: bool, transport=None, questions=None,
        write_packs: bool = True) -> Outcome:
    s = settings(owner)
    inst = instruments(owner, dry_run, transport)
    run_dir.mkdir(parents=True, exist_ok=True)
    qs = questions if questions is not None else QS.load()
    doms = QS.domains(qs)
    per_domain, cal_per_domain = plan(budget, inst, s, len(doms), min(sum(q.domain == d for q in qs) for d in doms))
    if cal_per_domain < 1:
        raise BudgetExceeded(f"${budget} does not buy two questions per domain at ${per_question_usd(inst, s)} each")
    cal, test = QS.split(QS.draw(qs, per_domain, s.sampling_seed), cal_per_domain, s.split_seed)
    print(f"plan: {per_domain} questions per domain ({len(cal)} calibration, {len(test)} test) at <= "
          f"${per_question_usd(inst, s)} declared each; budget ${budget}")

    wallet = Budget(budget, run_dir / "reserved.jsonl")
    tier = lambda q: OBS.domain_index(q, doms)
    items = [("calibration", q) for q in cal] + [("test", q) for q in test]
    append_new(items, lambda it: it[1].id,
               lambda it: record(it[1], it[0], tier(it[1]),
                                 OBS.observe(inst["primary"], inst["second"], it[1], tier(it[1]), s.samples,
                                             wallet.reserve), s.cuts),
               run_dir / "records.jsonl")
    grader = Grader(inst["grader"], run_dir / "grades.jsonl", tier, wallet.reserve)
    by_id = {q.id: q for q in qs}
    rows = []
    for r in read_rows(run_dir / "records.jsonl"):
        q = by_id[r["question_id"]]
        g1, g2 = grader(q, r["read"]), grader(q, r["second"])
        rows.append(r | {"grade1": g1, "grade2": g2, "g1": FIT.grade_class(g1), "g2": FIT.grade_class(g2)})

    cal_rows = [r for r in rows if r["split"] == "calibration"]
    test_rows = [r for r in rows if r["split"] == "test"]
    f = FIT.fit(cal_rows, s.buckets, s.min_count)
    score = FIT.held_out(cal_rows, s.buckets, s.min_count, s.folds, s.split_seed)
    doc = FIT.document(f, score, {"calibration_n": len(cal_rows), "buckets": list(s.buckets),
                                   "cuts": list(s.cuts), "min_count": s.min_count})
    doc_bytes = (json.dumps(doc, indent=1) + "\n").encode()
    (run_dir / "fitted.json").write_bytes(doc_bytes)
    f = FIT.from_document(json.loads(doc_bytes))

    agreement = Fraction(inst["primary"].usd_per_call) * s.samples * s.lambda_usd
    lines, model = {}, {}
    for p in s.penalties:
        for c in s.grid:
            pr = Prices(p, agreement, c)
            out = run_dir / "packs" / f"p{p}_c{'none' if c is None else str(c).replace('/', '_')}"
            bd = Board(f, s.buckets, pr, provenance(doc_bytes), "elicited" if dry_run else "data",
                       out if write_packs else None)
            lines[(p, c)] = B.play_all(test_rows, cal_rows, f, bd)
            model[(p, c)] = {"wald_expected": sum(float(bd.expected(r["b"])) for r in test_rows) / len(test_rows),
                             "exact": sum(float(bd.models[r["b"]].exact(pr)) for r in test_rows) / len(test_rows)}
    return Outcome(s, rows, f, score, lines, model, spent(run_dir), inst, budget, (per_domain, cal_per_domain))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help=f"use dryrun.toml's proposals; only {', '.join(DRY_RUN_MODELS)} may be called")
    p.add_argument("--budget-usd", type=Decimal, required=True)
    p.add_argument("--run-dir", type=Path)
    a = p.parse_args(argv)
    owner = load(DRY_RUN if a.dry_run else OWNER)
    run_dir = a.run_dir or HERE / "runs" / ("dry-run" if a.dry_run else "run")
    from showcases.omniscience import scoreboard
    outcome = run(owner, run_dir, a.budget_usd, a.dry_run)
    path = HERE / "SCOREBOARD.md"
    path.write_text(scoreboard.render(outcome, dry_run=a.dry_run, run_dir=run_dir.relative_to(HERE.parent.parent)
                                      if run_dir.is_relative_to(HERE.parent.parent) else run_dir))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
