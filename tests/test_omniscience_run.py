import json
import re
from collections import Counter
from fractions import Fraction
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


def test_no_frozen_model_can_be_built_until_each_is_verified_on_the_day():
    owner = load(RUN.OWNER)
    assert all(i["listed"] for i in owner["instruments"].values())       # pinned 2026-09-28
    owner["instruments"]["primary"]["listed"] = ""
    with pytest.raises(RUN.NotListed, match=r"instruments\.primary\.listed"):
        RUN.instruments(owner, dry_run=False, transport=lambda m: pytest.fail("a transport was built"))


def real(tmp_path, go=(), cap="15"):
    "owner.toml, verified and scaled to the fake board: 10 questions a domain, a pilot of 26 + 26."
    owner = load(RUN.OWNER)
    for i in owner["instruments"].values():
        i["listed"] = "test"
    owner["split"] = {"per_domain": 10, "calibration_per_domain": 5}
    owner["stages"].update(pilot_calibration=26, pilot_test=26, pilot_cap_usd=cap)
    owner["globals"] = {"rho": ["1/10", "7/10"], "agree": [["4/5", "1/5"]], "second": [["1/2", "4/5", "1/5"]],
                        "grader": ["9/10", "1"], "corr": ["0", "1/2"]}
    owner["penalties"], owner["second_price_grid"] = [1, 3], ["1/10", "1"]
    owner["confidence"]["cuts"] = [50]
    owner["audit"]["per_domain"] = 2
    owner["go"] = {"pilot_test": "", "stage2": "", "stage2_test": ""}   # the owner's real gates are not the test's
    for k in go:
        owner["go"][k] = "2026-09-28"
    return owner


def stage(tmp_path, owner, name, fake, call_workers=1):
    return RUN.run(owner, tmp_path / "run", None, False, transport=fake, questions=questions(10), write_packs=False,
                   workers=1, stage=name, call_workers=call_workers)


def test_the_real_run_goes_by_stage_each_later_one_waits_for_the_go_and_spend_is_measured(tmp_path):
    fake = Scripted(served="served-1")
    est = stage(tmp_path, real(tmp_path), "pilot-calibration", fake)
    assert isinstance(est, RUN.Estimate) and est.n == 26
    assert set(est.per_question) == {"primary", "second", "grader", "equivalence"}
    recs = [json.loads(line) for line in open(tmp_path / "run" / "records.jsonl")]
    assert len(recs) == 26 and {r["split"] for r in recs} == {"calibration"}
    assert all(len(r["samples"]) == 3 and r["classes"] for r in recs)     # three samples, read by classes
    post = json.loads((tmp_path / "run" / "posterior.json").read_text())
    assert sum(Fraction(q) for q in post["posterior"].values()) == 1
    assert all(sum(Fraction(q) for q in m.values()) == 1 for m in post["marginals"].values())
    assert len((tmp_path / "run" / "disclosure.txt").read_text().splitlines()) == 4          # every (p, c)
    assert json.loads((tmp_path / "run" / "calibration_counts.json").read_text())["sha256"] == post["counts_sha256"]
    assert Counter(r["domain"] for r in recs).most_common()[0][1] == 5 and len({r["domain"] for r in recs}) == 6
    with pytest.raises(RUN.NoGo, match="go.pilot_test"):
        stage(tmp_path, real(tmp_path), "pilot-test", fake)
    before = fake.calls
    o = stage(tmp_path, real(tmp_path, go=("pilot_test",)), "pilot-test", fake)
    assert len(o.test_rows) == 26 and o.stage == "pilot-test"
    assert fake.calls > before and all(c.usd > 0 for c in o.calls)       # measured: list price from the tokens
    md = SB.render(o, dry_run=False, run_dir="runs/test")
    assert "Re-scored with gemini-3.8-flash, not AA's grader" in md and "gpt-5.5 at low reasoning effort" in md
    assert "— (pilot)" in md and "p = 10 is underpowered" in md
    with pytest.raises(RUN.NoGo, match="go.stage2"):
        stage(tmp_path, real(tmp_path), "stage2", fake)


