"""The spend log: append-only JSONL, one row per paid item, resumed without paying twice, replayed without an API.

A run appends each row as soon as its call is paid and skips items already recorded, so an interrupted run
resumes where it stopped. A replay serves recorded rows by id and never calls anything.
"""
import json
from pathlib import Path
from typing import Callable, Hashable, Iterable, TypeVar

T = TypeVar("T")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_new(items: Iterable[T], id_of: Callable[[T], Hashable], pay: Callable[[T], dict], out: Path) -> list[dict]:
    "For each item not yet in `out`, pay for it and append its row at once. Returns the new rows."
    done = {r["question_id"] for r in read_rows(out)}
    new = []
    with open(out, "a") as f:
        for item in items:
            if id_of(item) in done:
                continue
            new.append(pay(item))
            f.write(json.dumps(new[-1]) + "\n")
            f.flush()
    return new


def recorded_by_id(recorded: Iterable[dict]) -> Callable[[Hashable], dict]:
    "Look up a recorded row by question id; a dry run with no recorded reply fails loud."
    by_id = {r["question_id"]: r for r in recorded}

    def get(question_id):
        if question_id not in by_id:
            raise KeyError(f"dry run: no recorded reply for question {question_id}")
        return by_id[question_id]
    return get
