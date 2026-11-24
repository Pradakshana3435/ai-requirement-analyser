from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Sequence, TypeVar

import config

A = TypeVar("A")
R = TypeVar("R")


def map_batches(fn: Callable[[A], R], batches: Sequence[A]) -> List[R]:
    """Run fn over the batches in parallel (up to MAX_PARALLEL at once), keeping their order."""
    if len(batches) <= 1 or config.MAX_PARALLEL <= 1:
        return [fn(b) for b in batches]
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL) as pool:
        return list(pool.map(fn, batches))