def test_stage2_writes_the_audit_sample_and_withholds_the_verdict_until_it_is_filled(tmp_path, monkeypatch):
    fake = Scripted()
    owner = real(tmp_path, go=("pilot_test", "stage2", "stage2_test"), cap="100")
    pilot = stage(tmp_path, owner, "pilot-test", fake)
    with pytest.raises(RUN.NoGo, match="stage2-calibration first"):          # the cut is seen before any test
        stage(tmp_path, owner, "stage2", fake)
    est = stage(tmp_path, owner, "stage2-calibration", fake)
    assert isinstance(est, RUN.Estimate) and est.n == 30 and set(est.projected) == {"stage 2 test", "whole run"}
    recs = [json.loads(line) for line in open(tmp_path / "run" / "records.jsonl")]
    assert sum(r["split"] == "test" for r in recs) == 26                      # no stage-2 test question observed
    cuts = (tmp_path / "run" / "cuts.txt").read_text()
    assert "on 30 calibration records" in cuts and "cut 50 (ruled)" in cuts and "cut 90:" in cuts
    no_go = real(tmp_path, go=("pilot_test", "stage2"), cap="100")
    with pytest.raises(RUN.NoGo, match="go.stage2_test"):
        stage(tmp_path, no_go, "stage2", fake)
    o = stage(tmp_path, owner, "stage2", fake)
    assert len(o.rows) == 60 and o.audit[:2] == (0, 12)
    # the verdict reads the 4 test questions the pilot did not see; all 30 beside it (ruled 2026-09-29)
    assert o.pilot_test_ids == {r["question_id"] for r in pilot.test_rows}
    claims = SB.claims(o, dry_run=False)
    assert "Δ, 4 unseen (± 2 SE)" in claims and "Δ, all 30" in claims and "the pilot's 26 were seen first" in claims
    # 7 and 8 as ruled 2026-09-28: stage 2's Counts, its gate and its verdict cover the whole split, pilot included
    assert sum(o.calibration.counts.values()) == 30 and len(o.test_rows) == 30
    assert {r["question_id"] for r in pilot.test_rows} < {r["question_id"] for r in o.test_rows}
    assert "withheld" in SB.claims(o, dry_run=False)
    import csv
    path = tmp_path / "run" / "audit.csv"
    rows = list(csv.DictReader(open(path)))
    letter = {"CORRECT": "A", "INCORRECT": "B"}
    for r in rows:
        r["owner_grade"] = letter[r["grader_grade"]]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, RUN.AUDIT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    played = o.plates
    # the audit re-renders the board from the plates' saved results: no plate is played again
    monkeypatch.setattr(RUN, "test_plate", lambda job: (_ for _ in ()).throw(AssertionError("a plate was played")))
    o = RUN.run(owner, tmp_path / "run", None, False, transport=RUN.replay_only, questions=questions(10),
                write_packs=False, workers=1, stage="stage2")
    assert o.audit == (12, 12, 12) and "agreed with the grader on 12" in SB.claims(o, dry_run=False)
    assert o.plates == played


def test_the_pilot_cap_stops_the_run_before_the_call_that_could_pass_it(tmp_path):
    with pytest.raises(RUN.BudgetExceeded, match="stage pilot"):
        stage(tmp_path, real(tmp_path, cap="0.05"), "pilot-calibration", Scripted())
    w = RUN.Budget(Decimal("80"), tmp_path / "run" / "reserved.jsonl", "pilot", Decimal("0.05"))
    assert w.spent <= Decimal("0.05")


def test_a_served_model_that_changes_stops_the_run():
    from arena.transports import Call
    guard = RUN.ServedModels()
    c = lambda m, name="primary": Call(name, "gpt", "q", 0, 1, 1, Decimal(0), 0.0, "", served_model=m)
    guard(c("snap-1")), guard(c("snap-1", "primary.sample")), guard(c("other", "grader"))
    with pytest.raises(RUN.ModelChanged, match="primary"):
        guard(c("snap-2", "primary.confidence"))


def test_a_dry_run_refuses_any_model_but_haiku():
    owner = load(RUN.DRY_RUN)
    owner["instruments"]["second"]["model"] = "gpt-6-astra"
    with pytest.raises(RUN.NotADryRunModel, match="gpt-6-astra"):
        RUN.instruments(owner, dry_run=True, transport=lambda m: lambda s, u: pytest.fail("called"))


def test_no_frozen_model_is_named_in_the_showcase_code_or_its_dry_run_files():
    "The pre-registration is ruled (2026-09-28), so owner.toml names the frozen models; nothing else may."
    for path in [*SHOWCASE.glob("*.py"), *(p for p in SHOWCASE.glob("*.toml") if p.name != "owner.toml")]:
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
                 "S15", "blind switches", "switches after consulting"):
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
    owner["confidence"]["gate"] = "stands"
    with pytest.raises(RUN.BucketGate, match="under a fifth"):
        RUN.run(owner, tmp_path / "run", Decimal("1"), True, transport=Scripted(), questions=questions(10),
                write_packs=False, workers=1)


