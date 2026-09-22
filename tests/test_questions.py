import json
import random

import pytest

from data.questions import QuestionSetError, draw_game, load, parse, split
from oracle.game import tiers_by_fives
from tests.conftest import as_record, make_questions


def test_load_round_trips(question_file, questions):
    assert load(question_file) == tuple(questions)


@pytest.mark.parametrize("breakage", [
    lambda r: r.pop("answer"),
    lambda r: r.update(answer="E"),
    lambda r: r.update(tier="impossible"),
    lambda r: r["options"].pop("D"),
    lambda r: r["options"].update(E="extra"),
    lambda r: r["options"].update(A=""),
    lambda r: r.update(id=""),
])
def test_malformed_questions_are_errors(breakage):
    r = as_record(make_questions(1)[0])
    breakage(r)
    with pytest.raises(QuestionSetError):
        parse(r)


def test_duplicate_ids_are_errors(tmp_path):
    q = as_record(make_questions(1)[0])
    p = tmp_path / "dup.jsonl"
    p.write_text(json.dumps(q) + "\n" + json.dumps(q) + "\n")
    with pytest.raises(QuestionSetError, match="duplicate"):
        load(p)


def test_split_sizes_disjoint_and_deterministic(questions):
    s = split(questions, seed=7, per_tier=200, held_out_per_tier=100)
    assert len(s.calibration) == 600 and len(s.held_out) == 300 and len(s.play) == 60
    ids = [q.id for q in s.calibration + s.held_out + s.play]
    assert len(ids) == len(set(ids)) == len(questions)
    for part, n in ((s.calibration, 200), (s.held_out, 100), (s.play, 20)):
        assert all(sum(q.tier == t for q in part) == n for t in range(3))
    assert split(list(reversed(questions)), seed=7, per_tier=200, held_out_per_tier=100) == s
    assert split(questions, seed=8, per_tier=200, held_out_per_tier=100) != s


def test_split_refuses_a_tier_too_small():
    with pytest.raises(QuestionSetError, match="calibration needs"):
        split(make_questions(250), seed=0, per_tier=200, held_out_per_tier=100)


def test_draw_game_matches_tiers_without_repeats(questions):
    play = split(questions, seed=7, per_tier=200, held_out_per_tier=100).play
    tiers = tiers_by_fives(15)
    game = draw_game(play, tiers, random.Random(1))
    assert [q.tier for q in game] == list(tiers)
    assert len({q.id for q in game}) == 15
    assert draw_game(play, tiers, random.Random(1)) == game
