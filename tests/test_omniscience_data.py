from decimal import Decimal

import pytest

from arena.transports import Instrument, Reply
from showcases.omniscience import grader as GR
from showcases.omniscience import observe as OBS
from showcases.omniscience import questions as QS
from tests.omniscience_fakes import questions


def test_the_pinned_public_set_loads():
    qs = QS.load()
    assert len(qs) == 600 and len(QS.domains(qs)) == 6
    assert all(sum(q.domain == d for q in qs) == 100 for d in QS.domains(qs))


def test_a_changed_file_is_refused(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes(QS.CSV.read_bytes() + b"\n")
    with pytest.raises(QS.QuestionSetError, match="sha256"):
        QS.load(p)


def test_draw_and_split_are_stratified_and_seeded():
    qs = questions(6)
    drawn = QS.draw(qs, 4, seed=1)
    assert drawn == QS.draw(qs, 4, seed=1) and len(drawn) == 24
    cal, test = QS.split(drawn, 2, seed=7)
    assert len(cal) == len(test) == 12 and not {q.id for q in cal} & {q.id for q in test}
    assert all(sum(q.domain == d for q in cal) == 2 for d in QS.domains(qs))


@pytest.mark.parametrize("a,b,same", [("Paris", "paris.", True), ("The Beatles", "Beatles", True),
                                      ("Paris", "Paris, France", False), ("1.5.0", "1.5", False)])
def test_matching_is_normalised_exact(a, b, same):
    assert OBS.matches(a, b) is same


@pytest.mark.parametrize("text,conf", [("85", 85), (" 100 ", 100), ("7%", 7), ("101", None), ("about 80", None),
                                       ("", None), ("15\n\nI'm very uncertain", 15), ("\n92\nbecause", 92),
                                       ("I need to give a score\n40", None)])
def test_confidence_is_parsed_strictly(text, conf):
    assert OBS.parse_confidence(text) == conf


def test_buckets():
    cuts = (50, 80, 95)
    assert [OBS.bucket_of(c, cuts) for c in (0, 49, 50, 94, 95, 100, None)] == \
           ["b0", "b0", "b1", "b2", "b3", "b3", "unread"]


def test_one_question_is_observed_once_and_every_call_logged_at_its_price():
    q = questions(1)[0]
    replies = iter(["Oslo", "72", "Oslo", "oslo.", "Bergen", "Oslo", "Oslo", "Bergen"])
    prim = Instrument("primary", "m1", Decimal("0.001"), lambda s, u: Reply(next(replies), 50, 2))
    sec = Instrument("second", "m2", Decimal("0.002"), lambda s, u: Reply(next(replies), 50, 2))
    reserved = []
    seen = OBS.observe(prim, sec, q, 3, 5, reserved.append)
    assert (seen.read, seen.confidence, seen.k, seen.second, seen.s) == ("Oslo", 72, 4, "Bergen", "different")
    assert [c.instrument for c in seen.calls] == ["primary", "primary.confidence"] + ["primary.sample"] * 5 + ["second"]
    assert [c.usd for c in seen.calls] == [Decimal("0.001")] * 7 + [Decimal("0.002")]
    assert all(c.question_id == q.id and c.tier == 3 for c in seen.calls) and len(reserved) == 8


def test_grading_runs_once_per_distinct_answer_and_is_shared(tmp_path):
    q = questions(1)[0]
    n = []
    inst = Instrument("grader", "g", Decimal("0.003"), lambda s, u: n.append(u) or Reply("C", 900, 1))
    g = GR.Grader(inst, tmp_path / "grades.jsonl")
    assert g(q, "Oslo") == g(q, "Oslo") == "PARTIAL_ANSWER" and len(n) == 1
    assert "Gold target: " + q.answer in n[0] and "Predicted answer: Oslo" in n[0]
    again = GR.Grader(inst, tmp_path / "grades.jsonl")
    assert again(q, "Oslo") == "PARTIAL_ANSWER" and len(n) == 1
    assert [c.usd for c in GR.calls(tmp_path / "grades.jsonl")] == [Decimal("0.003")]


@pytest.mark.parametrize("text,grade", [("A", "CORRECT"), (' "D" ', "NOT_ATTEMPTED"), ("B.", "UNGRADED"),
                                        ("The answer is A", "UNGRADED")])
def test_grades_are_parsed_strictly(text, grade):
    assert GR.parse_grade(text) == grade


def test_the_grader_prompt_is_aas_verbatim():
    assert GR.TEMPLATE.startswith("Your job is to look at a question, a gold target, and a predicted answer")
    assert GR.TEMPLATE.rstrip().endswith('Just return the letters "A", "B", "C", or "D", with no text around it.')
    assert GR.TEMPLATE.count("{predicted_answer}") == 1
