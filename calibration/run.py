"""Run one instrument on one tier's calibration and held-out questions; record right/wrong and every call.

    python -m calibration.run --instrument llm --tier easy
    python -m calibration.run --instrument llm --tier easy --dry-run recorded.jsonl --out /tmp/replayed.jsonl

Rows go to `calibration/<instrument>.jsonl`, one per question: question id, tier, slice (calibration | held_out),
report, truth, right, and the call's model, tokens, declared dollars and latency (rule 5). A run appends and skips
questions already recorded, so an interrupted run resumes without paying twice. `--dry-run` replays a recorded
jsonl instead of calling any API.
"""
import argparse
import json
from pathlib import Path
from typing import Callable, Iterable, Iterator

from calibration.instruments import Call, from_owner, read
from data import owner as O
from data.questions import TIERS, Question, Split, load, split

HERE = Path(__file__).resolve().parent
Asker = Callable[[Question], tuple[str, Call]]  # question -> (report, call)


def rows_path(instrument: str) -> Path:
    return HERE / f"{instrument}.jsonl"


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def row(slice_: str, q: Question, report: str, c: Call) -> dict:
    return {"instrument": c.instrument, "model": c.model, "slice": slice_, "question_id": q.id, "tier": q.tier,
            "report": report, "truth": q.answer, "right": report == q.answer,
            "input_tokens": c.input_tokens, "output_tokens": c.output_tokens, "usd": str(c.usd),
            "latency_s": c.latency_s, "reply": c.reply}


def slices(s: Split, tier: int) -> Iterator[tuple[str, Question]]:
    for name, part in (("calibration", s.calibration), ("held_out", s.held_out)):
        yield from ((name, q) for q in part if q.tier == tier)


def run(s: Split, tier: int, ask: Asker, out: Path) -> list[dict]:
    "Ask every not-yet-recorded calibration and held-out question of the tier; append its row as soon as it is paid."
    done = {r["question_id"] for r in read_rows(out)}
    new = []
    with open(out, "a") as f:
        for slice_, q in slices(s, tier):
            if q.id in done:
                continue
            report, c = ask(q)
            new.append(row(slice_, q, report, c))
            f.write(json.dumps(new[-1]) + "\n")
            f.flush()
    return new


def replaying(recorded: Iterable[dict]) -> Asker:
    "An asker that serves recorded replies by question id and never calls an API."
    by_id = {r["question_id"]: r for r in recorded}

    def ask(q: Question) -> tuple[str, Call]:
        if q.id not in by_id:
            raise KeyError(f"dry run: no recorded reply for question {q.id}")
        r = by_id[q.id]
        return r["report"], Call.from_json({k: r[k] for k in ("instrument", "model", "input_tokens", "output_tokens",
                                                               "usd", "latency_s", "reply")}
                                           | {"question_id": q.id, "tier": q.tier})
    return ask


def owner_split(owner) -> Split:
    return split(load(O.ROOT / O.need(owner, "questions.path")), seed=O.need(owner, "split_seed"),
                 per_tier=O.need(owner, "calibration.per_tier"),
                 held_out_per_tier=O.need(owner, "calibration.held_out_per_tier"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--instrument", required=True, choices=("llm", "phone", "audience"))
    p.add_argument("--tier", required=True, choices=TIERS)
    p.add_argument("--dry-run", type=Path, help="replay this recorded jsonl; no API calls")
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    owner = O.load()
    out = a.out or rows_path(a.instrument)
    if a.dry_run and out.resolve() == a.dry_run.resolve():
        p.error("--out must differ from --dry-run")
    instrument = None if a.dry_run else from_owner(owner, a.instrument)
    ask = replaying(read_rows(a.dry_run)) if a.dry_run else (lambda q: read(instrument, q))
    new = run(owner_split(owner), TIERS.index(a.tier), ask, out)
    print(f"{a.instrument} / {a.tier}: {len(new)} new rows -> {out}")


if __name__ == "__main__":
    main()
