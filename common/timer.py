# common/timer.py

import time
from contextlib import contextmanager

from common.logger import get_logger, log_event


logger = get_logger(__name__)


@contextmanager
def timer(name: str, trace_id: str | None = None):
    start = time.perf_counter()
    try:
        yield
    finally:
        cost = time.perf_counter() - start
        log_event(
            logger,
            "timer",
            trace_id,
            name=name,
            elapsed_seconds=round(cost, 3),
        )
