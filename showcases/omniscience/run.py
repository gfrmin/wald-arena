"""The AA-Omniscience pipeline, end to end: draw, observe, grade, gate, ship the calibration Counts, play a test plate
per (p, c), score.

    python -m showcases.omniscience.run --dry-run --budget-usd 3          # the stand-ins of dryrun.toml
    python -m showcases.omniscience.run --stage pilot-calibration         # the real run, stage by stage

A dry run's numbers come from `dryrun.toml` (or --dry-run-file), its models from DRY_RUN_MODELS only, and its size
from the budget at declared prices. The real run's numbers come from `owner.toml`, ruled in full; it goes by stage
(QUESTIONS.md 2.14 as ruled 2026-09-28): `pilot-calibration` observes and grades the pilot's calibration questions,
prints the measured cost and the projection, prints the gate, and stops; `pilot-test` and `stage2` each need the
owner's go in `owner.toml`. No instrument is built while its `listed` is empty.

Spend is reserved before each call and settled after it (`Budget`), against the whole run's cap and the stage's.
Records are appended one question at a time, so an interrupted run resumes; the calls of a question cut off mid-way
are made again, and the wallet remembers what they cost.
"""
import argparse
import json
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import wald


from arena.config import load, need, optional
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
# Stand-ins a dry run may call. None is a frozen model of brief 002 (gpt-6-astra, gpt-5.5, claude-opus-5-5).
DRY_RUN_MODELS = ("claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-sonnet-4-6")
ROLES = ("primary", "second", "grader")


class BudgetExceeded(RuntimeError):
    pass


class NotADryRunModel(RuntimeError):
    pass


class ReplayCalled(RuntimeError):
    pass


class NotListed(RuntimeError):
    pass


def replay_only(model):
    "A transport for --replay: every answer and grade must come from the run directory, so any call is refused."
    def send(system, user):
        raise ReplayCalled(f"--replay: {model} would have been called; the run directory does not hold this answer")
    return send


class Budget:
    """The wallet. Before each call it reserves an upper bound on what the call costs, and writes it to `log`: the
    declared price, or for an instrument priced `measured`, the most one of its calls has cost so far (at first, list
    price for 4,000 tokens in and 4,000 out). After the call the reservation is settled at what the call cost, list
    price from its tokens. Spend is the settled costs plus any reservation never settled (a call cut off), so a run
    cut off mid-question resumes knowing what it paid. It stops before a call that could take the whole run's spend
    past `limit`, or this stage's past `stage_limit` (QUESTIONS.md 2.14 as ruled 2026-09-28)."""

    def __init__(self, limit: Decimal, log: Path | None = None, stage: str = "", stage_limit: Decimal | None = None):
        self.limit, self.log, self.stage, self.stage_limit = limit, log, stage, stage_limit
        self.rows = read_rows(log) if log else []
        self.open: dict[str, int] = {}

    def _costs(self) -> list[tuple[dict, Decimal]]:
        "Each reservation, with what it cost: its settlement, or its bound if never settled."
        settled = {r["settle"]: Decimal(r["usd"]) for r in self.rows if "settle" in r}
        return [(r, settled.get(i, Decimal(r["usd"]))) for i, r in enumerate(self.rows) if "settle" not in r]

    def _spent(self, stage: str | None = None) -> Decimal:
        return sum((c for r, c in self._costs() if stage is None or r.get("stage", "") == stage), Decimal(0))

    @property
    def spent(self) -> Decimal:
        return self._spent()

    def bound(self, instrument: Instrument) -> Decimal:
        if instrument.usd_per_call is not None:
            return instrument.usd_per_call
        seen = [Decimal(r["usd"]) for r in self.rows
                if "settle" in r and self.rows[r["settle"]]["instrument"] == instrument.name]
        return max(seen) if seen else instrument.list_usd(4000, 4000)

    def _write(self, row: dict):
        self.rows.append(row)
        if self.log:
            with open(self.log, "a") as f:
                f.write(json.dumps(row) + "\n")

    def reserve(self, instrument: Instrument):
        b = self.bound(instrument)
        if self.spent + b > self.limit:
            raise BudgetExceeded(f"the next {instrument.name} call (up to ${b}) could take the run's spend past "
                                 f"${self.limit} (spent ${self.spent})")
        if self.stage_limit is not None and self._spent(self.stage) + b > self.stage_limit:
            raise BudgetExceeded(f"the next {instrument.name} call (up to ${b}) could take stage {self.stage}'s spend "
                                 f"past ${self.stage_limit} (spent ${self._spent(self.stage)})")
        self.open[instrument.name] = len(self.rows)
        self._write({"instrument": instrument.name, "usd": str(b), "stage": self.stage})

    def settle(self, instrument_name: str, call: Call):
        "What a measured call cost, list price from its tokens; a declared price was reserved exactly."
        i = self.open.pop(instrument_name, None)
        if i is not None and Decimal(self.rows[i]["usd"]) != call.usd:
            self._write({"settle": i, "usd": str(call.usd)})


