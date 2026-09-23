import re
from decimal import Decimal
from pathlib import Path

import pytest

from arena.config import MissingOwnerNumber, load
from showcases.omniscience import run as RUN
from showcases.omniscience import scoreboard as SB
from tests.omniscience_fakes import Scripted, questions

FROZEN = re.compile(r"gpt-6|astra|gpt-5\.5|opus", re.I)
SHOWCASE = Path(RUN.__file__).parent


def dry(tmp_path, budget="1", fake=None):
    fake = fake or Scripted()
    o = RUN.run(load(RUN.DRY_RUN), tmp_path / "run", Decimal(budget), True, transport=fake,
                questions=questions(10), write_packs=False)
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
    assert set(o.lines) == {(p, c) for p in o.settings.penalties for c in o.settings.grid}
    for lines in o.lines.values():
        assert set(lines) == set(RUN.B.CONTESTANTS)
        assert all(L.n == sum(r["split"] == "test" for r in o.rows) for L in lines.values())
    raw = o.lines[(o.settings.penalties[0], None)]["raw model"]
    assert raw.coverage == 1 and raw.consult_rate == 0
    for m in o.model.values():
        assert m["exact"] >= m["wald_expected"] - 1e-9
    md = SB.render(o, dry_run=True, run_dir="runs/test")
    assert "self-graded, degenerate" in md and "not AA's grader" in md and "| wald |" in md


def test_the_run_writes_lawful_packs(tmp_path):
    o = RUN.run(load(RUN.DRY_RUN), tmp_path / "run", Decimal("0.5"), True, transport=Scripted(),
                questions=questions(6), write_packs=True)
    packs = list((tmp_path / "run" / "packs").rglob("*.py"))
    assert packs and all(p.read_text().startswith("# omni_s") for p in packs)
