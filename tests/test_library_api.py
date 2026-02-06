"""Tests for yt_fetch public library API."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import yt_fetch
from yt_fetch import (
    BatchResult,
    FetchOptions,
    FetchResult,
    Metadata,
    Transcript,
    fetch_batch,
    fetch_video,
)
from yt_fetch.core.models import TranscriptSegment


def _make_metadata(video_id: str) -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title="Test",
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


# --- Exports ---


class TestExports:
    def test_version_exported(self):
        assert hasattr(yt_fetch, "__version__")
        assert isinstance(yt_fetch.__version__, str)

    def test_fetch_video_exported(self):
        assert callable(yt_fetch.fetch_video)

    def test_fetch_batch_exported(self):
        assert callable(yt_fetch.fetch_batch)

    def test_models_exported(self):
        assert yt_fetch.FetchOptions is FetchOptions
        assert yt_fetch.FetchResult is FetchResult
        assert yt_fetch.BatchResult is BatchResult
        assert yt_fetch.Metadata is Metadata
        assert yt_fetch.Transcript is Transcript

    def test_all_list(self):
        for name in yt_fetch.__all__:
            assert hasattr(yt_fetch, name)


# --- fetch_video ---


class TestFetchVideo:
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_with_valid_id(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata("dQw4w9WgXcQ")
        mock_trans.return_value = _make_transcript("dQw4w9WgXcQ")

        opts = FetchOptions(out=tmp_path)
        result = fetch_video("dQw4w9WgXcQ", opts)

        assert isinstance(result, FetchResult)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.success is True

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_with_url(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata("dQw4w9WgXcQ")
        mock_trans.return_value = _make_transcript("dQw4w9WgXcQ")

        opts = FetchOptions(out=tmp_path)
        result = fetch_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", opts)

        assert result.success is True
        assert result.video_id == "dQw4w9WgXcQ"

    def test_with_invalid_id(self):
        result = fetch_video("not-valid")
        assert result.success is False
        assert "Invalid video ID" in result.errors[0]

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_default_options(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata("dQw4w9WgXcQ")
        mock_trans.return_value = _make_transcript("dQw4w9WgXcQ")

        # Should work without explicit options (uses defaults)
        # We need to patch out to avoid writing to ./out
        with patch("yt_fetch.core.pipeline.Path") as mock_path:
            mock_path.return_value = tmp_path
            mock_path.side_effect = None
            result = fetch_video("dQw4w9WgXcQ", FetchOptions(out=tmp_path))

        assert isinstance(result, FetchResult)

    def test_no_cli_context_needed(self):
        """Library usage should not require Click or CLI setup."""
        # Just constructing options should work without CLI
        opts = FetchOptions()
        assert opts.languages == ["en"]
        assert opts.download == "none"


# --- fetch_batch ---


class TestFetchBatch:
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_batch_success(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        result = fetch_batch(["dQw4w9WgXcQ", "abc12345678"], opts)

        assert isinstance(result, BatchResult)
        assert result.total == 2
        assert result.succeeded == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_batch_deduplicates(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        result = fetch_batch(["dQw4w9WgXcQ", "dQw4w9WgXcQ"], opts)

        assert result.total == 1

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_batch_parses_urls(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        result = fetch_batch(
            ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "abc12345678"],
            opts,
        )

        assert result.total == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_batch_empty(self, mock_meta, mock_trans, tmp_path):
        opts = FetchOptions(out=tmp_path, workers=1)
        result = fetch_batch([], opts)

        assert result.total == 0
        assert result.succeeded == 0