class ModelChanged(RuntimeError):
    pass


class ServedModels:
    """The model each instrument's provider says served each call (2.3), from every call already recorded. The run
    stops if an instrument is served a model other than the one it was served before."""

    def __init__(self, calls=()):
        self.seen: dict[str, str] = {}
        for c in calls:
            self(c)

    def __call__(self, c: Call):
        if not c.served_model:
            return
        base = c.instrument.split(".")[0]
        first = self.seen.setdefault(base, c.served_model)
        if c.served_model != first:
            raise ModelChanged(f"{base} was served {c.served_model!r} on question {c.question_id}, after {first!r}: "
                               "the instrument changed mid-run, so the run stops")


@dataclass(frozen=True)
class Settings:
    lambda_usd: Fraction
    penalties: tuple[Fraction, ...]
    grid: tuple[Fraction, ...]
    split_seed: int
    sampling_seed: int
    plate_seed: int
    cuts: tuple[int, ...]
    unread: str
    samples: int
    grids: W.Grids
    gate: str = "stands"             # "waived" only for the Haiku dry run (owner, 2026-09-27); never for the real run
    list_prices: dict = field(default_factory=dict)   # model -> (input, output) $ per million tokens, for the audit

    @property
    def buckets(self):
        return OBS.bucket_names(self.cuts, self.unread)


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
                    fractions(need(owner, "globals.second")), fractions(need(owner, "globals.grader")),
                    fractions(optional(owner, "globals.corr", [])))   # absent: the World has no κ (the dry runs)
    return Settings(Fraction(need(owner, "lambda_usd")), fractions(need(owner, "penalties")), fractions(grid),
                    need(owner, "split_seed"), need(owner, "sampling_seed"), need(owner, "plate_seed"),
                    tuple(need(owner, "confidence.cuts")), need(owner, "confidence.unread"),
                    need(owner, "agreement.samples"), grids, gate_ruling(optional(owner, "confidence.gate", "stands")),
                    {m: (Decimal(v["input"]), Decimal(v["output"]))
                     for m, v in optional(owner, "list_price_per_mtok", {}).items()})


def gate_ruling(value: str) -> str:
    if value not in ("stands", "waived"):
        raise ValueError(f"confidence.gate = {value!r}: 'stands' or 'waived'")
    return value


def instruments(owner, dry_run: bool, transport=None) -> dict[str, Instrument]:
    out = {}
    roles = ROLES + (("equivalence",) if "equivalence" in owner.get("instruments", {}) else ())
    for role in roles:
        model = need(owner, f"instruments.{role}.model")
        if dry_run and model not in DRY_RUN_MODELS:
            raise NotADryRunModel(f"instruments.{role}.model = {model!r}: a dry run may call only {DRY_RUN_MODELS}")
        if not dry_run and not str(optional(owner, f"instruments.{role}.listed", "")).strip():
            raise NotListed(f"instruments.{role}.listed is empty: {model!r} is verified against its provider's list "
                            "on the day, and pinned with the date, before any call (ruled 2026-09-28)")
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


