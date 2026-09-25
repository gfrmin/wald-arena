"""The kit's reference evaluators for CHARTER v0.2, which every board that learns across episodes reads the same way.

wald 0.2.0's public names give S15's disclosure (`Plate.disclosure()`) but not E7's lines or the Score of Counts a
host ships; `wald.counts` has both and is not a host's to call (wald's API.md). So both come from the kit's reference,
`laws/counts_check.py` of gfrmin/wald-charter at the kit tag `wald.law` names, fetched and verified against
`arena/allowed_signers` by `sh arena/fetch_kit.sh`. wald recomputes the Score and the digest at declaration and
refuses a pack whose numbers differ, so what this module writes into a pack is checked by a second implementation.

`W` is the dict `wald.load_pack` returns for a SURFACE v0.2 pack; Counts are a `Counter` of wald's records,
(((act, outcome), ...), end, after-report).

A Score is an exact rational with tens of thousands of digits, past Python's default limit of 4,300 for integer
literals, so importing this module lifts that limit (QUESTIONS.md 2.23).
"""
import importlib.util
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import wald

sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
LAWS = HERE / "charter" / "laws"


class KitMissing(RuntimeError):
    pass


def _lock() -> dict:
    return dict(line.split("=", 1) for line in (HERE / "kit.lock").read_text().split()
                if "=" in line and not line.startswith("#"))


def _load():
    tag = _lock()["TAG"]
    if tag != wald.law["kit"]:
        raise KitMissing(f"arena/kit.lock names {tag}, but the pinned wald was judged under {wald.law['kit']}")
    if not (LAWS / "counts_check.py").exists():
        raise KitMissing("the kit is not fetched: run `sh arena/fetch_kit.sh`")
    git = lambda *a: subprocess.run(["git", "-C", str(LAWS.parent), *a], capture_output=True, text=True).stdout.strip()
    if git("rev-parse", "HEAD") != _lock()["SHA"] or git("status", "--porcelain", "--", "laws"):
        raise KitMissing(f"arena/charter is not the clean checkout of {tag} at {_lock()['SHA']}: "
                         "run `sh arena/fetch_kit.sh`")
    sys.path.insert(0, str(LAWS))
    spec = importlib.util.spec_from_file_location("counts_check", LAWS / "counts_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CC = None


def cc():
    global _CC
    if _CC is None:
        _CC = _load()
    return _CC


def digest(counts: Counter, falsifiers=()) -> str:
    "V2.13's digest of shipped Counts."
    return cc().counts_sha(counts, falsifiers)


def score(W: dict, counts: Counter, falsifiers=()) -> Fraction:
    "C2.S14 / V2.8: the leave-one-out predictive probability of the shipped records."
    return cc().loo_score(W, counts, falsifiers)


def e7(W: dict, counts: Counter) -> dict:
    """E7's lines: {(history, act, end): total variation}, for every draw in Counts, grouped by the history within its
    episode that led to it. `act` is the kit's `<after>` for an after-report, whose `end` is the terminal fired."""
    return cc().diagnostic(W, counts)


AFTER = "<after>"


def e7_sizes(counts: Counter) -> Counter:
    "How many draws each of E7's lines groups, keyed as `e7` keys them."
    n = Counter()
    for (draws, end, after), k in counts.items():
        seq = list(draws) + ([(AFTER, after)] if after is not None else [])
        for j, (act, _) in enumerate(seq):
            n[(tuple(seq[:j]), act, end if act == AFTER else None)] += k
    return n


def posterior_global(W: dict, counts: Counter) -> dict:
    "P(Global | Counts), for display beside the result; nothing that decides reads it."
    return cc().post_global(W, counts)


def marginals(W: dict, counts: Counter) -> dict:
    "{component: {value: P}} of P(Global | Counts), for display."
    names = [name for name, _ in W["globals"]]
    out = {name: {} for name in names}
    for g, p in posterior_global(W, counts).items():
        for name, v in zip(names, g):
            out[name][v] = out[name].get(v, Fraction(0)) + p
    return out
