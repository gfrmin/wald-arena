"""The spend log: append-only JSONL, one row per paid item, resumed without paying twice, replayed without an API.

A run appends each row as soon as its call is paid and skips items already recorded, so an interrupted run
resumes where it stopped. A replay serves recorded rows by id and never calls anything.
"""
import json
import threading
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Hashable, Iterable, TypeVar

T = TypeVar("T")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def each(items: Iterable[T], work: Callable[[T], object], workers: int = 1,
         done: Callable[[T, object], None] = lambda item, out: None, quiet: tuple = ()) -> None:
    """work(item) for every item, up to `workers` at once, and done(item, result) as each finishes, one at a time.
    On the first failure no queued item starts; items already running finish, and done is still called for those
    that succeed, so nothing paid is lost. Then the first failure is raised: the first not of a `quiet` type (the
    knock-on stops a failure causes in the other workers), else the first."""
    items = list(items)
    if workers <= 1:
        for item in items:
            done(item, work(item))
        return
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(work, item): item for item in items}
        pending = set(futures)
        while pending:
            finished, pending = wait(pending, return_when=FIRST_EXCEPTION)
            if any(f.exception() for f in finished):
                for f in pending:
                    f.cancel()
                finished |= {f for f in pending if not f.cancelled()}
                wait(finished)
                pending = set()
            for f in finished:
                if not f.cancelled() and f.exception() is None:
                    with lock:
                        done(futures[f], f.result())
        failures = [f.exception() for f in futures if not f.cancelled() and f.exception()]
    if failures:
        raise next((e for e in failures if not isinstance(e, quiet)), failures[0])


def append_new(items: Iterable[T], id_of: Callable[[T], Hashable], pay: Callable[[T], dict], out: Path,
               workers: int = 1, quiet: tuple = ()) -> list[dict]:
    """For each item not yet in `out`, pay for it and append its row the moment it is paid, up to `workers` items at
    once (rows then land in the order they finish). Returns the new rows."""
    recorded = {r["question_id"] for r in read_rows(out)}
    new = []
    with open(out, "a") as f:
        def write(item, row):
            new.append(row)
            f.write(json.dumps(row) + "\n")
            f.flush()
        each([i for i in items if id_of(i) not in recorded], pay, workers, write, quiet)
    return new


def recorded_by_id(recorded: Iterable[dict]) -> Callable[[Hashable], dict]:
    "Look up a recorded row by question id; a dry run with no recorded reply fails loud."
    by_id = {r["question_id"]: r for r in recorded}

    def get(question_id):
        if question_id not in by_id:
            raise KeyError(f"dry run: no recorded reply for question {question_id}")
        return by_id[question_id]
    return get