def record(q: QS.Question, split: str, tier: int, seen: OBS.Seen, bucketing) -> dict:
    "bucketing: (cuts, unread). The bucket is recomputed from the confidence whenever a run reads the record."
    return {"question_id": q.id, "split": split, "domain": q.domain, "tier": tier, "read": seen.read,
            "confidence": seen.confidence, "b": OBS.bucket_of(seen.confidence, *bucketing), "samples": list(seen.samples),
            "second": seen.second, "k": seen.k, "s": seen.s, "calls": [c.to_json() for c in seen.calls]} | (
        {"classes": list(seen.classes) if seen.classes else None}
        if any(c.instrument == "equivalence" for c in seen.calls) else {})


STAGES = ("pilot-calibration", "pilot-test", "stage2")


class NoGo(RuntimeError):
    pass


def pilot(cal, test, n_cal: int, n_test: int, seed: int) -> tuple[list, list]:
    """The pilot (2.14 as ruled 2026-09-28): n_cal calibration and n_test test questions from 2.1's split, 8 or 9 per
    domain, the domains that take one more chosen by the seed; each domain's first questions in the split's order."""
    rng = random.Random(f"pilot:{seed}")

    def take(qs, n):
        doms = QS.domains(qs)
        base, extra = divmod(n, len(doms))
        more = set(rng.sample(doms, extra))
        return [q for d in doms for q in [x for x in qs if x.domain == d][:base + (d in more)]]
    return take(cal, n_cal), take(test, n_test)


@dataclass
class Estimate:
    "Measured list-price dollars per question on the pilot's calibration split, projected (2.14)."
    n: int
    per_question: dict              # instrument -> mean $ per question
    reasoning: dict                 # instrument -> mean reasoning tokens per call
    projected: dict                 # "pilot test", "stage 2", "whole run" -> $
    spent: Decimal


def estimate(rows, calls_by_q, spent: Decimal, n_pilot_test: int, n_stage2: int) -> Estimate:
    per_q, reasoning = Counter(), {}
    n = len(rows)
    by_inst = {}
    for r in rows:
        for c in calls_by_q[r["question_id"]]:
            base = c.instrument.split(".")[0]
            per_q[base] += c.usd
            by_inst.setdefault(base, []).append(c)
    per_question = {k: v / n for k, v in per_q.items()}
    reasoning = {k: sum(c.reasoning_tokens for c in v) / len(v) for k, v in by_inst.items()}
    each = sum(per_question.values(), Decimal(0))
    return Estimate(n, per_question, reasoning,
                    {"pilot test": each * n_pilot_test, "stage 2": each * n_stage2,
                     "whole run": spent + each * (n_pilot_test + n_stage2)}, spent)


def spent(run_dir: Path) -> list[Call]:
    return [Call.from_json(c) for r in read_rows(run_dir / "records.jsonl") for c in r["calls"]] + \
        grading_calls(run_dir / "grades.jsonl")


def per_call_usd(inst, cal_rows, grade_calls) -> dict[str, Decimal]:
    """Each instrument's declared price per call: its owner-declared price, or for one priced `measured`, the mean
    list-price dollars of its calls on the calibration split (2.12, as for Millionaire)."""
    cal = {r["question_id"] for r in cal_rows}
    seen = {}
    for c in [Call.from_json(c) for r in cal_rows for c in r["calls"]] + [g for g in grade_calls if g.question_id in cal]:
        seen.setdefault(c.instrument, []).append(c.usd)
    mean = lambda k: sum(seen[k], Decimal(0)) / len(seen[k])
    fixed = lambda role, key: inst[role].usd_per_call if inst[role].usd_per_call is not None else mean(key)
    out = {"sample": fixed("primary", "primary.sample"), "grader": fixed("grader", "grader")}
    if "equivalence" in inst:
        out["equivalence"] = fixed("equivalence", "equivalence")
    return out


def prices(per_call: dict, s: Settings, p: Fraction, c: Fraction) -> W.Prices:
    """Each act's declared dollars × λ_usd, in utility (brief 002, revision 2). The agreement act costs its samples
    and, where one is made, the equivalence call that reads them (proposed 2026-09-28)."""
    usd = lambda k: Fraction(per_call[k]) * s.lambda_usd
    agreement = usd("sample") * s.samples + (usd("equivalence") if "equivalence" in per_call else 0)
    return W.Prices(p, agreement, c, usd("grader"))


