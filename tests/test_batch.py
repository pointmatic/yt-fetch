# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for yt_fetch.core.pipeline.process_batch."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from yt_fetch.core.models import BatchResult, FetchResult, Metadata, Transcript, TranscriptSegment
from yt_fetch.core.options import FetchOptions
from yt_fetch.core.pipeline import process_batch
from yt_fetch.services.metadata import MetadataError
from yt_fetch.services.transcript import TranscriptError


def _make_metadata(video_id: str) -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title=f"Video {video_id}",
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript(video_id: str) -> Transcript:
    return Transcript(
        video_id=video_id,
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=1.0, text="Hello")],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


class TestProcessBatch:
    """Test batch processing."""

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_all_succeed(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=2)
        result = process_batch(["vid_aaaaaaa", "vid_bbbbbbb"], opts)

        assert isinstance(result, BatchResult)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert len(result.results) == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_mixed_success_and_failure(self, mock_meta, mock_trans, tmp_path):
        def meta_side_effect(vid, opts):
            if vid == "bad_vid_aaaaa":
                raise MetadataError("not found")
            return _make_metadata(vid)

        mock_meta.side_effect = meta_side_effect
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        result = process_batch(["vid_aaaaaaa", "bad_vid_aaaaa", "vid_bbbbbbb"], opts)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1

        # The failed one should have errors
        failed = [r for r in result.results if not r.success]
        assert len(failed) == 1
        assert failed[0].video_id == "bad_vid_aaaaa"

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_error_isolation(self, mock_meta, mock_trans, tmp_path):
        """One failure should not prevent other videos from processing."""
        call_order = []

        def meta_side_effect(vid, opts):
            call_order.append(vid)
            if vid == "bad_vid_aaaaa":
                raise MetadataError("fail")
            return _make_metadata(vid)

        mock_meta.side_effect = meta_side_effect
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        result = process_batch(["vid_aaaaaaa", "bad_vid_aaaaa", "vid_bbbbbbb"], opts)

        # All three should have been attempted
        assert result.total == 3
        # The good ones should succeed
        good = [r for r in result.results if r.success]
        assert len(good) == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_empty_batch(self, mock_meta, mock_trans, tmp_path):
        opts = FetchOptions(out=tmp_path)
        result = process_batch([], opts)

        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.results == []

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_single_video(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata("vid_aaaaaaa")
        mock_trans.return_value = _make_transcript("vid_aaaaaaa")

        opts = FetchOptions(out=tmp_path)
        result = process_batch(["vid_aaaaaaa"], opts)

        assert result.total == 1
        assert result.succeeded == 1


class TestProcessBatchFailFast:
    """Test --fail-fast behavior."""

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_fail_fast_stops_after_error(self, mock_meta, mock_trans, tmp_path):
        processed = []

        def meta_side_effect(vid, opts):
            processed.append(vid)
            if vid == "bad_vid_aaaaa":
                raise MetadataError("fail")
            return _make_metadata(vid)

        mock_meta.side_effect = meta_side_effect
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        # Use workers=1 to ensure sequential processing for deterministic order
        opts = FetchOptions(out=tmp_path, fail_fast=True, workers=1)
        result = process_batch(["vid_aaaaaaa", "bad_vid_aaaaa", "vid_ccccccc", "vid_ddddddd"], opts)

        # Should have processed fewer than all 4 videos
        # At minimum vid_aaaaaaa and bad_vid_aaaaa are processed
        assert result.failed >= 1
        # Total processed should be less than 4 (some skipped after fail-fast)
        assert result.total < 4

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_no_fail_fast_processes_all(self, mock_meta, mock_trans, tmp_path):
        def meta_side_effect(vid, opts):
            if vid == "bad_vid_aaaaa":
                raise MetadataError("fail")
            return _make_metadata(vid)

        mock_meta.side_effect = meta_side_effect
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, fail_fast=False, workers=1)
        result = process_batch(["vid_aaaaaaa", "bad_vid_aaaaa", "vid_ccccccc"], opts)

        # All 3 should be processed
        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1


class TestProcessBatchConcurrency:
    """Test concurrency behavior."""

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_respects_workers_count(self, mock_meta, mock_trans, tmp_path):
        """Verify batch completes with multiple workers."""
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        ids = [f"vid_{chr(97+i)}" * 3 + chr(97+i) * 2 for i in range(5)]
        opts = FetchOptions(out=tmp_path, workers=3)
        result = process_batch(ids, opts)

        assert result.total == 5
        assert result.succeeded == 5
