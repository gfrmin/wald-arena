"""The joint kernel, fitted on the calibration split. No float leaves this module as a probability.

A question's record, once graded, is (b, g1, k, s, g2): the read's confidence bucket, the grade class of the read,
how many agreement samples matched it, whether the second opinion's answer matched it, and the grade class of the
second answer. The fit is the chain rule, so nothing in it assumes independence:

    P(g1, k, s, g2 | b) = P(g1 | b) · P(k | g1, b) · P(s, g2 | g1, kbin(k), b)

Each factor is a Dirichlet(1) mean of counts (`arena.calibration`). A conditioning slice with fewer than `min_count`
records backs off: the bucket first, then (for the last factor) the k-bin, and each back-off is recorded. The
held-out score is k-fold within calibration, by the shared scorer, beside the score of an "independent second
opinion" contrast, P(g2) · P(s | g1, g2), which is what fitting the second opinion's own accuracy would give (J2).
"""
import random
from fractions import Fraction
from itertools import product
from typing import Iterable, Mapping

from arena.calibration import dirichlet1_mean, held_out_log_score, uniform_log_score

G = ("right", "zero", "wrong")
K = tuple(range(6))
S = ("same", "different")
KBINS = ((0, 1, 2), (3, 4), (5,))
POOLED = "*"


def grade_class(grade: str) -> str:
    "CORRECT scores +1, INCORRECT -p, PARTIAL_ANSWER and NOT_ATTEMPTED 0 (QUESTIONS.md 2.8); an ungraded reply is wrong."
    return {"CORRECT": "right", "PARTIAL_ANSWER": "zero", "NOT_ATTEMPTED": "zero"}.get(grade, "wrong")


def kbin(k: int) -> int:
    return next(i for i, b in enumerate(KBINS) if k in b)


def _fit(rows, buckets, min_count):
    backed_off = []

    def counts(outcomes, key, sel):
        return {o: sum(key(r) == o for r in rows if sel(r)) for o in outcomes}

    def smoothed(name, outcomes, key, levels):
        "levels: [(label, selector)], most specific first; the first with enough records is fitted."
        for i, (label, sel) in enumerate(levels):
            c = counts(outcomes, key, sel)
            if sum(c.values()) >= min_count or i == len(levels) - 1:
                if i:
                    backed_off.append(f"{name} -> {label}")
                return dirichlet1_mean(c)

    p_g1 = {b: smoothed(f"P(g1|{b})", G, lambda r: r["g1"],
                        [(b, lambda r, b=b: r["b"] == b), (POOLED, lambda r: True)]) for b in buckets}
    p_k = {(b, g): smoothed(f"P(k|{g},{b})", K, lambda r: r["k"],
                            [(b, lambda r, b=b, g=g: r["b"] == b and r["g1"] == g),
                             (POOLED, lambda r, g=g: r["g1"] == g)]) for b in buckets for g in G}
    sg = tuple(product(S, G))
    p_sg2 = {(b, g, kb): smoothed(f"P(s,g2|{g},kbin{kb},{b})", sg, lambda r: (r["s"], r["g2"]),
                                  [(b, lambda r, b=b, g=g, kb=kb: r["b"] == b and r["g1"] == g and kbin(r["k"]) == kb),
                                   (f"{POOLED}, kbin{kb}", lambda r, g=g, kb=kb: r["g1"] == g and kbin(r["k"]) == kb),
                                   (f"{POOLED}, any k", lambda r, g=g: r["g1"] == g)])
             for b in buckets for g in G for kb in range(len(KBINS))}
    return {"g1": p_g1, "k": p_k, "sg2": p_sg2, "backed_off": backed_off}


def fit(rows: Iterable[Mapping], buckets: tuple[str, ...], min_count: int) -> dict:
    return _fit(list(rows), buckets, min_count)


def joint(f: Mapping, b: str, g1: str, k: int, s: str, g2: str) -> Fraction:
    return f["g1"][b][g1] * f["k"][(b, g1)][k] * f["sg2"][(b, g1, kbin(k))][(s, g2)]


def _independent(rows):
    "The contrast: the second opinion's own accuracy, and whether it matched given both grades, pooled."
    p_g2 = dirichlet1_mean({g: sum(r["g2"] == g for r in rows) for g in G})
    p_s = {(g1, g2): dirichlet1_mean({s: sum(r["s"] == s for r in rows if r["g1"] == g1 and r["g2"] == g2) for s in S})
           for g1 in G for g2 in G}
    return p_g2, p_s


def held_out(rows: Iterable[Mapping], buckets, min_count: int, folds: int, seed: int) -> dict:
    "k-fold held-out log scores of the joint fit and of the independence contrast, by the shared scorer."
    rows = list(rows)
    order = list(range(len(rows)))
    random.Random(f"folds:{seed}").shuffle(order)
    joint_p, indep_p = [], []
    for i in range(folds):
        held = set(order[i::folds])
        test = [rows[j] for j in sorted(held)]
        train = [rows[j] for j in order if j not in held]
        f = _fit(train, buckets, min_count)
        p_g2, p_s = _independent(train)
        for r in test:
            head = f["g1"][r["b"]][r["g1"]] * f["k"][(r["b"], r["g1"])][r["k"]]
            joint_p.append(head * f["sg2"][(r["b"], r["g1"], kbin(r["k"]))][(r["s"], r["g2"])])
            indep_p.append(head * p_g2[r["g2"]] * p_s[(r["g1"], r["g2"])][r["s"]])
    return {"n": len(rows), "folds": folds, "joint": held_out_log_score(joint_p),
            "independent_second": held_out_log_score(indep_p),
            "uniform": uniform_log_score(len(G) * len(K) * len(S) * len(G))}


def document(f: Mapping, score: Mapping, meta: Mapping) -> dict:
    "The fitted document the pack generator reads: every cell a 'p/q' string, source fitted, with its score."
    q = lambda d: {str(k): str(v) for k, v in d.items()}
    return {"source": "fitted", "method": "chain rule; Dirichlet(1) means of calibration counts", **meta,
            "held_out": score, "backed_off": f["backed_off"],
            "g1": {b: q(v) for b, v in f["g1"].items()},
            "k": {f"{b}|{g}": q(v) for (b, g), v in f["k"].items()},
            "sg2": {f"{b}|{g}|{kb}": {f"{s}|{g2}": str(p) for (s, g2), p in v.items()}
                    for (b, g, kb), v in f["sg2"].items()}}


def from_document(doc: Mapping) -> dict:
    return {"g1": {b: {g: Fraction(p) for g, p in v.items()} for b, v in doc["g1"].items()},
            "k": {tuple(key.split("|")): {int(k): Fraction(p) for k, p in v.items()} for key, v in doc["k"].items()},
            "sg2": {(b, g, int(kb)): {tuple(sg.split("|")): Fraction(p) for sg, p in v.items()}
                    for b, g, kb in (key.split("|") for key in doc["sg2"]) for v in [doc["sg2"][f"{b}|{g}|{kb}"]]},
            "backed_off": doc["backed_off"]}
