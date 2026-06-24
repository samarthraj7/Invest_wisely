"""Shared resilience helpers for external APIs: a minimum-interval rate limiter
and an exponential-backoff retry wrapper (with jitter) for transient failures
and HTTP 429 / 5xx responses.
"""
from __future__ import annotations

import random
import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RateLimiter:
    """Enforces a minimum interval between calls. Thread-safe."""

    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval_s:
                time.sleep(self.min_interval_s - delta)
            self._last = time.monotonic()


class RateLimited(Exception):
    """Raise from a wrapped fn to signal a 429-style backoff is warranted."""


def with_retry(
    fn: Callable[[], T],
    *,
    retries: int = 3,
    base_delay_s: float = 0.8,
    max_delay_s: float = 8.0,
    rate_limiter: RateLimiter | None = None,
) -> T:
    """Call `fn`, retrying on exceptions with exponential backoff + jitter.

    Raise `RateLimited` from `fn` (or let any exception propagate) to trigger a
    retry. After exhausting retries, the last exception is re-raised so callers
    can fall back gracefully.
    """
    attempt = 0
    while True:
        if rate_limiter:
            rate_limiter.wait()
        try:
            return fn()
        except Exception:  # noqa: BLE001 - intentional: back off on any transient error
            attempt += 1
            if attempt > retries:
                raise
            delay = min(max_delay_s, base_delay_s * (2 ** (attempt - 1)))
            time.sleep(delay + random.uniform(0, delay * 0.25))
