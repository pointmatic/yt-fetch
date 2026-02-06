"""Tests for yt_fetch.utils.rate_limit."""

import threading
import time
from unittest.mock import patch

import pytest

from yt_fetch.utils.rate_limit import TokenBucket


class TestTokenBucketInit:
    def test_defaults(self):
        bucket = TokenBucket()
        assert bucket.rate == 2.0
        assert bucket.capacity == 2.0

    def test_custom_rate(self):
        bucket = TokenBucket(rate=5.0)
        assert bucket.rate == 5.0
        assert bucket.capacity == 5.0

    def test_custom_capacity(self):
        bucket = TokenBucket(rate=2.0, capacity=10.0)
        assert bucket.rate == 2.0
        assert bucket.capacity == 10.0


class TestTokenBucketAcquire:
    def test_acquire_within_capacity(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        for _ in range(10):
            assert bucket.acquire(blocking=False) is True

    def test_acquire_exceeds_capacity(self):
        bucket = TokenBucket(rate=2.0, capacity=2.0)
        assert bucket.acquire(blocking=False) is True
        assert bucket.acquire(blocking=False) is True
        assert bucket.acquire(blocking=False) is False

    def test_acquire_refills_over_time(self):
        bucket = TokenBucket(rate=100.0, capacity=1.0)
        assert bucket.acquire(blocking=False) is True
        assert bucket.acquire(blocking=False) is False
        time.sleep(0.02)  # 100 tokens/sec * 0.02s = 2 tokens
        assert bucket.acquire(blocking=False) is True

    def test_acquire_blocking_waits(self):
        bucket = TokenBucket(rate=100.0, capacity=1.0)
        bucket.acquire(blocking=False)  # drain
        start = time.monotonic()
        bucket.acquire(blocking=True)  # should wait ~0.01s
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # should be fast with 100 RPS

    def test_capacity_caps_tokens(self):
        bucket = TokenBucket(rate=100.0, capacity=2.0)
        time.sleep(0.1)  # would add 10 tokens, but capped at 2
        count = 0
        while bucket.acquire(blocking=False):
            count += 1
        assert count == 2

    def test_acquire_multiple_tokens(self):
        bucket = TokenBucket(rate=10.0, capacity=5.0)
        assert bucket.acquire(tokens=3.0, blocking=False) is True
        assert bucket.acquire(tokens=3.0, blocking=False) is False
        assert bucket.acquire(tokens=2.0, blocking=False) is True


class TestTokenBucketThreadSafety:
    def test_concurrent_acquire(self):
        bucket = TokenBucket(rate=1000.0, capacity=100.0)
        acquired = []
        barrier = threading.Barrier(10)

        def worker():
            barrier.wait()
            result = bucket.acquire(blocking=False)
            acquired.append(result)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 10 should succeed (capacity=100)
        assert sum(1 for r in acquired if r) == 10

    def test_concurrent_acquire_limited(self):
        bucket = TokenBucket(rate=1000.0, capacity=3.0)
        acquired = []
        barrier = threading.Barrier(10)

        def worker():
            barrier.wait()
            result = bucket.acquire(blocking=False)
            acquired.append(result)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = sum(1 for r in acquired if r)
        failures = sum(1 for r in acquired if not r)
        assert successes == 3
        assert failures == 7
