"""BASELINE -- the LLM plays directly: the contestant's own model, told the rules, the ladder, its remaining lifelines
and the question, asked for exactly one of `answer X` / `use fifty|phone|audience` / `walk`, in a loop.

This is a baseline, labelled as one (CLAUDE.md rule 1). The wald contestant never calls it.

The model decides alone: no LLM read is fired for it (its decision call is its knowledge), and the lifelines it
uses fire the same instruments the other contestants get. Parsing is strict up to whitespace and case; an
unparseable reply is a walk, and the host counts it as invalid. Every decision call is logged (rule 5).
"""
import re

from arena.transports import Instrument, call
from explainers.millionaire.calibration.reading import question_text
from explainers.millionaire.oracle.game import UNREAD, Game
from explainers.millionaire.oracle.host import INVALID, Decision, View

NAME = "LLM plays directly"
LIFELINE_NAMES = {"fifty": "50:50", "phone": "phone a friend", "audience": "ask the audience"}
REPLY = re.compile(r"\s*(?:answer\s+(?P<answer>[ABCD])|use\s+(?P<lifeline>fifty|phone|audience)|(?P<walk>walk))\s*",
                   re.IGNORECASE)


def money(x) -> str:
    return f"${int(x):,}" if x == int(x) else f"${float(x):,.2f}"


def rules(game: Game) -> str:
    ladder = "\n".join(f"  Q{r + 1}: {money(p)}" + ("  (safe haven)" if r in game.havens else "")
                       for r, p in enumerate(game.ladder))
    return (
        "You are the contestant on \"Who Wants to Be a Millionaire\". Your goal is to leave with as much money as "
        "possible.\n\n"
        f"There are {game.rungs} questions, each multiple choice with four options, exactly one right. Answering "
        "question N right wins its prize and moves you to question N+1. Before answering you may walk away and keep "
        "the prize you already hold. A wrong answer ends the game and you keep only the prize of the last safe haven "
        "you passed (nothing before the first).\n\n"
        f"The ladder:\n{ladder}\n\n"
        "Lifelines, each usable once per game, before you answer:\n"
        "  use fifty    -- 50:50: two wrong options are removed.\n"
        "  use phone    -- phone a friend: a friend tells you which option they think is right.\n"
        "  use audience -- ask the audience: the audience tells you which option it thinks is right.\n\n"
        "Reply with exactly one of these and nothing else:\n"
        "  answer A | answer B | answer C | answer D | use fifty | use phone | use audience | walk"
    )


def said(outcome: str) -> str:
    return "gave no clear answer" if outcome == UNREAD else f"said {outcome}"


def situation(game: Game, view: View) -> str:
    r = view.rung
    left = ", ".join(f"{LIFELINE_NAMES[k]} (use {k})" for k in ("fifty", "phone", "audience") if k in view.remaining)
    events = []
    for k, o in view.history:
        if k == "fifty":
            events.append(f"50:50 removed two wrong options; {o[0]} and {o[1]} remain.")
        elif k == "phone":
            events.append(f"Your friend {said(o)}.")
        elif k == "audience":
            events.append(f"The audience {said(o)}.")
    return (f"Question {r + 1} of {game.rungs}, for {money(game.ladder[r])}. Walking away now keeps "
            f"{money(game.walk(r))}; a wrong answer leaves you with {money(game.safe(r))}.\n"
            f"Lifelines left: {left or 'none'}.\n\n"
            f"{question_text(view.question)}"
            + ("\n\n" + "\n".join(events) if events else ""))


def parse(text: str) -> str:
    "The act a reply names, or INVALID."
    m = REPLY.fullmatch(text)
    if not m:
        return INVALID
    if m["answer"]:
        return f"answer {m['answer'].upper()}"
    return m["lifeline"].lower() if m["lifeline"] else "walk"


def contestant(instrument: Instrument, game: Game):
    "The contestant: one model call per decision, logged as instrument 'llm_direct'."
    system = rules(game)

    def decide(view: View) -> Decision:
        text, c = call(instrument, view.question.id, view.question.tier, system, situation(game, view), name="llm_direct")
        return Decision(parse(text), calls=(c,), raw=text)

    return decide
