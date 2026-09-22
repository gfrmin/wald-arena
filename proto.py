"""WWTBAM as a wald World per question, with lifelines priced by option value; and the exact game DP as the oracle.
Ladder (US 2020s-style, 15 rungs), safe havens after Q5 and Q10.  Instruments: the contestant's own LLM read at
reliability rho_t per tier, 50:50 (exact), phone (rho_p), audience (rho_a).  Utilities in $ (thousands)."""
import sys; sys.path.insert(0, '/home/claude/repos/wald-charter-master/laws')
from fractions import Fraction as F
from functools import lru_cache
import spec_check as S, meta_check as M
LADDER = [F(x) for x in (0.5,1,2,3,5, 7,10,20,30,50, 100,250,500,1000,10000)]   # $k after answering rung i (0-based)... scaled: 10000 = $1M
SAFE = lambda r: F(0) if r < 5 else (LADDER[4] if r < 10 else LADDER[9])            # what a wrong answer at rung r keeps
TIER = lambda r: min(r // 5, 2)                                                       # 0 easy, 1 medium, 2 hard
OPTS = ("A", "B", "C", "D")
def noisy(rho):
    "a report names the truth with rho, else one of the three wrong options uniformly"
    return {w: {o: (rho if o == w else (1 - rho) / 3) for o in OPTS} for w in OPTS}
def fifty():
    "keeps the truth and one wrong option, uniformly: outcome is the unordered pair"
    K = {}
    for w in OPTS:
        K[w] = {}
        for x in OPTS:
            if x != w: K[w]["".join(sorted(w + x))] = F(1, 3)
    return K
def stage_world(r, life, rho, rho_p, rho_a, c_llm, V_next):
    """the per-question World at rung r with lifelines `life` still held.  Terminal acts: answer X, walk.
    u(w, answer X) = V_next(life) if X == w else SAFE(r);  u(w, walk) = LADDER[r-1] (0 at r = 0).
    Lifeline prices are option values: V_next(life) - V_next(life - {l})  [J: an approximation, measured below]."""
    t = TIER(r); walk = LADDER[r - 1] if r > 0 else F(0)
    T = {f"answer {x}": {w: (V_next(life) if x == w else SAFE(r)) for w in OPTS} for x in OPTS}
    T["walk"] = {w: walk for w in OPTS}
    O = {"llm": {"K": noisy(rho[t]), "price": c_llm, "once": True, "ends": {}}}
    for l, K in (("fifty", fifty()), ("phone", noisy(rho_p[t])), ("audience", noisy(rho_a[t]))):
        if l in life:
            O[l] = {"K": K, "price": V_next(life) - V_next(life - {l}), "once": True, "ends": {}}
    return {"prior": {w: F(1, 4) for w in OPTS}, "T": T, "O": O, "N": 4, "d": 4}
def solve_game(rho, rho_p, rho_a, c_llm):
    "V(r, life): expected $k from rung r with lifelines `life`, under the per-question wald policy (exact within a stage)"
    @lru_cache(None)
    def V(r, life):
        if r == 15: return LADDER[14]
        nxt = lambda L: V(r + 1, L)
        w = stage_world(r, life, rho, rho_p, rho_a, c_llm, nxt)
        return S.REF.solve(w["prior"], w, w["N"])[0]
    return V, lambda r, life: stage_world(r, life, rho, rho_p, rho_a, c_llm, lambda L: V(r + 1, L))
if __name__ == "__main__":
    rho = {0: F(95, 100), 1: F(80, 100), 2: F(60, 100)}; rho_p = {0: F(9, 10), 1: F(7, 10), 2: F(5, 10)}; rho_a = {0: F(9, 10), 1: F(75, 100), 2: F(45, 100)}
    c_llm = F(1, 1000)   # $1 per LLM read, in $k
    V, world = solve_game(rho, rho_p, rho_a, c_llm)
    full = frozenset({"fifty", "phone", "audience"})
    print("expected winnings from the start, all lifelines: $%.1fk" % float(V(0, full)))
    for r in (0, 4, 5, 9, 10, 12, 14):
        w = world(r, full); b = w["prior"]; v, a = S.REF.solve(b, w, w["N"])
        print(f"  rung {r+1:2d} (tier {TIER(r)}): value ${float(v):8.1f}k  first act {a!r}  lifeline prices " + ", ".join(f"{l}={float(w['O'][l]['price']):.1f}" for l in ("fifty","phone","audience")))
    # the always-answer baseline: read the LLM once, answer its report, never walk, never use lifelines
    @lru_cache(None)
    def A(r):
        if r == 15: return LADDER[14]
        t = TIER(r); return rho[t] * A(r + 1) + (1 - rho[t]) * SAFE(r) - c_llm
    print("always-answer baseline: $%.1fk" % float(A(0)))
    # naive lifeline user: same as wald but lifelines free (option value ignored) -- overuses them early
    V0, _ = solve_game(rho, rho_p, rho_a, c_llm)
