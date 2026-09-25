import re
from decimal import Decimal
from pathlib import Path

import pytest
import wald

from arena.config import MissingOwnerNumber, load
from showcases.omniscience import run as RUN
from showcases.omniscience import scoreboard as SB
from tests.omniscience_fakes import Scripted, questions

FROZEN = re.compile(r"gpt-6|astra|gpt-5\.5|opus", re.I)
SHOWCASE = Path(RUN.__file__).parent


def small(owner):
    "The dry run's numbers on a World small enough for a test: two buckets and one hypothesis per Global but calib."
    owner["confidence"]["cuts"] = [50]
    owner["confidence"]["unread"] = "b0"
    owner["globals"] = {"rho": ["1/10", "7/10"], "agree": [["4/5", "1/5"]], "second": [["1/2", "4/5", "1/5"]],
                        "grader": ["9/10", "1"]}
    owner["penalties"] = [1, 3]
    return owner


def dry(tmp_path, budget="1", fake=None, write_packs=False):
    fake = fake or Scripted()
    o = RUN.run(small(load(RUN.DRY_RUN)), tmp_path / "run", Decimal(budget), True, transport=fake,
                questions=questions(10), write_packs=write_packs, workers=1)
    return o, fake


def test_no_frozen_model_can_be_built_until_the_owner_rules():
    owner = load(RUN.OWNER)
    with pytest.raises(MissingOwnerNumber, match=r"instruments\.primary\.model"):
        RUN.instruments(owner, dry_run=False, transport=lambda m: pytest.fail("a transport was built"))
    with pytest.raises(MissingOwnerNumber):
        RUN.main(["--budget-usd", "1"])


def test_a_dry_run_refuses_any_model_but_haiku():
    owner = load(RUN.DRY_RUN)
    owner["instruments"]["second"]["model"] = "gpt-6-astra"
    with pytest.raises(RUN.NotADryRunModel, match="gpt-6-astra"):
        RUN.instruments(owner, dry_run=True, transport=lambda m: lambda s, u: pytest.fail("called"))


def test_no_frozen_model_is_named_in_the_showcase_code_or_its_owner_files():
    for path in [*SHOWCASE.glob("*.py"), *SHOWCASE.glob("*.toml")]:
        text = "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("#"))
        assert not FROZEN.search(text), path


def test_the_budget_sets_the_draw_and_is_never_exceeded(tmp_path):
    o, fake = dry(tmp_path, "1")
    per_q = RUN.per_question_usd(o.instruments, o.settings)
    assert o.per_domain[0] == min(int(Decimal(1) / (per_q * 6)), 10)
    assert sum(c.usd for c in o.calls) <= Decimal(1) and fake.calls == len(o.calls)
    assert len(o.rows) == 6 * o.per_domain[0]


def test_the_wallet_stops_before_the_call_that_would_overspend_and_remembers_across_a_resume(tmp_path):
    inst = RUN.from_owner(load(RUN.DRY_RUN), "primary", lambda m: lambda s, u: None)
    log = tmp_path / "reserved.jsonl"
    w = RUN.Budget(Decimal("0.0015"), log)
    w.reserve(inst)
    w.reserve(inst)
    with pytest.raises(RUN.BudgetExceeded):
        w.reserve(inst)
    resumed = RUN.Budget(Decimal("0.0015"), log)
    assert resumed.spent == Decimal("0.0014")
    with pytest.raises(RUN.BudgetExceeded):
        resumed.reserve(inst)


def test_end_to_end_resumes_without_paying_twice_and_scores_every_contestant(tmp_path):
    o, fake = dry(tmp_path, "1")
    first = fake.calls
    o2, fake2 = dry(tmp_path, "1")
    assert fake2.calls == 0 and len(o2.calls) == first
    assert set(o.lines) == set(o.plates) == {(p, c) for p in o.settings.penalties for c in o.settings.grid}
    n_test = sum(r["split"] == "test" for r in o.rows)
    for lines in o.lines.values():
        assert set(lines) == set(RUN.B.CONTESTANTS) and all(L.n == n_test for L in lines.values())
    raw = next(iter(o.lines.values()))["raw model"]
    assert raw.coverage == 1 and raw.consult_rate == 0
    for po in o.plates.values():
        assert po.counts_n == sum(o.calibration.counts.values()) + n_test
        assert po.e7 and "no class" in po.disclosure
    md = SB.render(o, dry_run=True, run_dir="runs/test")
    for said in ("self-graded, degenerate", "not AA's grader", "| wald |", "What the Counts moved", "E7, p = 1",
                 "S15", "blind switches"):
        assert said in md, said


def test_the_run_writes_lawful_packs_that_ship_the_calibration(tmp_path):
    o, _ = dry(tmp_path, "0.5", write_packs=True)
    packs = sorted((tmp_path / "run" / "packs").glob("*.py"))
    assert len(packs) == len(o.plates)
    for p in packs:
        text = p.read_text()
        assert o.calibration.digest in text and text.startswith("# omniscience-p")
        wald.declare(wald.load_pack(text, "."))


def test_no_second_opinion_cannot_be_priced_none():
    owner = load(RUN.DRY_RUN)
    owner["second_price_grid"] = ["1/10", "none"]
    with pytest.raises(ValueError, match="2.22"):
        RUN.settings(owner)


def test_a_thin_bucket_stops_the_run_before_any_test_question(tmp_path):
    owner = small(load(RUN.DRY_RUN))
    owner["confidence"]["cuts"] = [95]            # the scripted model states 90 or 30: nothing reaches 95
    with pytest.raises(RUN.BucketGate, match="under a fifth"):
        RUN.run(owner, tmp_path / "run", Decimal("1"), True, transport=Scripted(), questions=questions(10),
                write_packs=False, workers=1)


def test_calibration_counts_are_constructed_one_record_per_question_every_instrument_drawn(tmp_path):
    o, _ = dry(tmp_path, "1")
    cal = [r for r in o.rows if r["split"] == "calibration"]
    C = o.calibration
    assert sum(C.counts.values()) == len(cal)
    assert all([a for a, _ in draws] == ["confidence", "agreement", "second_opinion"] for draws, _, _ in C.counts)
    ends = {end for (draws, end, _) in C.counts if dict(draws)["second_opinion"] == "same"}
    assert ends <= {"answer_primary"}
    assert sum(C.shares.values()) == 1
