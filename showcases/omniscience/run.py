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
import hashlib
import json
import os
import pickle
import random
import threading
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


class Stopped(RuntimeError):
    "A call not started because another worker's failure stopped the run first."


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
    declared price, or for an instrument priced `measured`, the most the call can cost (list price for BOUND_INPUT
    tokens in and the instrument's whole max_tokens out). After the call the reservation is settled at what the call
    cost, list price from its tokens. Spend is the settled costs plus every reservation not settled (a call in flight
    or cut off), so calls made at once never pass a cap together, and a run cut off mid-question resumes knowing what
    it paid. It stops before a call that could take the whole run's spend past `limit`, or this stage's past
    `stage_limit` (QUESTIONS.md 2.14 as ruled 2026-09-28). Thread-safe: each thread holds its own reservations; once
    `stop()` is called (or a cap refuses a call) every later reservation raises Stopped, so no new call starts."""

    def __init__(self, limit: Decimal, log: Path | None = None, stage: str = "", stage_limit: Decimal | None = None):
        self.limit, self.log, self.stage, self.stage_limit = limit, log, stage, stage_limit
        self.rows = read_rows(log) if log else []
        self.open: dict[tuple[int, str], int] = {}
        self.lock = threading.RLock()
        self.stopped = False

    def stop(self):
        with self.lock:
            self.stopped = True

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
        "The most the next call can cost: list price for BOUND_INPUT tokens in and the whole output cap out."
        if instrument.usd_per_call is not None:
            return instrument.usd_per_call
        return instrument.list_usd(BOUND_INPUT, instrument.max_output or BOUND_OUTPUT)

    def _write(self, row: dict):
        self.rows.append(row)
        if self.log:
            with open(self.log, "a") as f:
                f.write(json.dumps(row) + "\n")

    def reserve(self, instrument: Instrument):
        with self.lock:
            if self.stopped:
                raise Stopped(f"the run stopped before this {instrument.name} call")
            b = self.bound(instrument)
            try:
                if self.spent + b > self.limit:
                    raise BudgetExceeded(f"the next {instrument.name} call (up to ${b}) could take the run's spend "
                                         f"past ${self.limit} (spent ${self.spent})")
                if self.stage_limit is not None and self._spent(self.stage) + b > self.stage_limit:
                    raise BudgetExceeded(f"the next {instrument.name} call (up to ${b}) could take stage "
                                         f"{self.stage}'s spend past ${self.stage_limit} "
                                         f"(spent ${self._spent(self.stage)})")
            except BudgetExceeded:
                self.stopped = True
                raise
            self.open[(threading.get_ident(), instrument.name)] = len(self.rows)
            self._write({"instrument": instrument.name, "usd": str(b), "stage": self.stage})

    def settle(self, instrument_name: str, call: Call):
        "What a measured call cost, list price from its tokens; a declared price was reserved exactly."
        with self.lock:
            i = self.open.pop((threading.get_ident(), instrument_name), None)
            if i is not None and Decimal(self.rows[i]["usd"]) != call.usd:
                self._write({"settle": i, "usd": str(call.usd)})


BOUND_INPUT = 4000       # the longest prompt measured is 1,823 tokens (the grader's, in the dry runs)
BOUND_OUTPUT = 16000     # an instrument with no max_tokens of its own: the transports' default cap


class ModelChanged(RuntimeError):
    pass


class ServedModels:
    """The model each instrument's provider says served each call (2.3), from every call already recorded. The run
    stops if an instrument is served a model other than the one it was served before."""

    def __init__(self, calls=()):
        self.seen: dict[str, str] = {}
        self.lock = threading.Lock()
        for c in calls:
            self(c)

    def __call__(self, c: Call):
        if not c.served_model:
            return
        base = c.instrument.split(".")[0]
        with self.lock:
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
    changes: tuple = ()              # the owner's changes to the pre-registration, each stated on the board

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
                     for m, v in optional(owner, "list_price_per_mtok", {}).items()},
                    tuple(optional(owner, "board.changes", [])))


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
        if not dry_run and not stated(optional(owner, f"instruments.{role}.listed", "")):
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


STAGES = ("pilot-calibration", "pilot-test", "stage2-calibration", "stage2")
GO = {"pilot-test": "go.pilot_test", "stage2-calibration": "go.stage2", "stage2": "go.stage2_test"}
CALIBRATION_STAGES = ("pilot-calibration", "stage2-calibration")
SHOWN_CUTS = (70, 80, 85, 90, 95)     # the cuts the calibration stages show beside the ruled one, for the owner


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


def estimate(rows, calls_by_q, spent: Decimal, ahead: dict[str, int]) -> Estimate:
    "Measured $ and reasoning tokens per question on `rows`, and the dollars of each part still ahead (label -> n)."
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
                    {label: each * k for label, k in ahead.items()} | {"whole run": spent + each * sum(ahead.values())},
                    spent)


def spent(run_dir: Path) -> list[Call]:
    "Every call paid for, from the log written as each call returns; a run recorded before that log, from its rows."
    if (run_dir / "calls.jsonl").exists():
        return [Call.from_json(r) for r in read_rows(run_dir / "calls.jsonl")]
    return [Call.from_json(c) for r in read_rows(run_dir / "records.jsonl") for c in r["calls"]] + \
        grading_calls(run_dir / "grades.jsonl")


def stated(value) -> bool:
    "A date the owner wrote: a non-empty string. `false`, `0` or an empty string is not a go, nor a verification."
    return isinstance(value, str) and bool(value.strip())


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


def cut_table(cal_rows, s: Settings) -> str:
    """For the owner ruling the cut (2.15; rechecked on stage 2's 300 records before any stage-2 test question): at
    each shown cut and the ruled one, each bucket's records and how many reads in it were right. Counts, displayed;
    which cut "separates clearly better" is the owner's judgement, not a threshold here (rule 6)."""
    lines = [f"cut table on {len(cal_rows)} calibration records (ruled cut {list(s.cuts)}; unread -> {s.unread}):"]
    for cut in sorted(set(SHOWN_CUTS) | set(s.cuts)):
        parts = []
        for b in ("b0", "b1"):
            here = [r for r in cal_rows if OBS.bucket_of(r["confidence"], (cut,), s.unread) == b]
            right = sum(r["g1"] == "right" for r in here)
            parts.append(f"{b} {len(here)} ({len(here) / len(cal_rows):.0%}), {right} right"
                         + (f" ({right / len(here):.0%})" if here else ""))
        lines.append(f"  cut {cut}{' (ruled)' if (cut,) == tuple(s.cuts) else ''}: " + "; ".join(parts))
    return "\n".join(lines)


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


def write_counts(run_dir: Path, calib: Calibration):
    (run_dir / "calibration_counts.json").write_text(json.dumps(
        {"records": [[[list(d) for d in draws], end, after, n] for (draws, end, after), n in
                     sorted(calib.counts.items(), key=repr)],
         "sha256": calib.digest, "score": calib.score}, indent=1) + "\n")


POSTERIOR_NOTE = ("P(Global | Counts) is wald's (wald.counts.posterior_global, rendered by wald.report); the marginals "
                  "are that text's exact rationals summed per component, for the owner to read. No contestant reads either.")


def posterior(s: Settings, per_call, calib: Calibration) -> tuple[dict, dict]:
    """wald's P(Global | Counts), as the exact rationals wald.report renders, and each Global component's marginal
    summed from them: a display for the owner (S1), never read by a contestant. The Counts' likelihood does not
    depend on the prices, so one declaration serves every plate."""
    import re
    import wald.counts
    _, world = W.declare(W.text(s.buckets, s.grids, prices(per_call, s, Fraction(1), Fraction(0)), "omniscience",
                                calib.counts))
    text = str(wald.report(wald.counts.posterior_global(world, calib.counts)))
    joint = {tuple(x.strip("' ") for x in m.group(1).split("', '")): Fraction(int(m.group(2)), int(m.group(3) or 1))
             for m in re.finditer(r"\(('[^)]*')\) (\d+)(?:/(\d+))?", text)}
    if sum(joint.values()) != 1:
        raise ValueError("wald.report's posterior did not parse to a distribution; its format has changed")
    marg = {}
    for key, q in joint.items():
        for part in key:
            name, value = part.split(" ", 1)
            pairs = zip((f"rho {b}" for b in s.buckets), value.split()) if name == "rho" else [(name, value)]
            for n, v in pairs:                      # ρ is one Global value per bucket: a marginal for each
                marg.setdefault(n, {}).setdefault(v, Fraction(0))
                marg[n][v] += q
    return marg, joint


def _disclosure(args):
    s, per_call, counts, p, c = args
    _, world = W.declare(W.text(s.buckets, s.grids, prices(per_call, s, p, c), "omniscience", counts))
    return str(wald.plate(world).disclosure())


def disclosures(s: Settings, per_call, calib: Calibration, workers: int | None) -> dict:
    "S15's disclosure (Plate.disclosure) for the declaration at each (p, c), with the Counts shipped."
    jobs = [(s, per_call, calib.counts, p, c) for p in s.penalties for c in s.grid]
    if workers == 1:
        return {(j[3], j[4]): _disclosure(j) for j in jobs}
    with ProcessPoolExecutor(max_workers=workers or 3) as ex:
        return {(j[3], j[4]): d for j, d in zip(jobs, ex.map(_disclosure, jobs))}


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
    plate, played = B.play_plate(world, test_rows, s.samples, label=name)
    _, fresh = B.play_plate(bare, test_rows, s.samples, fresh=True, label=name)
    plays, results = [x[0] for x in played], [x[1] for x in played]
    fplays, fresults = [x[0] for x in fresh], [x[1] for x in fresh]
    first = wald.plate(bare).run(B.RecordedDoor(test_rows[0], s.samples)).acts
    return PlateOut(p, c, plays, fplays, realised(test_rows, plays, results, p, c),
                    realised(test_rows, fplays, fresults, p, c), str(wald.e7(world, plate.counts())),
                    draws_per_line(plate.counts()),
                    str(plate.disclosure()), (results[0].acts, first),
                    sum(a.acts != b.acts for a, b in zip(results, fresults)), sum(plate.counts().values()),
                    time.time() - t0)


PLATES = "plates.pkl"


def plates_key(jobs, digest: str) -> str:
    """What a plate's result depends on: the Counts (by digest), the test questions in plate order with everything
    the door serves, the settings and prices of every (p, c). Plates are replayed when any of it changes."""
    s, base, _, _, test_rows, _, _ = jobs[0]
    return hashlib.sha256(repr((digest, repr(s), repr(base), [(p, c) for _, _, p, c, *_ in jobs],
                                [sorted(r.items()) for r in test_rows])).encode()).hexdigest()


def saved_plates(run_dir: Path, jobs, digest: str):
    """The plates' results as a run saved them, if their key still holds; else None and the plates are played.
    Playing stage 2's 21 plates takes hours; the owner's audit then re-renders the board from these."""
    path = run_dir / PLATES
    if not path.exists():
        return None
    saved = pickle.loads(path.read_bytes())
    if saved["key"] != plates_key(jobs, digest):
        print(f"{PLATES}: saved for other Counts, questions or prices; playing the plates again", flush=True)
        return None
    print(f"{PLATES}: the plates' results as saved ({len(saved['plates'])} plates); not played again", flush=True)
    return saved["plates"]


def save_plates(run_dir: Path, jobs, digest: str, outs) -> None:
    (run_dir / PLATES).write_bytes(pickle.dumps({"key": plates_key(jobs, digest), "plates": outs}))


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
    marginals: dict | None = None    # P(Global | Counts) per component, summed from wald.report: a display (S1)
    pilot_test_ids: frozenset = frozenset()   # seen before α was widened: the verdict leaves them out (2026-09-29)


AUDIT_FIELDS = ("question_id", "domain", "question", "gold_answer", "answer", "grader_grade", "owner_grade")


def audit(run_dir: Path, test_rows, by_id, per_domain: int, seed: int) -> tuple[int, int, int]:
    """2.9 as ruled: the owner hand-audits `per_domain` grades per domain, drawn with the seed from the whole test
    split's graded answers (the read's and the second opinion's; all 300, the pilot's included, as ruled 2026-09-28),
    before the verdict line is written. The sample is written
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


GRADING = ("grader", "equivalence")


def supersede_grading(owner, run_dir: Path, note: str, transport=None, questions=None) -> int:
    """The pilot's grades and equivalence sorts, redone under the grader configuration now in `owner.toml` (2.9 (b),
    ruled 2026-09-28): the calls already made stay in the log, marked `superseded` with `note`; the grade memo moves to
    `grades.superseded.jsonl`, so the next run grades afresh; each record keeps its old classes and equivalence call
    beside the new ones. Only the equivalence calls are made here, reserved and settled against the pilot's caps.
    Idempotent: a record already sorted under the current configuration is left alone. Returns the calls made."""
    inst = instruments(owner, dry_run=False, transport=transport)
    want = inst["equivalence"].effort or optional(owner, "instruments.equivalence.thinking", "")
    log = run_dir / "calls.jsonl"
    marked = [c | ({"superseded": note} if c["instrument"].split(".")[0] in GRADING and c.get("effort", "") != want
                   and not c.get("superseded") else {}) for c in read_rows(log)]
    log.write_text("".join(json.dumps(c) + "\n" for c in marked))
    if (run_dir / "grades.jsonl").exists() and not (run_dir / "grades.superseded.jsonl").exists():
        (run_dir / "grades.jsonl").rename(run_dir / "grades.superseded.jsonl")
    wallet = Budget(Decimal(need(owner, "stages.whole_cap_usd")), run_dir / "reserved.jsonl", "pilot",
                    Decimal(need(owner, "stages.pilot_cap_usd")))
    served = ServedModels(spent(run_dir))
    by_id = {q.id: q for q in (questions if questions is not None else QS.load())}
    doms = QS.domains(list(by_id.values()))
    rows, made = read_rows(run_dir / "records.jsonl"), 0
    out = []
    for r in rows:
        eq = [c for c in r["calls"] if c["instrument"] == "equivalence"]
        if eq and all(c.get("effort", "") == want for c in eq):
            out.append(r)
            continue
        q = by_id[r["question_id"]]
        wallet.reserve(inst["equivalence"])
        classes, c = OBS.equivalence(inst["equivalence"], q, OBS.domain_index(q, doms),
                                     (r["read"], *r["samples"], r["second"]))
        with open(log, "a") as f:
            f.write(json.dumps(c.to_json()) + "\n")
        wallet.settle("equivalence", c)
        served(c)
        made += 1
        seen = OBS.Seen(r["read"], r["confidence"], tuple(r["samples"]), r["second"],
                        tuple(Call.from_json(x) for x in r["calls"] if x["instrument"] != "equivalence") + (c,),
                        classes)
        out.append(r | {"k": seen.k, "s": seen.s, "classes": list(classes) if classes else None,
                        "calls": [x.to_json() for x in seen.calls],
                        "superseded": {"note": note, "classes": r.get("classes"), "k": r["k"], "s": r["s"],
                                       "calls": [x | {"superseded": note} for x in eq]}})
    tmp = run_dir / "records.jsonl.tmp"
    tmp.write_text("".join(json.dumps(r) + "\n" for r in out))
    tmp.replace(run_dir / "records.jsonl")
    return made


def run(owner, run_dir: Path, budget: Decimal | None, dry_run: bool, transport=None, questions=None,
        write_packs: bool = True, workers: int | None = None, stage: str | None = None, call_workers: int = 1):
    """A dry run (`dry_run`, sized by `budget`), or a stage of the real run (`stage`, sized and capped by the owner's
    numbers). A calibration stage returns an Estimate and plays no test question; the other stages return an Outcome.
    `call_workers` questions are observed, and answers graded, at once; the wallet keeps the caps exact."""
    s = settings(owner)
    if s.gate == "waived" and not dry_run:
        raise ValueError("confidence.gate = 'waived' is the Haiku dry run's alone; the gate stands for the real run")
    if not dry_run and stage not in STAGES:
        raise ValueError(f"the real run goes by stage: one of {', '.join(STAGES)}")
    if stage in GO and not stated(optional(owner, GO[stage], "")):
        raise NoGo(f"{GO[stage]} is not set in owner.toml: the owner's go comes first (2.14)")
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
        cal, test = {"pilot-calibration": (pcal, []), "pilot-test": (pcal, ptest),
                     "stage2-calibration": (cal_all, []), "stage2": (cal_all, test_all)}[stage]
        group = "stage2" if stage.startswith("stage2") else "pilot"
        if stage == "stage2":
            seen = {r["question_id"] for r in read_rows(run_dir / "records.jsonl")}
            if not {q.id for q in cal_all} <= seen:
                raise NoGo("stage 2's calibration split is not all recorded: run --stage stage2-calibration first, "
                           "so the gate, the cut and the Counts are seen before any stage-2 test question")
        wallet = Budget(Decimal(need(owner, "stages.whole_cap_usd")), run_dir / "reserved.jsonl", group,
                        Decimal(need(owner, "stages.pilot_cap_usd")) if group == "pilot" else None)
        print(f"stage {stage}: {len(cal)} calibration, {len(test)} test questions; spent ${wallet.spent} of the "
              f"${wallet.limit} whole-run cap" + (f", ${wallet._spent('pilot')} of the pilot's ${wallet.stage_limit}"
                                                  if group == "pilot" else ""), flush=True)
    if not (run_dir / "calls.jsonl").exists() and (run_dir / "records.jsonl").exists():
        with open(run_dir / "calls.jsonl", "w") as f:           # a run recorded before the log: seed it from its rows
            f.writelines(json.dumps(c.to_json()) + "\n" for c in spent(run_dir))
    served = ServedModels(spent(run_dir))

    log_lock = threading.Lock()

    def after(c: Call):
        "Log the call the moment it returns (rule 5), whatever stops the run next; then settle it and check its model."
        with log_lock:
            with open(run_dir / "calls.jsonl", "a") as f:
                f.write(json.dumps(c.to_json()) + "\n")
        wallet.settle(c.instrument.split(".")[0], c)
        served(c)

    def stopping(f):
        "Any failure in one worker stops the wallet, so the others start no new call."
        def run_one(*args):
            try:
                return f(*args)
            except BaseException:
                wallet.stop()
                raise
        return run_one

    tier = lambda q: OBS.domain_index(q, doms)
    items = [("calibration", q) for q in cal] + [("test", q) for q in test]
    append_new(items, lambda it: it[1].id,
               stopping(lambda it: record(it[1], it[0], tier(it[1]),
                                          OBS.observe(inst["primary"], inst["second"], it[1], tier(it[1]), s.samples,
                                                      wallet.reserve, inst.get("equivalence"), after),
                                          (s.cuts, s.unread))),
               run_dir / "records.jsonl", call_workers, quiet=(Stopped,))
    grader = Grader(inst["grader"], run_dir / "grades.jsonl", tier, wallet.reserve, after)
    by_id = {q.id: q for q in qs}
    order = {q.id: i for i, (_, q) in enumerate(items)}    # the split's order, whatever order the calls finished in
    recs = sorted((r for r in read_rows(run_dir / "records.jsonl") if r["question_id"] in order),
                  key=lambda r: order[r["question_id"]])
    grader.grade_all([(by_id[r["question_id"]], a) for r in recs for a in (r["read"], r["second"])], call_workers,
                     quiet=(Stopped,), guard=stopping)
    rows = []
    for r in recs:
        q = by_id[r["question_id"]]
        g1, g2 = grader(q, r["read"]), grader(q, r["second"])
        rows.append(r | {"b": OBS.bucket_of(r["confidence"], s.cuts, s.unread), "grade1": g1, "grade2": g2,
                         "g1": B.grade_class(g1), "g2": B.grade_class(g2)})

    if stage in CALIBRATION_STAGES:
        calls_by_q = {}
        for r in rows:
            calls_by_q[r["question_id"]] = [Call.from_json(c) for c in r["calls"]]
        for c in grading_calls(run_dir / "grades.jsonl"):
            calls_by_q.setdefault(c.question_id, []).append(c)
        n_ptest = need(owner, "stages.pilot_test")
        ahead = ({"pilot test": n_ptest, "stage 2": len(cal_all) + len(test_all) - len(pcal) - n_ptest}
                 if stage == "pilot-calibration" else {"stage 2 test": len(test_all) - n_ptest})
        est = estimate(rows, calls_by_q, wallet.spent, ahead)
        (run_dir / "estimate.json").write_text(json.dumps(
            {"n": est.n, "per_question": {k: str(v) for k, v in est.per_question.items()},
             "reasoning_tokens_per_call": est.reasoning, "projected": {k: str(v) for k, v in est.projected.items()},
             "spent": str(est.spent)}, indent=1) + "\n")
        print(f"measured on {est.n} calibration questions: $ per question " + ", ".join(
            f"{k} {v:.5f}" for k, v in est.per_question.items()) + "; reasoning tokens per call " + ", ".join(
            f"{k} {v:.0f}" for k, v in est.reasoning.items()), flush=True)
        print("projected: " + ", ".join(f"{k} ${v:.2f}" for k, v in est.projected.items()), flush=True)
        cuts = cut_table(rows, s)
        (run_dir / "cuts.txt").write_text(cuts + "\n")
        print(cuts, flush=True)
        shares, thin = bucket_gate(rows, s, dry_run)
        per_call = per_call_usd(inst, rows, grading_calls(run_dir / "grades.jsonl"))
        calib = calibrate(s, per_call, rows, shares, thin)
        write_counts(run_dir, calib)
        marg, joint = posterior(s, per_call, calib)
        (run_dir / "posterior.json").write_text(json.dumps(
            {"counts_sha256": calib.digest, "note": POSTERIOR_NOTE,
             "marginals": {n: {v: str(q) for v, q in vals.items()} for n, vals in marg.items()},
             "posterior": {" | ".join(k): str(q) for k, q in joint.items()}}, indent=1) + "\n")
        disc = disclosures(s, per_call, calib, workers)
        (run_dir / "disclosure.txt").write_text(
            "".join(f"p={W.num(p)} c={W.num(c)}: {d}\n" for (p, c), d in disc.items()))
        print(f"calibration Counts: {sum(calib.counts.values())} records, {len(calib.counts)} distinct, sha256 "
              f"{calib.digest}", flush=True)
        print("P(Global | Counts), summed from wald.report for display: " + "; ".join(
            f"{n}: " + ", ".join(f"{v} {float(q):.1%}" for v, q in vals.items() if q >= Fraction(1, 1000))
            for n, vals in marg.items()), flush=True)
        print("S15: " + "; ".join(sorted(set(disc.values()))), flush=True)
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
    write_counts(run_dir, calib)
    marg = None
    if not dry_run:
        marg, joint = posterior(s, per_call, calib)
        (run_dir / "posterior.json").write_text(json.dumps(
            {"counts_sha256": calib.digest, "note": POSTERIOR_NOTE,
             "marginals": {n: {v: str(q) for v, q in vals.items()} for n, vals in marg.items()},
             "posterior": {" | ".join(k): str(q) for k, q in joint.items()}}, indent=1) + "\n")

    base = prices(per_call, s, Fraction(1), Fraction(0))
    jobs = [(s, base, p, c, test_rows, calib.counts, packs) for p in s.penalties for c in s.grid]
    outs = saved_plates(run_dir, jobs, calib.digest)
    if outs is None:
        if workers == 1 or len(jobs) == 1:
            outs = [test_plate(j) for j in jobs]
        else:
            with ProcessPoolExecutor(max_workers=workers or min(len(jobs), os.cpu_count() or 1)) as ex:
                outs = list(ex.map(test_plate, jobs))
        save_plates(run_dir, jobs, calib.digest, outs)
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
                   per_call, stage, audited, marg, frozenset(q.id for q in ptest) if stage == "stage2" else frozenset())


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
    p.add_argument("--supersede-grading", metavar="NOTE",
                   help="mark the grades and equivalence sorts made under another grader configuration superseded, "
                        "and redo the sorts under owner.toml's; the next --stage run re-grades")
    p.add_argument("--workers", type=int, help="test plates played in parallel (default: one per plate, up to the CPUs)")
    p.add_argument("--call-workers", type=int,
                   help="questions observed, and answers graded, at once (default: owner.toml calls.workers, else 1)")
    a = p.parse_args(argv)
    if a.dry_run == bool(a.stage):
        p.error("give --dry-run (with --budget-usd) or --stage, not both and not neither")
    if a.dry_run and a.budget_usd is None:
        p.error("a dry run needs --budget-usd")
    owner = load(a.dry_run_file if a.dry_run else OWNER)
    run_dir = a.run_dir or HERE / "runs" / ("dry-run" if a.dry_run else "run")
    if a.supersede_grading:
        if a.dry_run or a.stage != "pilot-calibration":
            p.error("--supersede-grading goes with --stage pilot-calibration")
        print(f"re-sorted {supersede_grading(owner, run_dir, a.supersede_grading)} records under the current grader")
        return
    from showcases.omniscience import scoreboard
    out = run(owner, run_dir, a.budget_usd, a.dry_run, transport=replay_only if a.replay else None,
              workers=a.workers, stage=a.stage, call_workers=a.call_workers or optional(owner, "calls.workers", 1))
    if isinstance(out, Estimate):
        print(f"-> {run_dir / 'estimate.json'}; stopped before any test question, as ruled")
        return
    path = a.scoreboard or (HERE / "SCOREBOARD.md" if a.dry_run else run_dir / f"SCOREBOARD-{a.stage}.md")
    path.write_text(scoreboard.render(out, dry_run=a.dry_run, run_dir=run_dir.relative_to(HERE.parent.parent)
                                      if run_dir.is_relative_to(HERE.parent.parent) else run_dir))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
