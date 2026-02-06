"""Idempotency tests for yt_fetch.core.pipeline caching behavior.

Verifies that:
- Re-running without --force skips all work (services not called)
- Re-running with --force overwrites all outputs
- Selective --force-metadata, --force-transcript, --force-media work independently
- Cached file paths are returned correctly on skip
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from yt_fetch.core.models import FetchResult, Metadata, Transcript, TranscriptSegment
from yt_fetch.core.options import FetchOptions
from yt_fetch.core.pipeline import process_video
from yt_fetch.services.media import MediaResult


def _make_metadata(video_id: str = "testVid12345") -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title="Test Video",
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript(video_id: str = "testVid12345") -> Transcript:
    return Transcript(
        video_id=video_id,
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=2.0, text="Hello")],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


class TestIdempotencySkip:
    """Re-running without --force skips all work."""

    @patch("yt_fetch.core.pipeline.download_media")
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_second_run_skips_all(self, mock_meta, mock_trans, mock_media, tmp_path):
        # First run: fetch everything
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)

        result1 = process_video("testVid12345", opts)
        assert result1.success is True
        assert result1.metadata_path.exists()
        assert result1.transcript_path.exists()
        assert mock_meta.call_count == 1
        assert mock_trans.call_count == 1

        # Second run: should skip both
        mock_meta.reset_mock()
        mock_trans.reset_mock()

        result2 = process_video("testVid12345", opts)
        assert result2.success is True
        mock_meta.assert_not_called()
        mock_trans.assert_not_called()
        # Cached paths should still be returned
        assert result2.metadata_path == result1.metadata_path
        assert result2.transcript_path == result1.transcript_path

    @patch("yt_fetch.core.pipeline.download_media")
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_second_run_skips_media(self, mock_meta, mock_trans, mock_media, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        mock_media.return_value = MediaResult(
            video_id="testVid12345",
            paths=[tmp_path / "testVid12345" / "media" / "video.mp4"],
        )
        opts = FetchOptions(out=tmp_path, download="video")

        # First run
        result1 = process_video("testVid12345", opts)
        assert mock_media.call_count == 1

        # Create a fake media file so cache check passes
        media_dir = tmp_path / "testVid12345" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "video.mp4").write_bytes(b"fake")

        # Second run
        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_media.reset_mock()

        result2 = process_video("testVid12345", opts)
        mock_meta.assert_not_called()
        mock_trans.assert_not_called()
        mock_media.assert_not_called()
        # Cached media paths returned
        assert len(result2.media_paths) == 1

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_skipped_result_is_still_success(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)

        process_video("testVid12345", opts)
        mock_meta.reset_mock()
        mock_trans.reset_mock()

        result = process_video("testVid12345", opts)
        assert result.success is True
        assert result.errors == []


class TestIdempotencyForce:
    """Re-running with --force overwrites all outputs."""

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_refetches_all(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)

        # First run
        process_video("testVid12345", opts)

        # Second run with --force
        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()

        opts_force = FetchOptions(out=tmp_path, force=True)
        result = process_video("testVid12345", opts_force)

        mock_meta.assert_called_once()
        mock_trans.assert_called_once()
        assert result.success is True

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_overwrites_files(self, mock_meta, mock_trans, tmp_path):
        # First run with title "Original"
        meta1 = _make_metadata()
        meta1.title = "Original"
        mock_meta.return_value = meta1
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)
        process_video("testVid12345", opts)

        import json
        data1 = json.loads((tmp_path / "testVid12345" / "metadata.json").read_text())
        assert data1["title"] == "Original"

        # Second run with --force and title "Updated"
        meta2 = _make_metadata()
        meta2.title = "Updated"
        mock_meta.return_value = meta2
        mock_trans.return_value = _make_transcript()

        opts_force = FetchOptions(out=tmp_path, force=True)
        process_video("testVid12345", opts_force)

        data2 = json.loads((tmp_path / "testVid12345" / "metadata.json").read_text())
        assert data2["title"] == "Updated"


class TestSelectiveForce:
    """Selective --force-metadata, --force-transcript, --force-media."""

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_metadata_only(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)
        process_video("testVid12345", opts)

        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_meta.return_value = _make_metadata()

        opts_fm = FetchOptions(out=tmp_path, force_metadata=True)
        process_video("testVid12345", opts_fm)

        mock_meta.assert_called_once()
        mock_trans.assert_not_called()

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_transcript_only(self, mock_meta, mock_trans, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)
        process_video("testVid12345", opts)

        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_trans.return_value = _make_transcript()

        opts_ft = FetchOptions(out=tmp_path, force_transcript=True)
        process_video("testVid12345", opts_ft)

        mock_meta.assert_not_called()
        mock_trans.assert_called_once()

    @patch("yt_fetch.core.pipeline.download_media")
    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_media_only(self, mock_meta, mock_trans, mock_media, tmp_path):
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        mock_media.return_value = MediaResult(video_id="testVid12345")
        opts = FetchOptions(out=tmp_path, download="video")
        process_video("testVid12345", opts)

        # Create cached media
        media_dir = tmp_path / "testVid12345" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "video.mp4").write_bytes(b"fake")

        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_media.reset_mock()
        mock_media.return_value = MediaResult(video_id="testVid12345")

        opts_fmedia = FetchOptions(out=tmp_path, download="video", force_media=True)
        process_video("testVid12345", opts_fmedia)

        mock_meta.assert_not_called()
        mock_trans.assert_not_called()
        mock_media.assert_called_once()

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_force_overrides_selective(self, mock_meta, mock_trans, tmp_path):
        """--force should override even if selective flags are not set."""
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()
        opts = FetchOptions(out=tmp_path)
        process_video("testVid12345", opts)

        mock_meta.reset_mock()
        mock_trans.reset_mock()
        mock_meta.return_value = _make_metadata()
        mock_trans.return_value = _make_transcript()

        opts_force = FetchOptions(out=tmp_path, force=True)
        process_video("testVid12345", opts_force)

        mock_meta.assert_called_once()
        mock_trans.assert_called_once()
