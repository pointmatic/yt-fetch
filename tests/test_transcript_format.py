# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for yt_fetch.utils.time_fmt — timestamp edge cases."""

import pytest

from yt_fetch.utils.time_fmt import seconds_to_srt, seconds_to_vtt


class TestSecondsToVtt:
    def test_zero(self):
        assert seconds_to_vtt(0.0) == "00:00:00.000"

    def test_milliseconds(self):
        assert seconds_to_vtt(0.5) == "00:00:00.500"

    def test_one_second(self):
        assert seconds_to_vtt(1.0) == "00:00:01.000"

    def test_minutes(self):
        assert seconds_to_vtt(65.0) == "00:01:05.000"

    def test_hours(self):
        assert seconds_to_vtt(3661.5) == "01:01:01.500"

    def test_large_value(self):
        assert seconds_to_vtt(36000.0) == "10:00:00.000"

    def test_fractional_milliseconds(self):
        assert seconds_to_vtt(1.1234) == "00:00:01.123"

    def test_rounding_edge(self):
        assert seconds_to_vtt(1.9999) == "00:00:01.999"

    def test_negative_clamped_to_zero(self):
        assert seconds_to_vtt(-5.0) == "00:00:00.000"

    def test_uses_dot_separator(self):
        result = seconds_to_vtt(1.5)
        assert "." in result
        assert "," not in result

    def test_59_minutes_59_seconds(self):
        assert seconds_to_vtt(3599.999) == "00:59:59.999"

    def test_exact_boundary(self):
        assert seconds_to_vtt(60.0) == "00:01:00.000"

    def test_small_fraction(self):
        assert seconds_to_vtt(0.001) == "00:00:00.001"


class TestSecondsToSrt:
    def test_zero(self):
        assert seconds_to_srt(0.0) == "00:00:00,000"

    def test_milliseconds(self):
        assert seconds_to_srt(0.5) == "00:00:00,500"

    def test_one_second(self):
        assert seconds_to_srt(1.0) == "00:00:01,000"

    def test_minutes(self):
        assert seconds_to_srt(65.0) == "00:01:05,000"

    def test_hours(self):
        assert seconds_to_srt(3661.5) == "01:01:01,500"

    def test_uses_comma_separator(self):
        result = seconds_to_srt(1.5)
        assert "," in result
        # Only the timestamp comma, not a dot
        parts = result.split(",")
        assert len(parts) == 2

    def test_negative_clamped_to_zero(self):
        assert seconds_to_srt(-5.0) == "00:00:00,000"

    def test_rounding_edge(self):
        assert seconds_to_srt(1.9999) == "00:00:01,999"

    def test_small_fraction(self):
        assert seconds_to_srt(0.001) == "00:00:00,001"
