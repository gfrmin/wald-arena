"""The AA-Omniscience pipeline, end to end: draw, observe, grade, play the calibration plate, ship its Counts, play a
test plate per (p, c), score.

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
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import wald

from arena import kit

from arena.config import load, need
from arena.spend import append_new, read_rows
from arena.transports import Call, Instrument, from_owner
from showcases.omniscience import board as B
from showcases.omniscience import observe as OBS
from showcases.omniscience import questions as QS
from showcases.omniscience.grader import Grader
from showcases.omniscience import world as W
from showcases.omniscience.grader import calls as grading_calls

HERE = Path(__file__).resolve().parent
OWNER = HERE / "owner.toml"
DRY_RUN = HERE / "dryrun.toml"
DRY_RUN_MODELS = ("claude-haiku-4-5-20251001",)
ROLES = ("primary", "second", "grader")


class BudgetExceeded(RuntimeError):
    pass


class NotADryRunModel(RuntimeError):
    pass


class ReplayCalled(RuntimeError):
    pass


def replay_only(model):
    "A transport for --replay: every answer and grade must come from the run directory, so any call is refused."
    def send(system, user):
        raise ReplayCalled(f"--replay: {model} would have been called; the run directory does not hold this answer")
    return send


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
    grid: tuple[Fraction, ...]
    split_seed: int
    sampling_seed: int
    plate_seed: int
    cuts: tuple[int, ...]
    samples: int
    grids: W.Grids
    calibration_p: Fraction
    calibration_c: Fraction

    @property
    def buckets(self):
        return OBS.bucket_names(self.cuts)


def fractions(xs) -> tuple:
    return tuple(tuple(Fraction(v) for v in x) if isinstance(x, list) else Fraction(x) for x in xs)


def settings(owner) -> Settings:
    grid = need(owner, "second_price_grid")
    if "none" in grid:
        raise ValueError("second_price_grid: 'none' cannot condition on calibration Counts that use the second "
                         "opinion (QUESTIONS.md 2.22)")
    if need(owner, "agreement.price") != "per_call":
        raise ValueError("agreement.price: only 'per_call' is built; a declared batch price needs its own cell")
    grids = W.Grids(fractions(need(owner, "globals.rho")), fractions(need(owner, "globals.agree")),
                    fractions(need(owner, "globals.second")), fractions(need(owner, "globals.grader")))
    return Settings(Fraction(need(owner, "lambda_usd")), fractions(need(owner, "penalties")), fractions(grid),
                    need(owner, "split_seed"), need(owner, "sampling_seed"), need(owner, "plate_seed"),
                    tuple(need(owner, "confidence.cuts")), need(owner, "agreement.samples"), grids,
                    Fraction(need(owner, "calibration_plate.p")), Fraction(need(owner, "calibration_plate.c")))


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


def prices(inst, s: Settings, p: Fraction, c: Fraction) -> W.Prices:
    "Each act's declared dollars × λ_usd, in utility (brief 002, revision 2)."
    usd = lambda role: Fraction(inst[role].usd_per_call) * s.lambda_usd
    return W.Prices(p, usd("primary") * s.samples, c, usd("grader"))


def plate_order(rows, seed: int) -> list:
    "The order questions enter a plate (QUESTIONS.md 2.20): seeded, the same for every (p, c)."
    out = sorted(rows, key=lambda r: r["question_id"])
    random.Random(seed).shuffle(out)
    return out


@dataclass
class Calibration:
    "The calibration split's plate, and the Counts every test pack ships."
    pack: str
    counts: Counter
    digest: str
    score: Fraction
    acts: Counter                    # the calibration plate's act sequences, as a check on what it bought
    before: dict                     # P(Global) marginals, declared (display)
    after: dict                      # P(Global | calibration Counts) marginals (display)


@dataclass
class PlateOut:
    p: Fraction
    c: Fraction
    plays: list                      # Played per test row, in plate order
    fresh: list                      # the same rows from the declared prior, Counts never conditioned on
    realised: Fraction               # mean of answer utility less every price paid, the After-act's included
    realised_fresh: Fraction
    e7: dict                         # {(history, act, end): total variation}
    n_by_line: dict                  # {(history, act, end): draws the line groups}
    disclosure: str
    first: tuple                     # the first test question's acts, with the shipped Counts and without
    differ: int                      # test questions whose acts differ with the Counts and without
    counts_n: int                    # records in the plate's Counts at its end
    seconds: float


def calibrate(s: Settings, inst, cal_rows, out: Path | None) -> Calibration:
    pr = prices(inst, s, s.calibration_p, s.calibration_c)
    pr = W.Prices(pr.p, Fraction(0), s.calibration_c, pr.grade)        # every observation priced 0 (2.21)
    pack = W.text(s.buckets, s.grids, pr, "omniscience-calibration")
    spec, world = W.declare(pack)
    plate, plays = B.play_plate(world, plate_order(cal_rows, s.plate_seed), s.samples)
    counts = plate.counts()
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "calibration.py").write_text(pack)
    return Calibration(pack, counts, kit.digest(counts), kit.score(spec, counts),
                       Counter(tuple(res.acts) for _, res in plays), kit.marginals(spec, Counter()),
                       kit.marginals(spec, counts))


def realised(rows, plays, results, p, c) -> Fraction:
    "Answer utility less every price paid, the After-act's included, and c for a blind switch, which the door buys."
    return sum((B.answer_utility(r, pl, p) - res.paid - c * pl.blind for r, pl, res in zip(rows, plays, results)),
               Fraction(0)) / len(rows)


def test_plate(args) -> PlateOut:
    "One test plate: a module-level function, so plates run in parallel processes."
    s, inst_prices, p, c, test_rows, cal_counts, out = args
    t0 = time.time()
    pr = W.Prices(p, inst_prices.agreement, c, inst_prices.grade)
    name = f"omniscience-p{W.num(p).replace('/', '_')}-c{W.num(c).replace('/', '_')}"
    pack = W.text(s.buckets, s.grids, pr, name, cal_counts)
    spec, world = W.declare(pack)
    bare_spec, bare = W.declare(W.text(s.buckets, s.grids, pr, name + "-no-counts"))
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{name}.py").write_text(pack)
    plate, played = B.play_plate(world, test_rows, s.samples)
    _, fresh = B.play_plate(bare, test_rows, s.samples, fresh=True)
    plays, results = [x[0] for x in played], [x[1] for x in played]
    fplays, fresults = [x[0] for x in fresh], [x[1] for x in fresh]
    first = wald.plate(bare).run(B.RecordedDoor(test_rows[0], s.samples)).acts
    return PlateOut(p, c, plays, fplays, realised(test_rows, plays, results, p, c),
                    realised(test_rows, fplays, fresults, p, c), kit.e7(spec, plate.counts()),
                    dict(kit.e7_sizes(plate.counts())),
                    str(plate.disclosure()), (results[0].acts, first),
                    sum(a.acts != b.acts for a, b in zip(results, fresults)), sum(plate.counts().values()),
                    time.time() - t0)


@dataclass
class Outcome:
    settings: Settings
    rows: list
    test_rows: list                  # in plate order
    calibration: Calibration
    plates: dict                     # (p, c) -> PlateOut
    lines: dict                      # (p, c) -> {contestant: Line}
    calls: list
    instruments: dict
    budget: Decimal
    per_domain: tuple


def run(owner, run_dir: Path, budget: Decimal, dry_run: bool, transport=None, questions=None,
        write_packs: bool = True, workers: int | None = None) -> Outcome:
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
          f"${per_question_usd(inst, s)} declared each; budget ${budget}", flush=True)

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
        rows.append(r | {"b": OBS.bucket_of(r["confidence"], s.cuts), "grade1": g1, "grade2": g2,
                         "g1": B.grade_class(g1), "g2": B.grade_class(g2)})

    cal_rows = [r for r in rows if r["split"] == "calibration"]
    test_rows = plate_order([r for r in rows if r["split"] == "test"], s.plate_seed)
    packs = run_dir / "packs" if write_packs else None
    t0 = time.time()
    calib = calibrate(s, inst, cal_rows, packs)
    print(f"calibration plate: {sum(calib.counts.values())} records, {len(calib.counts)} distinct, "
          f"{time.time() - t0:.0f}s", flush=True)
    (run_dir / "calibration_counts.json").write_text(json.dumps(
        {"records": [[[list(d) for d in draws], end, after, n] for (draws, end, after), n in
                     sorted(calib.counts.items(), key=repr)],
         "sha256": calib.digest, "score": W.num(calib.score)}, indent=1) + "\n")

    base = prices(inst, s, Fraction(1), Fraction(0))
    jobs = [(s, base, p, c, test_rows, calib.counts, packs) for p in s.penalties for c in s.grid]
    if workers == 1 or len(jobs) == 1:
        outs = [test_plate(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers or min(len(jobs), os.cpu_count() or 1)) as ex:
            outs = list(ex.map(test_plate, jobs))
    plates = {(o.p, o.c): o for o in outs}
    for o in outs:
        print(f"plate p={o.p} c={o.c}: {o.seconds:.0f}s", flush=True)
    (run_dir / "e7.json").write_text(json.dumps(
        {f"p={W.num(o.p)} c={W.num(o.c)}": [{"history": [list(d) for d in h], "draw": act, "end": end,
                                             "n": o.n_by_line.get((h, act, end)), "total_variation": W.num(tv)}
                                            for (h, act, end), tv in sorted(o.e7.items(), key=repr)]
         for o in outs}, indent=1) + "\n")

    lines = {}
    for (p, c), po in plates.items():
        plays = B.baselines(test_rows, cal_rows, s.buckets, p) | {"wald": po.plays}
        lines[(p, c)] = {name: B.line(name, test_rows, plays[name], p, base.agreement, c) for name in B.CONTESTANTS}
    return Outcome(s, rows, test_rows, calib, plates, lines, spent(run_dir), inst, budget, (per_domain, cal_per_domain))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help=f"use dryrun.toml's proposals; only {', '.join(DRY_RUN_MODELS)} may be called")
    p.add_argument("--budget-usd", type=Decimal, required=True)
    p.add_argument("--run-dir", type=Path)
    p.add_argument("--replay", action="store_true",
                   help="play from the answers and grades already recorded in the run directory; refuse any call")
    p.add_argument("--workers", type=int, help="test plates played in parallel (default: one per plate, up to the CPUs)")
    a = p.parse_args(argv)
    owner = load(DRY_RUN if a.dry_run else OWNER)
    run_dir = a.run_dir or HERE / "runs" / ("dry-run" if a.dry_run else "run")
    from showcases.omniscience import scoreboard
    outcome = run(owner, run_dir, a.budget_usd, a.dry_run, transport=replay_only if a.replay else None,
                  workers=a.workers)
    path = HERE / "SCOREBOARD.md"
    path.write_text(scoreboard.render(outcome, dry_run=a.dry_run, run_dir=run_dir.relative_to(HERE.parent.parent)
                                      if run_dir.is_relative_to(HERE.parent.parent) else run_dir))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
