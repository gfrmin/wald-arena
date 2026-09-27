import re
import sys
from fractions import Fraction as F

import pytest
import wald

from showcases.omniscience import board as B
from showcases.omniscience import world as W

BUCKETS = ("b0", "b1", "unread")
GRIDS = W.Grids((F(1, 10), F(7, 10)), ((F(4, 5), F(1, 5)),), ((F(1, 2), F(4, 5), F(1, 5)),), (F(9, 10), F(1)))
PR = W.Prices(F(3), F(1, 100), F(1, 10), F(1, 500))


def row(b="b1", k=5, s="same", grade1="CORRECT", grade2="CORRECT", qid="q"):
    return dict(question_id=qid, b=b, k=k, s=s, grade1=grade1, grade2=grade2)


def calibrated(n=12):
    "A plate over questions whose read is right in b1 and wrong in b0; its Counts."
    _, world = W.declare(W.text(BUCKETS, GRIDS, W.Prices(F(1), F(0), F(0), F(1, 500)), "cal"))
    rows = [row("b1", 5, "same", "CORRECT", "CORRECT", f"r{i}") for i in range(n)] + \
           [row("b0", 1, "different", "INCORRECT", "CORRECT", f"w{i}") for i in range(n)]
    plate, _ = B.play_plate(world, rows, 5)
    return plate.counts()


def test_the_pack_is_lawful_and_says_what_is_learned():
    spec, world = W.declare(W.text(BUCKETS, GRIDS, PR, "t"))
    assert [name for name, _ in spec["globals"]] == list(W.GLOBALS)
    assert len(spec["prior_global"]) == 2 ** len(BUCKETS) * 2
    assert spec["after"]["name"] == "grade" and spec["after"]["price"] == F(1, 500)
    assert "no class" in str(wald.plate(world).disclosure())


def test_no_utility_reads_a_global():
    spec, _ = W.declare(W.text(BUCKETS, GRIDS, PR, "t"))
    for u in spec["T"].values():
        by_local = {}
        for (l, g), v in u.items():
            by_local.setdefault(l, set()).add(v)
        assert all(len(v) == 1 for v in by_local.values())


def test_the_door_grades_the_submitted_answer_and_the_read_on_abstention():
    d = B.RecordedDoor(row(grade1="INCORRECT", grade2="CORRECT"), 5)
    d.fire("answer_second")
    assert d.outcome("grade") == "right"
    d.fire("abstain")
    assert d.outcome("grade") == "not"
    assert d.outcome("agreement") == "all" and B.RecordedDoor(row(k=4), 5).outcome("agreement") == "some"


def test_shipped_counts_carry_walds_digest_and_score_and_wald_recomputes_them():
    counts = calibrated()
    pack = W.text(BUCKETS, GRIDS, PR, "t", counts)
    _, bare = W.declare(W.text(BUCKETS, GRIDS, PR, "t"))
    assert f'sha256="{wald.digest(counts)}"' in pack and f"score({wald.score(bare, counts)}," in pack
    W.declare(pack)
    bump = lambda m: f"score({m.group(1)[:-1]}{(int(m.group(1)[-1]) + 1) % 10}/"     # the numerator's last digit
    wrong_score = re.sub(r"score\((\d+)/", bump, pack)
    with pytest.raises(wald.refusals.Refused) as e:
        W.declare(wrong_score)
    assert e.value.name == "UNSCORED"
    wrong_digest = re.sub(r'sha256="[0-9a-f]{64}"', 'sha256="' + "0" * 64 + '"', pack)
    with pytest.raises(wald.refusals.Refused) as e:
        W.declare(wrong_digest)
    assert e.value.name == "PLATE"


def test_a_shipped_calibration_changes_what_wald_does():
    counts = calibrated()
    _, bare = W.declare(W.text(BUCKETS, GRIDS, PR, "t"))
    _, shipped = W.declare(W.text(BUCKETS, GRIDS, PR, "t", counts))
    door = lambda: B.RecordedDoor(row("b0", 1, "different", "INCORRECT", "INCORRECT"), 5)
    assert wald.plate(bare).run(door()).acts != wald.plate(shipped).run(door()).acts


def test_e7_has_a_line_for_every_draw_and_a_blind_switch_is_marked():
    counts = calibrated(6)
    _, world = W.declare(W.text(BUCKETS, GRIDS, PR, "t"))
    lines = str(wald.e7(world, counts)).splitlines()
    histories = {(draws[:j], draws[j][0]) for draws, _, _ in counts for j in range(len(draws))} | \
                {(draws, end) for draws, end, after in counts if after is not None}
    assert lines[0].startswith("E7:") and len(lines) - 1 == len(histories)
    assert all(0 <= F(line.rsplit(" ", 1)[1]) <= 1 for line in lines[1:])

    class R:
        acts = ("answer_second",)
    assert B.played(R()) == B.Played("second", False, True, True)
    R.acts = ("second_opinion", "answer_second")
    assert B.played(R()) == B.Played("second", False, True, False)


def test_the_threshold_is_a_baseline_on_calibration_counts():
    cal = [dict(b="b1", g1="right")] * 8 + [dict(b="b0", g1="wrong")] * 8
    rates = B.bucket_rates(cal, BUCKETS)
    assert rates["b1"]["right"] == F(9, 11) and rates["unread"]["right"] == F(1, 3)
    assert B.threshold(dict(b="b1"), rates, F(1)).submitted == "primary"
    assert B.threshold(dict(b="b0"), rates, F(1)).submitted == "abstain"


def test_a_long_score_is_written_and_read_without_lifting_the_process_digit_limit():
    limit = sys.get_int_max_str_digits()
    counts = calibrated(40)
    _, bare = W.declare(W.text(BUCKETS, GRIDS, PR, "t"))
    assert len(wald.score(bare, counts)) > limit
    W.declare(W.text(BUCKETS, GRIDS, PR, "t", counts))
    assert sys.get_int_max_str_digits() == limit
