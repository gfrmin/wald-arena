"""Play N games for one contestant and write its game logs to `explainers/millionaire/games/<contestant>.jsonl`.

    python -m explainers.millionaire.play --contestant oracle
    python -m explainers.millionaire.play --contestant always_answer
    python -m explainers.millionaire.play --contestant llm_direct

Every contestant plays the same questions: game i's questions are drawn from the play set with the owner's games
seed, and its 50:50 at rung r removes the same options for everyone. Needs the owner's numbers and the fitted
reliabilities; fails loud, naming what is missing.
"""
import argparse
import json
import random
from pathlib import Path

from explainers.millionaire.calibration.fit import fitted_path, reliability
from arena.transports import from_owner
from explainers.millionaire.calibration.reading import read
from explainers.millionaire.calibration.run import owner_split
from explainers.millionaire import owner as O
from explainers.millionaire.questions import Question, draw_game
from explainers.millionaire.oracle.game import Game
from explainers.millionaire.oracle.host import fifty_outcome, play

GAMES = O.ROOT / "games"
SLUGS = ("oracle", "always_answer", "llm_direct")


def games_path(slug: str) -> Path:
    return GAMES / f"{slug}.jsonl"


def game_questions(play_pool, tiers, seed: int, n: int) -> list[tuple[Question, ...]]:
    rng = random.Random(f"questions:{seed}")
    return [draw_game(play_pool, tiers, rng) for _ in range(n)]


def fire_for(instruments, seed: int, game_index: int):
    "Real instruments; the 50:50 at (game, rung) is seeded by both, so every contestant sees the same one."
    def fire(k, q, r):
        if k == "fifty":
            return fifty_outcome(q, random.Random(f"fifty:{seed}:{game_index}:{r}")), None
        return read(instruments[k], q)
    return fire


def fitted_game(owner) -> Game:
    return O.game(owner, {k: reliability(fitted_path(k)) for k in ("llm", "phone", "audience")})


def contestant_for(slug: str, game: Game, instruments):
    from explainers.millionaire.baselines import always_answer, llm_direct
    from explainers.millionaire.oracle import play as oracle_play
    return {"oracle": lambda: (oracle_play.NAME, oracle_play.contestant(game), game.read_first),
            "always_answer": lambda: (always_answer.NAME, always_answer.contestant, game.read_first),
            "llm_direct": lambda: (llm_direct.NAME, llm_direct.contestant(instruments["llm"], game), False)}[slug]()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--contestant", required=True, choices=SLUGS)
    p.add_argument("--games", type=int, help="default: the owner's games.per_contestant")
    a = p.parse_args(argv)
    owner = O.load()
    seed, n = O.need(owner, "games.seed"), a.games or O.need(owner, "games.per_contestant")
    game = fitted_game(owner)
    instruments = {k: from_owner(owner, k) for k in ("llm", "phone", "audience")}
    name, contestant, read_first = contestant_for(a.contestant, game, instruments)
    out = games_path(a.contestant)
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        for i, qs in enumerate(game_questions(owner_split(owner).play, game.tiers, seed, n)):
            log = play(contestant, name, i, qs, game, fire_for(instruments, seed, i), read_first)
            f.write(json.dumps(log.to_json()) + "\n")
            f.flush()
    print(f"{name}: {n} games -> {out}")


if __name__ == "__main__":
    main()
