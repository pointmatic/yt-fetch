"""Token bucket rate limiter."""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """Thread-safe token bucket rate limiter.

    Args:
        rate: Tokens added per second (e.g. 2.0 = 2 requests per second).
        capacity: Maximum burst capacity. Defaults to rate (no burst beyond 1s).
    """

    def __init__(self, rate: float = 2.0, capacity: float | None = None) -> None:
        self._rate = rate
        self._capacity = capacity if capacity is not None else rate
        self._tokens = self._capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def capacity(self) -> float:
        return self._capacity

    def acquire(self, tokens: float = 1.0, blocking: bool = True) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to consume (default 1).
            blocking: If True, block until tokens are available.
                      If False, return False immediately when unavailable.

        Returns:
            True if tokens were acquired, False if non-blocking and unavailable.
        """
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                if not blocking:
                    return False
                wait_time = (tokens - self._tokens) / self._rate
            time.sleep(wait_time)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time. Must be called under lock."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now