def plate_order(rows, seed: int) -> list:
    "The order questions enter a plate (QUESTIONS.md 2.20): seeded, the same for every (p, c)."
    out = sorted(rows, key=lambda r: r["question_id"])
    random.Random(seed).shuffle(out)
    return out


class BucketGate(RuntimeError):
    "A confidence bucket holds under a fifth of the calibration records: the owner rules again (2.15)."


GATE = Fraction(1, 5)


def histogram(cal_rows) -> list[tuple[str, int]]:
    "The calibration split's stated confidences, by tens, and the unreadable ones."
    bins = Counter("unread" if r["confidence"] is None else f"{min(r['confidence'] // 10, 9) * 10}-"
                   f"{min(r['confidence'] // 10, 9) * 10 + (10 if r['confidence'] >= 90 else 9)}" for r in cal_rows)
    order = [f"{d}-{d + (10 if d == 90 else 9)}" for d in range(0, 100, 10)] + ["unread"]
    return [(k, bins[k]) for k in order]


def bucket_shares(cal_rows, buckets) -> dict[str, Fraction]:
    n = Counter(r["b"] for r in cal_rows)
    return {b: Fraction(n[b], len(cal_rows)) for b in buckets}


def bucket_gate(cal_rows, s: Settings, dry_run: bool) -> tuple[dict[str, Fraction], dict[str, Fraction]]:
    """Before any test question is played: print the calibration histogram and each bucket's share, and stop if a
    bucket holds under a fifth of the calibration records (the owner's ruling on 2.15). Calibration data only.
    The owner waived the stop for the Haiku dry run alone (2026-09-27): there the thin buckets are printed, returned
    and reported, and the run goes on. Returns (shares, the buckets under a fifth)."""
    shares = bucket_shares(cal_rows, s.buckets)
    print("calibration confidences: " + ", ".join(f"{k} {n}" for k, n in histogram(cal_rows)), flush=True)
    print("bucket shares: " + ", ".join(f"{b} {n.numerator}/{n.denominator} ({float(n):.1%})"
                                        for b, n in shares.items()), flush=True)
    thin = {b: n for b, n in shares.items() if n < GATE}
    say = (f"under a fifth of the {len(cal_rows)} calibration records: "
           + ", ".join(f"{b} {float(n):.1%}" for b, n in thin.items()) + f" (cuts {list(s.cuts)}, unread -> {s.unread})")
    if thin and s.gate == "waived":
        print(f"GATE WAIVED for this dry run (owner, 2026-09-27): {say}", flush=True)
    elif thin:
        raise BucketGate(say + "; the owner rules again (2.15)")
    return shares, thin


def calibration_end(row, index_among_different: int) -> str:
    """The end a constructed calibration record takes (the owner's ruling on 2.21: chosen for what its grade teaches).
    It reads only what the record shows, never a grade, so the design stays ignorable (C2 §4): when the two answers
    match, one grade teaches both, so the read is submitted; when they differ, the records alternate in question
    order between grading the read and grading the second opinion, so both reliabilities are taught."""
    if row["s"] == "same":
        return "answer_primary"
    return "answer_primary" if index_among_different % 2 == 0 else "answer_second"


def construct(cal_rows, samples: int) -> Counter:
    """The calibration Counts, one record per question with every instrument drawn: the bucket, the agreement samples,
    the second opinion, then the chosen end and its grade."""
    counts, i = Counter(), 0
    for r in sorted(cal_rows, key=lambda r: r["question_id"]):
        end = calibration_end(r, i)
        i += r["s"] == "different"
        door = B.RecordedDoor(r, samples)
        draws = tuple((act, door.outcome(act)) for act in ("confidence", "agreement", "second_opinion"))
        door.fire(end)
        counts[(draws, end, door.outcome(W.AFTER))] += 1
    return counts


