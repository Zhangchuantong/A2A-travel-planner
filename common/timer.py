# common/timer.py

import time
from contextlib import contextmanager


@contextmanager
def timer(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        cost = time.perf_counter() - start
        print(f"[TIMER] {name}: {cost:.3f}s")