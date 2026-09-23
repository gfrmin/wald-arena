import random
from fractions import Fraction as F

import pytest

from showcases.omniscience import fit as FIT
from showcases.omniscience import packs as P

BUCKETS = ("b0", "b1", "unread")


def rows(n=400, seed=0, correlated=True, second_acc=0.6):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        b = rng.choice(BUCKETS[:2])
        g1 = "right" if rng.random() < (0.35 if b == "b0" else 0.85) else "wrong"
        k = sum(rng.random() < (0.9 if g1 == "right" else 0.3) for _ in range(5))
        if correlated:
            g2 = g1 if rng.random() < 0.9 else ("right" if g1 == "wrong" else "wrong")
        else:
            g2 = "right" if rng.random() < second_acc else "wrong"
        s = "same" if g1 == g2 == "right" or (g1 == g2 and rng.random() < 0.2) else "different"
        out.append(dict(b=b, g1=g1, k=k, s=s, g2=g2))
    return out


def test_the_fit_is_the_chain_rule_and_every_cell_exact():
    f = FIT.fit(rows(), BUCKETS, 10)
    total = sum(FIT.joint(f, "b1", g1, k, s, g2) for g1 in FIT.G for k in FIT.K for s in FIT.S for g2 in FIT.G)
    assert total == 1 and all(isinstance(v, F) for v in f["g1"]["b1"].values())
    doc = FIT.document(f, {}, {})
    assert FIT.from_document(doc)["sg2"] == f["sg2"]


def test_the_second_opinion_is_fitted_jointly_never_by_its_own_accuracy():
    "Two opinions that are right together: the joint kernel sees it; the second's own accuracy cannot."
    data = rows(correlated=True)
    f = FIT.fit(data, BUCKETS, 10)
    p_right_given_right = sum(f["sg2"][("b1", "right", 2)][(s, "right")] for s in FIT.S)
    p_right_given_wrong = sum(f["sg2"][("b1", "wrong", 0)][(s, "right")] for s in FIT.S)
    assert p_right_given_right > F(4, 5) and p_right_given_wrong < F(1, 4)
    h = FIT.held_out(data, BUCKETS, 10, 5, 1)
    assert h["joint"] > h["independent_second"] > h["uniform"]


def test_thin_slices_back_off_and_say_so():
    f = FIT.fit(rows(40), BUCKETS, 10)
    assert "P(g1|unread) -> *" in f["backed_off"]
    assert f["g1"]["unread"] == FIT.dirichlet1_mean({g: sum(r["g1"] == g for r in rows(40)) for g in FIT.G})


@pytest.mark.parametrize("p,c", [(F(1), None), (F(3), F(1, 2)), (F(10), F(0))])
def test_generated_packs_are_lawful_and_the_oracle_bounds_wald(p, c):
    f = FIT.fit(rows(), BUCKETS, 10)
    board = P.Board(f, BUCKETS, P.Prices(p, F(1, 100), c), "test", "elicited")
    for b in BUCKETS:
        text = P.stage1_text(board.models[b], board.pr, "test", "elicited")
        assert ("consult_second" in text) is (c is not None)
        board.stage1(b)
        assert board.models[b].exact(board.pr) >= board.expected(b)


def test_wald_switches_to_the_second_answer_when_the_world_says_so():
    "A free second opinion that is usually right whatever the read: after a disagreement wald answers second."
    f = FIT.fit(rows(correlated=False, second_acc=0.9), BUCKETS, 10)
    board = P.Board(f, BUCKETS, P.Prices(F(3), F(1, 100), F(0)), "test", "elicited")
    paths = {(k, s): board.play("b0", k, s) for k in FIT.K for s in FIT.S}
    assert any(pa.submitted == "second" and pa.consulted for pa in paths.values())
    assert all(pa.submitted != "second" or pa.consulted for pa in paths.values())


def test_without_a_second_opinion_wald_never_consults():
    f = FIT.fit(rows(), BUCKETS, 10)
    board = P.Board(f, BUCKETS, P.Prices(F(1), F(1, 100), None), "test", "elicited")
    assert not any(board.play(b, k, s).consulted for b in BUCKETS for k in FIT.K for s in FIT.S)
