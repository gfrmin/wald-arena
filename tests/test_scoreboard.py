import json
import random
import statistics
from decimal import Decimal
from fractions import Fraction as F

from baselines import always_answer, llm_direct
from calibration.instruments import Instrument, Reply
from data.questions import draw_game
from oracle import play as oracle_play
from oracle.game import exact
from oracle.host import play, simulated_fire
from tests.test_host_and_always_answer import BRIEF, LAM, PLAY, USD
from tools import scoreboard as SB
from tools.play import fire_for, game_questions


def simulate(contestant, name, n, seed, read_first=True):
    rng = random.Random(seed)
    fire = simulated_fire(BRIEF, rng, USD)
    return [play(contestant, name, i, draw_game(PLAY, BRIEF.tiers, rng), BRIEF, fire, read_first) for i in range(n)]


def test_oracle_plays_its_expected_value():
    "Simulated instruments: the oracle's realised mean utility is within 4 standard errors of the exact value."
    logs = simulate(oracle_play.contestant(BRIEF), oracle_play.NAME, 3000, 11)
    u = [float(g.utility(LAM)) for g in logs]
    se = statistics.stdev(u) / len(u) ** 0.5
    assert abs(statistics.mean(u) - float(oracle_play.expected(BRIEF))) < 4 * se
    assert oracle_play.expected(BRIEF) == exact(BRIEF).value(0, frozenset({"fifty", "phone", "audience"}))
    assert any(g.lifeline_rungs for g in logs)


def test_same_questions_and_same_fifty_for_every_contestant():
    assert game_questions(PLAY, BRIEF.tiers, 9, 5) == game_questions(PLAY, BRIEF.tiers, 9, 5)
    q = PLAY[0]
    f1, f2 = fire_for({}, 9, 3), fire_for({}, 9, 3)
    assert [f1("fifty", q, r) for r in range(15)] == [f2("fifty", q, r) for r in range(15)]


def write_root(tmp_path, logs_by_slug):
    (tmp_path / "owner.toml").write_text("""
lambda_usd = "100"
split_seed = 1
[ladder]
prizes = [100, 200, 300, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 125000, 250000, 500000, 1000000]
havens = [5, 10]
[rulings]
read_first = true
fifty_usd = "0"
[games]
per_contestant = 500
seed = 42
[questions]
path = "q.jsonl"
[instruments.llm]
model = "m1"
usd_per_call = "0.01"
[instruments.phone]
model = "m2"
usd_per_call = "0.02"
[instruments.audience]
model = "m3"
usd_per_call = "0.03"
""")
    fitted = tmp_path / "calibration" / "fitted"
    fitted.mkdir(parents=True)
    for k, rho in BRIEF.reliability.items():
        fitted.joinpath(f"{k}.json").write_text(json.dumps({"instrument": k, "tiers": [
            {"tier": t, "right": 1, "wrong": 1, "rho": str(r),
             "held_out": {"n": 100, "right": 60, "wrong": 40, "log_score": -0.9, "uniform_log_score": -1.386}}
            for t, r in zip(("easy", "medium", "hard"), rho)]}))
    (tmp_path / "games").mkdir()
    for slug, logs in logs_by_slug.items():
        (tmp_path / "games" / f"{slug}.jsonl").write_text("".join(json.dumps(g.to_json()) + "\n" for g in logs))


def test_scoreboard_skeleton_prints_not_yet_everywhere(tmp_path):
    (tmp_path / "owner.toml").write_text((SB.ROOT / "owner.toml").read_text())
    md = SB.render(SB.gather(tmp_path), illustrate=False)
    assert "**Not yet played.**" in md and "`lambda_usd`" in md
    assert md.count("| wald | not yet |") == 3  # winnings, walk-away, wrong-answer
    assert "## wald's regret against the exact game (J2)" in md and "not yet: needs" in md


def test_scoreboard_filled_by_the_contestants_that_played(tmp_path):
    oracle_logs = simulate(oracle_play.contestant(BRIEF), oracle_play.NAME, 60, 1)
    always_logs = simulate(always_answer.contestant, always_answer.NAME, 60, 1)
    replies = iter(["use fifty", "answer A", "walk"] * 100)
    inst = Instrument("llm", "m1", Decimal("0.01"), lambda s, u: Reply(next(replies), 10, 1))
    direct_logs = [play(llm_direct.contestant(inst, BRIEF), llm_direct.NAME, i, qs, BRIEF,
                        lambda k, q, r: ("AB", None), read_first=False)
                   for i, qs in enumerate(game_questions(PLAY, BRIEF.tiers, 42, 5))]
    write_root(tmp_path, {"oracle": oracle_logs, "always_answer": always_logs, "llm_direct": direct_logs})
    i = SB.gather(tmp_path)
    assert i.missing == () and i.game is not None
    md = SB.render(i, illustrate=False)
    assert "Not yet played" not in md
    assert "| wald | not yet |" in md
    mean = statistics.mean(float(g.winnings) for g in oracle_logs)
    assert f"| the oracle plays | 60 | {SB.usd(mean)} |" in md
    assert SB.usd(always_answer.expected(i.game)) in md and SB.usd(oracle_play.expected(i.game)) in md
    assert "| LLM plays directly | 5 |" in md and "— (no model)" in md
    assert "Games seed: 42" in md and "| Q1 | $38,110 |" not in md  # the real table, on these prices
    assert "| llm | easy | 1/2 |" in md
    # lifeline use by rung: the oracle's counts add up to the logs
    total = sum(len(g.lifeline_rungs) for g in oracle_logs)
    oracle_block = md.split("**the oracle plays**")[1].split("**LLM plays directly**")[0]
    totals = [int(line.rsplit("|", 2)[1]) for line in oracle_block.splitlines() if line.startswith(("| fifty", "| phone", "| audience"))]
    assert sum(totals) == total