def test_the_gate_waived_for_the_dry_run_reports_the_thin_bucket_and_plays_on(tmp_path):
    owner = small(load(RUN.DRY_RUN))
    owner["confidence"]["cuts"] = [95]
    owner["confidence"]["gate"] = "waived"
    o = RUN.run(owner, tmp_path / "run", Decimal("1"), True, transport=Scripted(), questions=questions(10),
                write_packs=False, workers=1)
    assert o.calibration.thin and o.plates
    assert "The gate was waived for this dry run" in SB.calibration(o)


def test_the_gate_cannot_be_waived_for_the_real_run(tmp_path):
    owner = small(load(RUN.DRY_RUN))
    owner["confidence"]["gate"] = "waived"
    fake = Scripted()
    with pytest.raises(ValueError, match="the gate stands for the real run"):
        RUN.run(owner, tmp_path / "run", Decimal("1"), False, transport=fake, questions=questions(10),
                write_packs=False, workers=1)
    assert not (tmp_path / "run" / "records.jsonl").exists()      # refused before any call


def test_calibration_counts_are_constructed_one_record_per_question_every_instrument_drawn(tmp_path):
    o, _ = dry(tmp_path, "1")
    cal = [r for r in o.rows if r["split"] == "calibration"]
    C = o.calibration
    assert sum(C.counts.values()) == len(cal)
    assert all([a for a, _ in draws] == ["confidence", "agreement", "second_opinion"] for draws, _, _ in C.counts)
    ends = {end for (draws, end, _) in C.counts if dict(draws)["second_opinion"] == "same"}
    assert ends <= {"answer_primary"}
    assert sum(C.shares.values()) == 1


def test_the_ruled_kappa_is_read_from_the_owner_file_and_absent_when_unnamed():
    owner = load(RUN.DRY_RUN)
    assert RUN.settings(owner).grids.corr == ()
    owner["globals"]["corr"] = ["0", "1/2", "9/10"]
    assert RUN.settings(owner).grids.corr == (Fraction(0), Fraction(1, 2), Fraction(9, 10))


def test_a_call_paid_before_the_cap_stops_a_question_is_logged_at_once(tmp_path):
    "Rule 5: the first call is paid, the second is refused by the $0.50 cap; the paid one is in calls.jsonl."
    from arena.transports import Call
    with pytest.raises(RUN.BudgetExceeded):
        stage(tmp_path, real(tmp_path, cap="0.5"), "pilot-calibration", Scripted())
    logged = RUN.spent(tmp_path / "run")
    assert logged and all(isinstance(c, Call) for c in logged)
    wallet = RUN.Budget(Decimal("80"), tmp_path / "run" / "reserved.jsonl")
    assert sum(c.usd for c in logged) == wallet.spent             # every reservation settled, every call logged


def test_the_reserve_is_the_worst_case_a_call_can_cost_and_the_caps_hold():
    from arena.transports import Instrument
    inst = Instrument("primary", "m", None, None, list_price=(Decimal(5), Decimal(30)), max_output=16000)
    w = RUN.Budget(Decimal("1"))
    assert w.bound(inst) == Decimal("0.5")                          # 4,000 in at $5 + 16,000 out at $30 per million
    w.reserve(inst), w.reserve(inst)                                # unsettled, each counts at its worst case
    with pytest.raises(RUN.BudgetExceeded):
        w.reserve(inst)                                              # a third could take the spend past $1


@pytest.mark.parametrize("value", [False, 0, "", "  "])
def test_a_go_or_a_verification_is_a_date_not_a_boolean(tmp_path, value):
    owner = real(tmp_path)
    owner["go"]["pilot_test"] = value
    with pytest.raises(RUN.NoGo):
        stage(tmp_path, owner, "pilot-test", Scripted())
    owner["instruments"]["primary"]["listed"] = value
    with pytest.raises(RUN.NotListed):
        RUN.instruments(owner, dry_run=False, transport=lambda m: pytest.fail("a transport was built"))


