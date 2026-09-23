"""The stage packs for one question, generated from the fitted document, never edited (rule 3); the exact joint
decision as an oracle; and wald's play of the packs, which is the only place an act of wald's is chosen.

Stage 1, per (bucket b, prices): Ω = (g1, k); prior P(g1|b)·P(k|g1,b); acts `answer_primary`, `abstain`, and, when
a second opinion is on offer, `consult_second`, worth V2(g1) − c; `agreement` reveals k (a point kernel).
Stage 2, per (b, s, k if already seen, prices): Ω = (g1, g2, k), prior ∝ the joint table at s; acts
`answer_primary`, `answer_second`, `abstain`; `agreement` as before.

V2(g1) is the value, given the true g1, of entering stage 2 without k. It is exact on the path that consults
first; on the path that buys agreement and then consults, stage 2 knows k and V2 does not, which is the J1
approximation whose regret against the exact joint decision the oracle measures.
"""
import hashlib
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import wald

from showcases.omniscience.fit import G, K, S, joint

KS = tuple(f"k{k}" for k in K)
TERMINAL1 = ("answer_primary", "abstain", "consult_second")
TERMINAL2 = ("answer_primary", "answer_second", "abstain")


@dataclass(frozen=True)
class Prices:
    "In utility, where a right answer is 1. consult None: no second opinion on offer."
    p: Fraction
    agreement: Fraction
    consult: Fraction | None


def u(g: str, p: Fraction) -> Fraction:
    return {"right": Fraction(1), "zero": Fraction(0), "wrong": -p}[g]


def u2(act: str, g1: str, g2: str, p: Fraction) -> Fraction:
    return {"answer_primary": u(g1, p), "answer_second": u(g2, p), "abstain": Fraction(0)}[act]


def num(x: Fraction) -> str:
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


# ---------------------------------------------------------------- the model (generator and oracle only)

class Model:
    def __init__(self, f, b: str):
        self.f, self.b = f, b

    def p1(self, g1, k) -> Fraction:
        return self.f["g1"][self.b][g1] * self.f["k"][(self.b, g1)][k]

    def p2(self, g1, k, s, g2) -> Fraction:
        return joint(self.f, self.b, g1, k, s, g2)

    def stage2_states(self, s, known_k):
        "{(g1, g2, k): weight} at s, restricted to known_k when agreement was already bought; normalised."
        w = {(g1, g2, k): self.p2(g1, k, s, g2) for g1 in G for g2 in G for k in K
             if known_k is None or k == known_k}
        z = sum(w.values())
        return {x: v / z for x, v in w.items()}

    def stage2_policy(self, s, known_k, pr: Prices):
        """The optimal stage-2 policy: (value, realised(g1, g2, k)). Ties go to the earlier act in TERMINAL2."""
        st = self.stage2_states(s, known_k)

        def best(states):
            z = sum(states.values())
            return max(TERMINAL2, key=lambda a: (sum(w * u2(a, g1, g2, pr.p) for (g1, g2, _), w in states.items()) / z,
                                                 -TERMINAL2.index(a)))

        def ev(a, states):
            z = sum(states.values())
            return sum(w * u2(a, g1, g2, pr.p) for (g1, g2, _), w in states.items()) / z

        now = best(st)
        v_now = ev(now, st)
        if known_k is None:
            by_k = {k: {x: w for x, w in st.items() if x[2] == k} for k in K}
            act_k = {k: best(v) for k, v in by_k.items() if sum(v.values())}
            v_agree = sum(sum(v.values()) * ev(act_k[k], v) for k, v in by_k.items() if sum(v.values())) - pr.agreement
            if v_agree > v_now:
                return v_agree, lambda g1, g2, k: u2(act_k[k], g1, g2, pr.p) - pr.agreement
        return v_now, lambda g1, g2, k: u2(now, g1, g2, pr.p)

    def v2(self, g1: str, pr: Prices) -> Fraction:
        "Stage 2's value given the true g1, entered without k (the consult cell's continuation)."
        z = self.f["g1"][self.b][g1]
        pol = {s: self.stage2_policy(s, None, pr)[1] for s in S}
        return sum(self.p2(g1, k, s, g2) * pol[s](g1, g2, k) for k in K for s in S for g2 in G) / z

    def exact(self, pr: Prices) -> Fraction:
        "The oracle: the best expected utility over every order of the two observations."
        def terminal(ws):
            z = sum(ws.values())
            return max(Fraction(0), sum(w * u(g1, pr.p) for (g1, _), w in ws.items()) / z)

        def consult(known_k):
            if pr.consult is None:
                return None
            tot = sum(self.p2(g1, k, s, g2) for g1 in G for k in K for s in S for g2 in G
                      if known_k is None or k == known_k)
            return sum(sum(self.p2(g1, k, s, g2) for g1 in G for k in K for g2 in G
                           if known_k is None or k == known_k) / tot * self.stage2_policy(s, known_k, pr)[0]
                       for s in S) - pr.consult

        prior = {(g1, k): self.p1(g1, k) for g1 in G for k in K}
        root = max(v for v in (terminal(prior), consult(None)) if v is not None)
        after = Fraction(0)
        for k in K:
            ws = {x: w for x, w in prior.items() if x[1] == k}
            after += sum(ws.values()) * max(v for v in (terminal(ws), consult(k)) if v is not None)
        return max(root, after - pr.agreement)


# ---------------------------------------------------------------- pack text

def _prior(states: dict) -> str:
    return "{" + ", ".join(f"({', '.join(repr(c) for c in x)}): {num(w)}" for x, w in states.items()) + "}"


