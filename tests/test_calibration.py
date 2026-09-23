import json
import math
from decimal import Decimal
from fractions import Fraction as F

import pytest

from explainers.millionaire.calibration import fit as FIT
from explainers.millionaire.calibration import run as RUN
from arena.transports import Instrument, Reply
from explainers.millionaire.calibration.reading import read
from explainers.millionaire.questions import split
from tests.conftest import make_questions

SPLIT = split(make_questions(320), seed=5, per_tier=200, held_out_per_tier=100)


def asker_from(calls):
    "Wrong on every third question, unparseable on every seventh; counts calls."
    def ask(q):
        calls.append(q.id)
        i = int(q.id.split("-")[1])
        reply = "maybe" if i % 7 == 0 else (q.answer if i % 3 else "ABCD"[("ABCD".index(q.answer) + 1) % 4])
        inst = Instrument("llm", "scripted", Decimal("0.002"), lambda s, u: Reply(reply, 40, 1))
        return read(inst, q)
    return ask


def test_run_records_rule5_fields_and_resumes(tmp_path):
    out, calls = tmp_path / "llm.jsonl", []
    rows = RUN.run(SPLIT, 0, asker_from(calls), out)
    assert len(rows) == 300 and len(calls) == 300
    assert {r["slice"] for r in rows} == {"calibration", "held_out"}
    r = rows[0]
    assert {"question_id", "tier", "report", "truth", "right", "model", "input_tokens", "output_tokens", "usd",
            "latency_s"} <= set(r)
    assert RUN.run(SPLIT, 0, asker_from(calls), out) == [] and len(calls) == 300  # resumed: nothing re-paid
    assert len(RUN.read_rows(out)) == 300


def test_dry_run_replays_without_any_api(tmp_path):
    recorded = tmp_path / "llm.jsonl"
    RUN.run(SPLIT, 1, asker_from([]), recorded)
    replayed = tmp_path / "replayed.jsonl"
    RUN.run(SPLIT, 1, RUN.replaying(RUN.read_rows(recorded)), replayed)
    assert RUN.read_rows(replayed) == RUN.read_rows(recorded)
    with pytest.raises(KeyError, match="no recorded reply"):
        RUN.run(SPLIT, 2, RUN.replaying(RUN.read_rows(recorded)), tmp_path / "other.jsonl")


def test_fit_counts_to_exact_beta_posterior_mean_and_held_out_score(tmp_path):
    rows_file = tmp_path / "llm.jsonl"
    RUN.run(SPLIT, 0, asker_from([]), rows_file)
    rows = RUN.read_rows(rows_file)
    (f,) = FIT.fit(rows)
    cal = [r for r in rows if r["slice"] == "calibration"]
    right = sum(r["right"] for r in cal)
    assert (f.right, f.wrong) == (right, 200 - right)
    assert f.rho == F(right + 1, 202) and isinstance(f.rho, F)
    assert any(r["report"] == "?" and not r["right"] for r in rows)  # unparseable counted wrong
    held = [r for r in rows if r["slice"] == "held_out"]
    hr = sum(r["right"] for r in held)
    expect = (hr * math.log(f.rho) + (100 - hr) * math.log((1 - f.rho) / 3)) / 100
    assert f.held_n == 100 and f.log_score == pytest.approx(expect)
    assert f.log_score > FIT.TierFit.UNIFORM  # this scripted model is informative


def test_fitted_file_round_trips_rho_as_fractions(tmp_path):
    rows_file = tmp_path / "llm.jsonl"
    for t in range(3):
        RUN.run(SPLIT, t, asker_from([]), rows_file)
    fits = FIT.fit(RUN.read_rows(rows_file))
    out = tmp_path / "fitted.json"
    out.write_text(json.dumps(FIT.document("llm", fits, rows_file)))
    doc = json.loads(out.read_text())
    assert doc["source"] == "fitted" and all(isinstance(t["rho"], str) for t in doc["tiers"])
    assert FIT.reliability(out) == tuple(f.rho for f in fits)


def test_reliability_refuses_a_missing_tier(tmp_path):
    rows_file = tmp_path / "llm.jsonl"
    RUN.run(SPLIT, 0, asker_from([]), rows_file)
    out = tmp_path / "fitted.json"
    out.write_text(json.dumps(FIT.document("llm", FIT.fit(RUN.read_rows(rows_file)), rows_file)))
    with pytest.raises(ValueError, match="medium"):
        FIT.reliability(out)