def test_grading_under_another_configuration_is_superseded_kept_and_redone(tmp_path):
    "2.9 (b), ruled 2026-09-28: the old sorts and grades stay logged, marked; the sorts and grades are redone."
    owner = real(tmp_path)
    stage(tmp_path, owner, "pilot-calibration", Scripted(thinking=""))
    run_dir = tmp_path / "run"
    before = RUN.spent(run_dir)
    fake = Scripted(thinking="low")
    assert RUN.supersede_grading(owner, run_dir, "thinking off not honoured", fake, questions(10)) == 26
    assert fake.calls == 26                                               # one equivalence call a record, nothing else
    after = RUN.spent(run_dir)
    old = [c for c in after if c.superseded]
    assert len(old) == sum(c.instrument in RUN.GRADING for c in before) and len(after) == len(before) + 26
    recs = [json.loads(line) for line in open(run_dir / "records.jsonl")]
    assert all(r["superseded"]["calls"] and r["classes"] for r in recs)
    assert not (run_dir / "grades.jsonl").exists() and (run_dir / "grades.superseded.jsonl").exists()
    assert RUN.supersede_grading(owner, run_dir, "again", fake, questions(10)) == 0          # idempotent
    est = stage(tmp_path, owner, "pilot-calibration", fake)                                  # re-grades, nothing else
    grades = RUN.grading_calls(run_dir / "grades.jsonl")
    assert grades and all(g.effort == "low" for g in grades) and est.n == 26
    wallet = RUN.Budget(Decimal("80"), run_dir / "reserved.jsonl")
    assert wallet.spent == sum(c.usd for c in RUN.spent(run_dir))


def test_a_change_to_the_pre_registration_is_printed_on_the_board(tmp_path):
    owner = real(tmp_path, go=("pilot_test",))
    owner["board"] = {"changes": ["α widened, ruled after the pilot."]}
    stage(tmp_path, owner, "pilot-calibration", Scripted())
    o = stage(tmp_path, owner, "pilot-test", Scripted())
    assert "- **Changed after the pilot:** α widened, ruled after the pilot." in SB.header(o, False, "runs/test")


def test_calls_made_at_once_keep_the_caps_exact_and_stop_together(tmp_path):
    "Four questions at a time: the first refusal stops every worker; every paid call is logged and settled."
    with pytest.raises(RUN.BudgetExceeded):
        stage(tmp_path, real(tmp_path, cap="1.2"), "pilot-calibration", Scripted(), call_workers=4)
    run_dir = tmp_path / "run"
    logged = RUN.spent(run_dir)
    wallet = RUN.Budget(Decimal("80"), run_dir / "reserved.jsonl", "pilot", Decimal("1.2"))
    assert logged and wallet.spent == sum(c.usd for c in logged)          # every reservation settled at its call
    running = Decimal(0)
    for r in wallet.rows:                                                  # at every reserve, open bounds included
        if "settle" not in r:
            running += Decimal(r["usd"])
        else:
            running += Decimal(r["usd"]) - Decimal(wallet.rows[r["settle"]]["usd"])
        assert running <= Decimal("1.2")


def test_a_later_reservation_after_a_stop_is_refused():
    from arena.transports import Instrument
    w = RUN.Budget(Decimal("10"))
    inst = Instrument("grader", "m", Decimal("0.01"), None)
    w.reserve(inst)
    w.stop()
    with pytest.raises(RUN.Stopped):
        w.reserve(inst)


def test_the_counts_do_not_depend_on_the_order_the_records_were_written(tmp_path):
    owner = real(tmp_path)
    stage(tmp_path, owner, "pilot-calibration", Scripted())
    first = json.loads((tmp_path / "run" / "calibration_counts.json").read_text())["sha256"]
    path = tmp_path / "run" / "records.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[::-1]) + "\n")                        # as if the calls had finished backwards
    stage(tmp_path, owner, "pilot-calibration", Scripted())
    assert json.loads((tmp_path / "run" / "calibration_counts.json").read_text())["sha256"] == first


def test_four_workers_build_the_same_counts_as_one(tmp_path):
    one, four = tmp_path / "one", tmp_path / "four"
    one.mkdir(), four.mkdir()
    stage(one, real(one), "pilot-calibration", Scripted())
    stage(four, real(four), "pilot-calibration", Scripted(), call_workers=4)
    digest = lambda d: json.loads((d / "run" / "calibration_counts.json").read_text())["sha256"]
    assert digest(one) == digest(four)
    assert len(RUN.spent(one / "run")) == len(RUN.spent(four / "run"))
