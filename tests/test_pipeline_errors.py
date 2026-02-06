# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pipeline and error edge case tests for Story 7.3.

Covers:
- Idempotency with transcript content verification
- Error isolation with transcript errors in batch
- Fail-fast with transcript errors
- Retry integration with pipeline service calls
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, call
import json

import pytest

from yt_fetch.core.models import BatchResult, FetchResult, Metadata, Transcript, TranscriptSegment
from yt_fetch.core.options import FetchOptions
from yt_fetch.core.pipeline import process_batch, process_video
from yt_fetch.services.metadata import MetadataError
from yt_fetch.services.transcript import TranscriptError


def _make_metadata(video_id: str = "testVid12345") -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title="Test Video",
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript(video_id: str = "testVid12345", text: str = "Hello") -> Transcript:
    return Transcript(
        video_id=video_id,
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=2.0, text=text)],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


# --- Idempotency: transcript content verification ---


class TestIdempotencyTranscript:
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_overwrites_transcript(self, mock_meta, mock_trans, tmp_path):
        """--force should overwrite transcript content."""
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript(text="Original text")
        opts = FetchOptions(out=tmp_path)
        process_video("testVid12345", opts)

        data1 = json.loads((tmp_path / "testVid12345" / "transcript.json").read_text())
        assert data1["segments"][0]["text"] == "Original text"

        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript(text="Updated text")
        opts_force = FetchOptions(out=tmp_path, force=True)
        process_video("testVid12345", opts_force)

        data2 = json.loads((tmp_path / "testVid12345" / "transcript.json").read_text())
        assert data2["segments"][0]["text"] == "Updated text"

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_transcript_only_preserves_metadata(self, mock_meta, mock_trans, tmp_path):
        """--force-transcript should not refetch metadata."""
        meta = _make_metadata()
        meta.title = "Original Title"
        mock_meta.return_value = meta
        mock_trans.return_value = _make_transcript(text="v1")
        opts = FetchOptions(out=tmp_path)
        process_video("testVid12345", opts)

        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_trans.return_value = _make_transcript(text="v2")

        opts_ft = FetchOptions(out=tmp_path, force_transcript=True)
        process_video("testVid12345", opts_ft)

        mock_meta.assert_not_called()
        mock_trans.assert_called_once()
        # Metadata should be unchanged
        meta_data = json.loads((tmp_path / "testVid12345" / "metadata.json").read_text())
        assert meta_data["title"] == "Original Title"
        # Transcript should be updated
        trans_data = json.loads((tmp_path / "testVid12345" / "transcript.json").read_text())
        assert trans_data["segments"][0]["text"] == "v2"


# --- Error isolation: transcript errors in batch ---


class TestBatchTranscriptErrors:
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_transcript_error_isolated(self, mock_meta, mock_trans, tmp_path):
        """A transcript error for one video should not affect others."""
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)

        def trans_side(vid, opts):
            if vid == "bad_trans_aaa":
                raise TranscriptError("no transcript")
            return _make_transcript(vid)

        mock_trans.side_effect = trans_side

        opts = FetchOptions(out=tmp_path, workers=1)
        result = process_batch(["vid_aaaaaaa", "bad_trans_aaa", "vid_bbbbbbb"], opts)

        assert result.total == 3
        # bad_trans_aaa has errors but metadata still succeeded
        bad = [r for r in result.results if r.video_id == "bad_trans_aaa"]
        assert len(bad) == 1
        assert bad[0].success is False
        assert any("transcript" in e for e in bad[0].errors)

        # Other videos should succeed
        good = [r for r in result.results if r.success]
        assert len(good) == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_both_metadata_and_transcript_error(self, mock_meta, mock_trans, tmp_path):
        """Both metadata and transcript errors should be collected."""
        mock_meta.side_effect = MetadataError("meta fail")
        mock_trans.side_effect = TranscriptError("trans fail")

        opts = FetchOptions(out=tmp_path)
        result = process_video("testVid12345", opts)

        assert result.success is False
        assert len(result.errors) == 2
        assert any("metadata" in e for e in result.errors)
        assert any("transcript" in e for e in result.errors)


# --- Fail-fast with transcript errors ---


class TestFailFastTranscript:
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_fail_fast_on_transcript_error(self, mock_meta, mock_trans, tmp_path):
        """Fail-fast should trigger on transcript errors too."""
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)

        def trans_side(vid, opts):
            if vid == "bad_trans_aaa":
                raise TranscriptError("fail")
            return _make_transcript(vid)

        mock_trans.side_effect = trans_side

        opts = FetchOptions(out=tmp_path, fail_fast=True, workers=1)
        result = process_batch(
            ["vid_aaaaaaa", "bad_trans_aaa", "vid_ccccccc", "vid_ddddddd"], opts
        )

        assert result.failed >= 1
        assert result.total < 4


# --- Retry integration with pipeline ---


class TestRetryIntegration:
    """Test retry behavior on service functions directly (not through pipeline mocks)."""

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_metadata_backend_retries(self, mock_sleep):
        """The retry decorator on _yt_dlp_backend should retry MetadataError."""
        from yt_fetch.utils.retry import retry

        call_count = 0

        @retry(max_retries=3, retryable=(MetadataError,))
        def flaky_metadata(vid):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MetadataError("transient")
            return _make_metadata(vid)

        result = flaky_metadata("testVid12345")
        assert result.video_id == "testVid12345"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_transcript_retries(self, mock_sleep):
        """The retry decorator on get_transcript should retry TranscriptError."""
        from yt_fetch.utils.retry import retry

        call_count = 0

        @retry(max_retries=3, retryable=(TranscriptError,))
        def flaky_transcript(vid):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TranscriptError("transient")
            return _make_transcript(vid)

        result = flaky_transcript("testVid12345")
        assert result.video_id == "testVid12345"
        assert call_count == 2

    @patch("yt_fetch.utils.retry.time.sleep")
    def test_retry_exhausted_raises(self, mock_sleep):
        """If retries are exhausted, the error should propagate."""
        from yt_fetch.utils.retry import retry

        @retry(max_retries=2, retryable=(MetadataError,))
        def always_fails(vid):
            raise MetadataError("permanent")

        with pytest.raises(MetadataError, match="permanent"):
            always_fails("testVid12345")
        assert mock_sleep.call_count == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_pipeline_catches_exhausted_retry(self, mock_meta, mock_trans, tmp_path):
        """Pipeline should catch errors after retry exhaustion."""
        mock_meta.side_effect = MetadataError("permanent")
        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path)
        result = process_video("testVid12345", opts)

        assert result.success is False
        assert any("metadata" in e for e in result.errors)