def _by(component: str, cells: dict) -> str:
    return f'by("{component}", {{' + ", ".join(f'"{k}": {num(v)}' for k, v in cells.items()) + "})"


def _pack(name, provenance, space, prior, utility, util_source, pr: Prices, price_source) -> str:
    return "\n".join([
        f"# {name}: generated by showcases/omniscience/packs.py from {provenance} -- regenerate, do not edit.",
        f'world("{name}", closed=True)',
        'horizon(1, source="elicited")',
        'depth(1, source="elicited")',
        "space({" + ", ".join(f'"{c}": {list(v)!r}' for c, v in space.items()) + "})",
        f'prior({_prior(prior)}, source="fitted")',
        "utility({" + ", ".join(f'"{a}": {t}' for a, t in utility.items()) + f'}}, source="{util_source}")',
        f'price({{"agreement": {num(pr.agreement)}}}, source="{price_source}")',
        'act("agreement", once=True, kernel=point("k"), reads=["k"])', ""])


def stage1_text(m: Model, pr: Prices, provenance: str, price_source: str) -> str:
    prior = {(g1, f"k{k}"): m.p1(g1, k) for g1 in G for k in K}
    util = {"answer_primary": _by("g1", {g: u(g, pr.p) for g in G}), "abstain": _by("g1", {g: 0 for g in G})}
    if pr.consult is not None:
        util["consult_second"] = _by("g1", {g: m.v2(g, pr) - pr.consult for g in G})
    return _pack(f"omni_s1_{m.b}", provenance, {"g1": G, "k": KS}, prior, util,
                 "fitted" if pr.consult is not None else "elicited", pr, price_source)


def stage2_text(m: Model, s: str, known_k, pr: Prices, provenance: str, price_source: str) -> str:
    prior = {(g1, g2, f"k{k}"): w for (g1, g2, k), w in m.stage2_states(s, known_k).items()}
    util = {"answer_primary": _by("g1", {g: u(g, pr.p) for g in G}),
            "answer_second": _by("g2", {g: u(g, pr.p) for g in G}),
            "abstain": _by("g1", {g: 0 for g in G})}
    return _pack(f"omni_s2_{m.b}_{s}_{'k' + str(known_k) if known_k is not None else 'kunseen'}", provenance,
                 {"g1": G, "g2": G, "k": KS}, prior, util, "elicited", pr, price_source)


def declare(text: str, data_dir: Path):
    return wald.declare(wald.load_pack(text, str(data_dir)))


# ---------------------------------------------------------------- wald plays

class Recorded(wald.Door):
    "Serves what was recorded for the question; fires by remembering. No API call is made from here."
    def __init__(self, k: int):
        self.k, self.fired = k, []

    def outcome(self, act):
        return f"k{self.k}"

    def fire(self, act):
        self.fired.append(act)


@dataclass(frozen=True)
class Path_:
    submitted: str      # "primary", "second" or "abstain"
    agreement: bool
    consulted: bool


class Board:
    """The generated packs for one fitted document and one price point, declared once and played by wald."""
    def __init__(self, f, buckets, pr: Prices, provenance: str, price_source: str, out: Path | None = None):
        self.f, self.pr, self.prov, self.src, self.out = f, pr, provenance, price_source, out
        self.models = {b: Model(f, b) for b in buckets}
        self._worlds = {}

    def _world(self, key, text):
        if key not in self._worlds:
            if self.out:
                self.out.mkdir(parents=True, exist_ok=True)
                (self.out / f"{'_'.join(map(str, key))}.py").write_text(text)
            self._worlds[key] = declare(text, self.out or Path("."))
        return self._worlds[key]

    def stage1(self, b):
        return self._world(("s1", b), stage1_text(self.models[b], self.pr, self.prov, self.src))

    def stage2(self, b, s, known_k):
        return self._world(("s2", b, s, known_k), stage2_text(self.models[b], s, known_k, self.pr, self.prov, self.src))

    @lru_cache(maxsize=None)
    def play(self, b: str, k: int, s: str) -> Path_:
        "wald's acts on a question whose samples matched k times and whose second opinion was s."
        r1 = wald.run(self.stage1(b), Recorded(k))
        if r1.status != "TERMINAL":
            raise RuntimeError(f"stage 1 ended {r1.status}")
        agreed = "agreement" in r1.acts
        if r1.acts[-1] != "consult_second":
            return Path_({"answer_primary": "primary", "abstain": "abstain"}[r1.acts[-1]], agreed, False)
        r2 = wald.run(self.stage2(b, s, k if agreed else None), Recorded(k))
        if r2.status != "TERMINAL":
            raise RuntimeError(f"stage 2 ended {r2.status}")
        return Path_({"answer_primary": "primary", "answer_second": "second", "abstain": "abstain"}[r2.acts[-1]],
                     agreed or "agreement" in r2.acts, True)

    def realised(self, path: Path_, g1: str, g2: str) -> Fraction:
        answer = {"primary": u(g1, self.pr.p), "second": u(g2, self.pr.p), "abstain": Fraction(0)}[path.submitted]
        return answer - self.pr.agreement * path.agreement - (self.pr.consult or 0) * path.consulted

    def expected(self, b: str) -> Fraction:
        "wald's policy under the fitted model: the J2 comparison's 'wald' column."
        m = self.models[b]
        return sum(m.p2(g1, k, s, g2) * self.realised(self.play(b, k, s), g1, g2)
                   for g1 in G for k in K for s in S for g2 in G)


def provenance(doc_bytes: bytes) -> str:
    return f"fitted.json sha256 {hashlib.sha256(doc_bytes).hexdigest()[:16]}"