@dataclass
class Calibration:
    "The constructed calibration Counts every test pack ships."
    counts: Counter
    digest: str
    score: str                       # as wald.score writes it, "p/q" in however many digits: text, never a number
    ends: Counter                    # records by end
    shares: dict                     # each bucket's share of the calibration records
    thin: dict                       # buckets under a fifth: non-empty only where the owner waived the gate
    histogram: list                  # the calibration confidences by tens


def calibrate(s: Settings, per_call, cal_rows, shares, thin=None) -> Calibration:
    """The constructed Counts, their digest and their Score, by wald's own `digest` and `score`. Declaring a pack that
    ships them is the check that this declaration could have written every record and that together they have
    positive probability under some Global value (S13): wald refuses the pack `PLATE` otherwise."""
    counts = construct(cal_rows, s.samples)
    pr = prices(per_call, s, Fraction(1), Fraction(0))
    _, bare = W.declare(W.text(s.buckets, s.grids, pr, "omniscience"))
    try:
        W.declare(W.text(s.buckets, s.grids, pr, "omniscience", counts))
    except wald.refusals.Refused as e:
        raise ValueError(f"constructed calibration records this declaration could not have written: {e}") from e
    return Calibration(counts, wald.digest(counts), wald.score(bare, counts),
                       Counter(end for _, end, _ in counts.elements()), shares, thin or {}, histogram(cal_rows))


@dataclass
class PlateOut:
    p: Fraction
    c: Fraction
    plays: list                      # Played per test row, in plate order
    fresh: list                      # the same rows from the declared prior, Counts never conditioned on
    realised: Fraction               # mean of answer utility less every price paid, the After-act's included
    realised_fresh: Fraction
    e7: str                          # wald.e7's lines for the plate's Counts, as wald writes them
    e7_n: dict                       # draws each E7 line groups, keyed as the scoreboard displays a line
    disclosure: str
    first: tuple                     # the first test question's acts, with the shipped Counts and without
    differ: int                      # test questions whose acts differ with the Counts and without
    counts_n: int                    # records in the plate's Counts at its end
    seconds: float


def draws_per_line(counts: Counter) -> dict:
    """How many draws each of E7's lines groups: (history, draw, end) as the scoreboard shows a line, the history
    "a=o → ..." or "(start)", and the end only on the After-act's line. Counting records is counting facts (S1)."""
    n = Counter()
    for (draws, end, after), k in counts.items():
        shown = lambda h: " → ".join(f"{a}={o}" for a, o in h) or "(start)"
        for j, (act, _) in enumerate(draws):
            n[(shown(draws[:j]), act, "")] += k
        if after is not None:
            n[(shown(draws), W.AFTER, end)] += k
    return dict(n)


def realised(rows, plays, results, p, c) -> Fraction:
    """What wald's episodes actually cost: answer utility less every price paid, the After-act's included, and c for a
    blind switch, whose second opinion the door buys. The World's −c on `answer_second` is not taken again here: the
    second opinion is bought once whichever way it came (2.19)."""
    return sum((B.answer_utility(r, pl, p) - res.paid - c * pl.blind for r, pl, res in zip(rows, plays, results)),
               Fraction(0)) / len(rows)


