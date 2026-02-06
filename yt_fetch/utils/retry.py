"""Exponential backoff retry decorator."""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Callable, Sequence

logger = logging.getLogger("yt_fetch")

# Default exceptions considered retryable
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    multiplier: float = 2.0,
    jitter: float = 0.25,
    retryable: Sequence[type[Exception]] | None = None,
) -> Callable:
    """Decorator for retrying a function with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts (0 = no retries).
        base_delay: Initial delay in seconds before first retry.
        multiplier: Delay multiplier per retry (2.0 = double each time).
        jitter: Jitter factor as fraction of delay (0.25 = ±25%).
        retryable: Exception types to retry on. Defaults to network-related errors.
    """
    if retryable is None:
        retryable = RETRYABLE_EXCEPTIONS

    retryable_tuple = tuple(retryable)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_tuple as exc:
                    last_exc = exc
                    if attempt >= max_retries:
                        logger.error(
                            "Retry exhausted for %s after %d attempts: %s",
                            func.__name__,
                            attempt + 1,
                            exc,
                        )
                        raise
                    delay = _compute_delay(attempt, base_delay, multiplier, jitter)
                    logger.warning(
                        "Retry %d/%d for %s after %.2fs: %s",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
            raise last_exc  # pragma: no cover

        return wrapper

    return decorator


def _compute_delay(
    attempt: int,
    base_delay: float,
    multiplier: float,
    jitter: float,
) -> float:
    """Compute delay with exponential backoff and jitter.

    delay = base_delay * multiplier^attempt * (1 ± jitter)
    """
    delay = base_delay * (multiplier ** attempt)
    jitter_range = delay * jitter
    delay += random.uniform(-jitter_range, jitter_range)
    return max(0.0, delay)


def is_retryable_http_status(status_code: int) -> bool:
    """Check if an HTTP status code is retryable (429 or 5xx)."""
    return status_code == 429 or 500 <= status_code < 600
