"""Tests for yt_fetch.utils.retry."""

from unittest.mock import patch, MagicMock

import pytest

from yt_fetch.utils.retry import _compute_delay, is_retryable_http_status, retry


class TestComputeDelay:
    def test_first_attempt(self):
        # attempt=0: base_delay * 2^0 = 1.0, jitter=0 for deterministic test
        delay = _compute_delay(0, base_delay=1.0, multiplier=2.0, jitter=0.0)
        assert delay == 1.0

    def test_second_attempt(self):
        delay = _compute_delay(1, base_delay=1.0, multiplier=2.0, jitter=0.0)
        assert delay == 2.0

    def test_third_attempt(self):
        delay = _compute_delay(2, base_delay=1.0, multiplier=2.0, jitter=0.0)
        assert delay == 4.0

    def test_custom_base_delay(self):
        delay = _compute_delay(0, base_delay=0.5, multiplier=2.0, jitter=0.0)
        assert delay == 0.5

    def test_jitter_within_range(self):
        delays = [_compute_delay(0, 1.0, 2.0, 0.25) for _ in range(100)]
        assert all(0.75 <= d <= 1.25 for d in delays)

    def test_never_negative(self):
        delays = [_compute_delay(0, 0.01, 1.0, 1.0) for _ in range(100)]
        assert all(d >= 0.0 for d in delays)


class TestIsRetryableHttpStatus:
    def test_429(self):
        assert is_retryable_http_status(429) is True

    def test_500(self):
        assert is_retryable_http_status(500) is True

    def test_502(self):
        assert is_retryable_http_status(502) is True

    def test_503(self):
        assert is_retryable_http_status(503) is True

    def test_200(self):
        assert is_retryable_http_status(200) is False

    def test_404(self):
        assert is_retryable_http_status(404) is False

    def test_401(self):
        assert is_retryable_http_status(401) is False


class TestRetryDecorator:
    @patch("yt_fetch.utils.retry.time.sleep")
    def test_succeeds_first_try(self, mock_sleep):
        call_count = 0

        @retry(max_retries=3, retryable=(ValueError,))
        def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert fn() == "ok"
        assert call_count == 1
        mock_sleep.assert_not_called()

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_retries_then_succeeds(self, mock_sleep):
        call_count = 0

        @retry(max_retries=3, base_delay=0.1, retryable=(ValueError,))
        def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return "ok"

        assert fn() == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_exhausts_retries(self, mock_sleep):
        call_count = 0

        @retry(max_retries=2, base_delay=0.1, retryable=(ValueError,))
        def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            fn()
        assert call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_no_retry_on_non_retryable(self, mock_sleep):
        call_count = 0

        @retry(max_retries=3, retryable=(ValueError,))
        def fn():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            fn()
        assert call_count == 1
        mock_sleep.assert_not_called()

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_zero_retries(self, mock_sleep):
        call_count = 0

        @retry(max_retries=0, retryable=(ValueError,))
        def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            fn()
        assert call_count == 1
        mock_sleep.assert_not_called()

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_preserves_function_name(self, mock_sleep):
        @retry(retryable=(ValueError,))
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep):
        @retry(max_retries=3, base_delay=1.0, multiplier=2.0, jitter=0.0, retryable=(ValueError,))
        def fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            fn()

        # 3 sleeps: delay for attempt 0=1.0, attempt 1=2.0, attempt 2=4.0
        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0, 4.0]

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_retries_subclass_exceptions(self, mock_sleep):
        """Retry should catch subclasses of retryable exceptions."""

        class BaseError(Exception):
            pass

        class SubError(BaseError):
            pass

        call_count = 0

        @retry(max_retries=2, base_delay=0.1, retryable=(BaseError,))
        def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise SubError("sub")
            return "ok"

        assert fn() == "ok"
        assert call_count == 2