def test_plate(args) -> PlateOut:
    "One test plate: a module-level function, so plates run in parallel processes."
    s, inst_prices, p, c, test_rows, cal_counts, out = args
    t0 = time.time()
    pr = W.Prices(p, inst_prices.agreement, c, inst_prices.grade)
    name = f"omniscience-p{W.num(p).replace('/', '_')}-c{W.num(c).replace('/', '_')}"
    pack = W.text(s.buckets, s.grids, pr, name, cal_counts)
    _, world = W.declare(pack)
    _, bare = W.declare(W.text(s.buckets, s.grids, pr, name + "-no-counts"))
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{name}.py").write_text(pack)
    plate, played = B.play_plate(world, test_rows, s.samples)
    _, fresh = B.play_plate(bare, test_rows, s.samples, fresh=True)
    plays, results = [x[0] for x in played], [x[1] for x in played]
    fplays, fresults = [x[0] for x in fresh], [x[1] for x in fresh]
    first = wald.plate(bare).run(B.RecordedDoor(test_rows[0], s.samples)).acts
    return PlateOut(p, c, plays, fplays, realised(test_rows, plays, results, p, c),
                    realised(test_rows, fplays, fresults, p, c), str(wald.e7(world, plate.counts())),
                    draws_per_line(plate.counts()),
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
    per_call: dict = field(default_factory=dict)      # each instrument's declared $ per call, as the packs price it
    stage: str | None = None
    audit: tuple | None = None       # (grades the owner has audited, of how many, agreeing with the grader); stage 2


AUDIT_FIELDS = ("question_id", "domain", "question", "gold_answer", "answer", "grader_grade", "owner_grade")


def audit(run_dir: Path, test_rows, by_id, per_domain: int, seed: int) -> tuple[int, int, int]:
    """2.9 as ruled: the owner hand-audits `per_domain` grades per domain, drawn with the seed from the test split's
    graded answers (the read's and the second opinion's), before the verdict line is written. The sample is written
    once, to `audit.csv`, with an empty `owner_grade` column for the owner to fill (A, B, C or D, as the grader).
    Returns (filled, drawn, agreeing)."""
    import csv
    path = run_dir / "audit.csv"
    if not path.exists():
        rng = random.Random(f"audit:{seed}")
        graded = sorted({(r["question_id"], a, g) for r in test_rows
                         for a, g in ((r["read"], r["grade1"]), (r["second"], r["grade2"]))})
        rows = []
        for d in sorted({r["domain"] for r in test_rows}):
            pool = [x for x in graded if by_id[x[0]].domain == d]
            rows += rng.sample(pool, min(per_domain, len(pool)))
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(AUDIT_FIELDS)
            for qid, answer, grade in rows:
                q = by_id[qid]
                w.writerow([qid, q.domain, q.text, q.answer, answer, grade, ""])
    with open(path, newline="") as f:
        got = list(csv.DictReader(f))
    letter = {"CORRECT": "A", "INCORRECT": "B", "PARTIAL_ANSWER": "C", "NOT_ATTEMPTED": "D"}
    filled = [r for r in got if r["owner_grade"].strip()]
    return len(filled), len(got), sum(r["owner_grade"].strip().upper() == letter.get(r["grader_grade"], "?")
                                      for r in filled)


def run(owner, run_dir: Path, budget: Decimal | None, dry_run: bool, transport=None, questions=None,
        write_packs: bool = True, workers: int | None = None, stage: str | None = None):
    """A dry run (`dry_run`, sized by `budget`), or a stage of the real run (`stage`, sized and capped by the owner's
    numbers). `pilot-calibration` returns an Estimate and plays no test question; the other stages return an Outcome."""
    s = settings(owner)
    if s.gate == "waived" and not dry_run:
        raise ValueError("confidence.gate = 'waived' is the Haiku dry run's alone; the gate stands for the real run")
    if not dry_run and stage not in STAGES:
        raise ValueError(f"the real run goes by stage: one of {', '.join(STAGES)}")
    if stage in ("pilot-test", "stage2") and not str(optional(owner, f"go.{stage.replace('-', '_')}", "")).strip():
        raise NoGo(f"go.{stage.replace('-', '_')} is not set in owner.toml: the owner's go comes first (2.14)")
    inst = instruments(owner, dry_run, transport)
    run_dir.mkdir(parents=True, exist_ok=True)
    qs = questions if questions is not None else QS.load()
    doms = QS.domains(qs)
    if dry_run:
        per_domain, cal_per_domain = plan(budget, inst, s, len(doms), min(sum(q.domain == d for q in qs) for d in doms))
        if cal_per_domain < 1:
            raise BudgetExceeded(f"${budget} does not buy two questions per domain at ${per_question_usd(inst, s)} each")
        cal, test = QS.split(QS.draw(qs, per_domain, s.sampling_seed), cal_per_domain, s.split_seed)
        print(f"plan: {per_domain} questions per domain ({len(cal)} calibration, {len(test)} test) at <= "
              f"${per_question_usd(inst, s)} declared each; budget ${budget}", flush=True)
        wallet = Budget(budget, run_dir / "reserved.jsonl")
    else:
        per_domain, cal_per_domain = need(owner, "split.per_domain"), need(owner, "split.calibration_per_domain")
        cal_all, test_all = QS.split(QS.draw(qs, per_domain, s.sampling_seed), cal_per_domain, s.split_seed)
        pcal, ptest = pilot(cal_all, test_all, need(owner, "stages.pilot_calibration"), need(owner, "stages.pilot_test"),
                            s.split_seed)
        cal, test = {"pilot-calibration": (pcal, []), "pilot-test": (pcal, ptest), "stage2": (cal_all, test_all)}[stage]
        group = "stage2" if stage == "stage2" else "pilot"
        wallet = Budget(Decimal(need(owner, "stages.whole_cap_usd")), run_dir / "reserved.jsonl", group,
                        Decimal(need(owner, "stages.pilot_cap_usd")) if group == "pilot" else None)
        print(f"stage {stage}: {len(cal)} calibration, {len(test)} test questions; spent ${wallet.spent} of the "
              f"${wallet.limit} whole-run cap" + (f", ${wallet._spent('pilot')} of the pilot's ${wallet.stage_limit}"
                                                  if group == "pilot" else ""), flush=True)
    served = ServedModels(spent(run_dir))

    def after(c: Call):
        wallet.settle(c.instrument.split(".")[0], c)
        served(c)

    tier = lambda q: OBS.domain_index(q, doms)
    items = [("calibration", q) for q in cal] + [("test", q) for q in test]
    append_new(items, lambda it: it[1].id,
               lambda it: record(it[1], it[0], tier(it[1]),
                                 OBS.observe(inst["primary"], inst["second"], it[1], tier(it[1]), s.samples,
                                             wallet.reserve, inst.get("equivalence"), after), (s.cuts, s.unread)),
               run_dir / "records.jsonl")
    grader = Grader(inst["grader"], run_dir / "grades.jsonl", tier, wallet.reserve, after)
    by_id = {q.id: q for q in qs}
    wanted = {q.id for q in cal} | {q.id for q in test}
    rows = []
    for r in read_rows(run_dir / "records.jsonl"):
        if r["question_id"] not in wanted:
            continue
        q = by_id[r["question_id"]]
        g1, g2 = grader(q, r["read"]), grader(q, r["second"])
        rows.append(r | {"b": OBS.bucket_of(r["confidence"], s.cuts, s.unread), "grade1": g1, "grade2": g2,
                         "g1": B.grade_class(g1), "g2": B.grade_class(g2)})

    if stage == "pilot-calibration":
        calls_by_q = {}
        for r in rows:
            calls_by_q[r["question_id"]] = [Call.from_json(c) for c in r["calls"]]
        for c in grading_calls(run_dir / "grades.jsonl"):
            calls_by_q.setdefault(c.question_id, []).append(c)
        est = estimate(rows, calls_by_q, wallet.spent, need(owner, "stages.pilot_test"),
                       per_domain * len(doms) - need(owner, "stages.pilot_calibration") - need(owner, "stages.pilot_test"))
        (run_dir / "estimate.json").write_text(json.dumps(
            {"n": est.n, "per_question": {k: str(v) for k, v in est.per_question.items()},
             "reasoning_tokens_per_call": est.reasoning, "projected": {k: str(v) for k, v in est.projected.items()},
             "spent": str(est.spent)}, indent=1) + "\n")
        print(f"measured on {est.n} calibration questions: $ per question " + ", ".join(
            f"{k} {v:.5f}" for k, v in est.per_question.items()) + "; reasoning tokens per call " + ", ".join(
            f"{k} {v:.0f}" for k, v in est.reasoning.items()), flush=True)
        print("projected: " + ", ".join(f"{k} ${v:.2f}" for k, v in est.projected.items()), flush=True)
        bucket_gate(rows, s, dry_run)
        return est

    cal_rows = [r for r in rows if r["split"] == "calibration"]
    test_rows = plate_order([r for r in rows if r["split"] == "test"], s.plate_seed)
    packs = run_dir / "packs" if write_packs else None
    shares, thin = bucket_gate(cal_rows, s, dry_run)
    t0 = time.time()
    per_call = per_call_usd(inst, cal_rows, grading_calls(run_dir / "grades.jsonl"))
    calib = calibrate(s, per_call, cal_rows, shares, thin)
    print(f"calibration Counts: {sum(calib.counts.values())} records, {len(calib.counts)} distinct, "
          f"Score and digest by wald in {time.time() - t0:.0f}s", flush=True)
    (run_dir / "calibration_counts.json").write_text(json.dumps(
        {"records": [[[list(d) for d in draws], end, after, n] for (draws, end, after), n in
                     sorted(calib.counts.items(), key=repr)],
         "sha256": calib.digest, "score": calib.score}, indent=1) + "\n")

    base = prices(per_call, s, Fraction(1), Fraction(0))
    jobs = [(s, base, p, c, test_rows, calib.counts, packs) for p in s.penalties for c in s.grid]
    if workers == 1 or len(jobs) == 1:
        outs = [test_plate(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers or min(len(jobs), os.cpu_count() or 1)) as ex:
            outs = list(ex.map(test_plate, jobs))
    plates = {(o.p, o.c): o for o in outs}
    for o in outs:
        print(f"plate p={o.p} c={o.c}: {o.seconds:.0f}s", flush=True)
    (run_dir / "e7.txt").write_text("".join(f"# p={W.num(o.p)} c={W.num(o.c)}\n{o.e7}\n\n" for o in outs))

    lines = {}
    for (p, c), po in plates.items():
        plays = B.baselines(test_rows, cal_rows, s.buckets, p) | {"wald": po.plays}
        lines[(p, c)] = {name: B.line(name, test_rows, plays[name], p, base.agreement, c) for name in B.CONTESTANTS}
    audited = audit(run_dir, test_rows, by_id, need(owner, "audit.per_domain"), s.split_seed) if stage == "stage2" else None
    return Outcome(s, rows, test_rows, calib, plates, lines, spent(run_dir), inst, budget, (per_domain, cal_per_domain),
                   per_call, stage, audited)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help=f"use dryrun.toml's proposals; only {', '.join(DRY_RUN_MODELS)} may be called")
    p.add_argument("--dry-run-file", type=Path, default=DRY_RUN,
                   help="another dry run's settings (its models still restricted to the list above)")
    p.add_argument("--stage", choices=STAGES, help="the real run's stage (owner.toml); required without --dry-run")
    p.add_argument("--scoreboard", type=Path)
    p.add_argument("--budget-usd", type=Decimal, help="a dry run's budget; the real run's caps are the owner's")
    p.add_argument("--run-dir", type=Path)
    p.add_argument("--replay", action="store_true",
                   help="play from the answers and grades already recorded in the run directory; refuse any call")
    p.add_argument("--workers", type=int, help="test plates played in parallel (default: one per plate, up to the CPUs)")
    a = p.parse_args(argv)
    if a.dry_run == bool(a.stage):
        p.error("give --dry-run (with --budget-usd) or --stage, not both and not neither")
    if a.dry_run and a.budget_usd is None:
        p.error("a dry run needs --budget-usd")
    owner = load(a.dry_run_file if a.dry_run else OWNER)
    run_dir = a.run_dir or HERE / "runs" / ("dry-run" if a.dry_run else "run")
    from showcases.omniscience import scoreboard
    out = run(owner, run_dir, a.budget_usd, a.dry_run, transport=replay_only if a.replay else None,
              workers=a.workers, stage=a.stage)
    if isinstance(out, Estimate):
        print(f"-> {run_dir / 'estimate.json'}; stopped before any test question, as ruled")
        return
    path = a.scoreboard or (HERE / "SCOREBOARD.md" if a.dry_run else run_dir / f"SCOREBOARD-{a.stage}.md")
    path.write_text(scoreboard.render(out, dry_run=a.dry_run, run_dir=run_dir.relative_to(HERE.parent.parent)
                                      if run_dir.is_relative_to(HERE.parent.parent) else run_dir))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
