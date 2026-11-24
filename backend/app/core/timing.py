import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


@contextmanager
def timed(label: str) -> Iterator[None]:
    """Measure wall-clock time and log ``label: 1.23s``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info("%s: %.2fs", label, time.perf_counter() - start)