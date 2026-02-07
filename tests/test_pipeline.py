# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for yt_fetch.core.pipeline."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_fetch.core.models import FetchResult, Metadata, Transcript, TranscriptSegment
from yt_fetch.core.options import FetchOptions
from yt_fetch.core.pipeline import process_video
from yt_fetch.services.media import MediaResult
from yt_fetch.services.metadata import MetadataError
from yt_fetch.services.transcript import TranscriptError, TranscriptNotFound


def _make_metadata(video_id: str = "dQw4w9WgXcQ") -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title="Test Video",
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript(video_id: str = "dQw4w9WgXcQ") -> Transcript:
    return Transcript(
        video_id=video_id,
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=2.0, text="Hello")],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


class TestProcessVideo:
    """Test the per-video pipeline."""

    @patch("yt_fetch.core.pipeline.download_media")
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_success_full_pipeline(self, mock_meta, mock_trans, mock_media, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        mock_media.return_value = MediaResult(video_id="dQw4w9WgXcQ", skipped=True)

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert isinstance(result, FetchResult)
        assert result.success is True
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.metadata_path is not None
        assert result.transcript_path is not None
        assert result.metadata_path.exists()
        assert result.transcript_path.exists()
        assert result.errors == []
        mock_meta.assert_called_once()
        mock_trans.assert_called_once()

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_creates_output_dir(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path)
        process_video("dQw4w9WgXcQ", opts)

        assert (tmp_path / "dQw4w9WgXcQ").is_dir()

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_metadata_error_continues(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = MetadataError("Video not found")
        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.success is False
        assert result.metadata_path is None
        assert result.transcript_path is not None
        assert len(result.errors) == 1
        assert "metadata" in result.errors[0]

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_transcript_error_continues(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.side_effect = TranscriptNotFound("No transcript")

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.success is True
        assert result.metadata_path is not None
        assert result.transcript_path is None
        assert len(result.errors) == 1
        assert "transcript" in result.errors[0]

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_both_errors(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = MetadataError("fail")
        mock_trans.side_effect = TranscriptError("fail")

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.success is False
        assert len(result.errors) == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_cache_skip_metadata(self, mock_meta, mock_trans, tmp_path):
        # Pre-create cached metadata file with valid data
        meta = _make_metadata()
        video_dir = tmp_path / "dQw4w9WgXcQ"
        video_dir.mkdir()
        import json
        (video_dir / "metadata.json").write_text(
            json.dumps(meta.model_dump(mode="json"), default=str)
        )

        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        mock_meta.assert_not_called()
        assert result.metadata_path == video_dir / "metadata.json"
        assert result.metadata is not None
        assert result.metadata.video_id == "dQw4w9WgXcQ"
        assert result.metadata.title == "Test Video"

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_cache_skip_transcript(self, mock_meta, mock_trans, tmp_path):
        # Pre-create cached transcript file with valid data
        trans = _make_transcript()
        video_dir = tmp_path / "dQw4w9WgXcQ"
        video_dir.mkdir()
        import json
        (video_dir / "transcript.json").write_text(
            json.dumps(trans.model_dump(mode="json"), default=str)
        )

        mock_meta.return_value = _make_metadata()

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        mock_trans.assert_not_called()
        assert result.transcript_path == video_dir / "transcript.json"
        assert result.transcript is not None
        assert result.transcript.video_id == "dQw4w9WgXcQ"
        assert result.transcript.language == "en"
        assert len(result.transcript.segments) == 1

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_overrides_cache(self, mock_meta, mock_trans, tmp_path):
        # Pre-create cached files
        video_dir = tmp_path / "dQw4w9WgXcQ"
        video_dir.mkdir()
        (video_dir / "metadata.json").write_text("{}")
        (video_dir / "transcript.json").write_text("{}")

        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path, force=True)
        result = process_video("dQw4w9WgXcQ", opts)

        mock_meta.assert_called_once()
        mock_trans.assert_called_once()
        assert result.success is True

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_metadata_selective(self, mock_meta, mock_trans, tmp_path):
        video_dir = tmp_path / "dQw4w9WgXcQ"
        video_dir.mkdir()
        (video_dir / "metadata.json").write_text("{}")
        (video_dir / "transcript.json").write_text("{}")

        mock_meta.return_value = _make_metadata()

        opts = FetchOptions(out=tmp_path, force_metadata=True)
        result = process_video("dQw4w9WgXcQ", opts)

        mock_meta.assert_called_once()
        mock_trans.assert_not_called()

    @patch("yt_fetch.core.pipeline.download_media")
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_media_download_when_enabled(self, mock_meta, mock_trans, mock_media, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        mock_media.return_value = MediaResult(
            video_id="dQw4w9WgXcQ",
            paths=[Path("/tmp/video.mp4")],
        )

        opts = FetchOptions(out=tmp_path, download="video")
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.success is True
        assert len(result.media_paths) == 1
        mock_media.assert_called_once()

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_no_media_when_download_none(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path, download="none")
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.media_paths == []

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_returns_metadata_and_transcript_objects(self, mock_meta, mock_trans, tmp_path):
        meta = _make_metadata()
        trans = _make_transcript()
        mock_meta.return_value = meta
        mock_trans.return_value = trans

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.metadata == meta
        assert result.transcript == trans

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_success_true_when_only_transcript_fails(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.side_effect = TranscriptError("No captions")

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.success is True
        assert result.metadata is not None
        assert result.transcript is None
        assert len(result.errors) == 1
        assert "transcript" in result.errors[0]

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_success_false_when_metadata_fails(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = MetadataError("Video not found")
        mock_trans.return_value = _make_transcript()

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        assert result.success is False
        assert result.metadata is None
        assert result.transcript is not None
        assert any("metadata" in e for e in result.errors)

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_cached_rerun_populates_both_objects(self, mock_meta, mock_trans, tmp_path):
        """Simulate a second run where both files are cached on disk."""
        import json

        meta = _make_metadata()
        trans = _make_transcript()
        video_dir = tmp_path / "dQw4w9WgXcQ"
        video_dir.mkdir()
        (video_dir / "metadata.json").write_text(
            json.dumps(meta.model_dump(mode="json"), default=str)
        )
        (video_dir / "transcript.json").write_text(
            json.dumps(trans.model_dump(mode="json"), default=str)
        )

        opts = FetchOptions(out=tmp_path)
        result = process_video("dQw4w9WgXcQ", opts)

        mock_meta.assert_not_called()
        mock_trans.assert_not_called()
        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.video_id == "dQw4w9WgXcQ"
        assert result.transcript is not None
        assert result.transcript.language == "en"
        assert len(result.transcript.segments) == 1
