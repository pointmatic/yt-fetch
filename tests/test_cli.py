"""Smoke tests for yt_fetch CLI subcommands."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from yt_fetch.cli import (
    EXIT_ALL_FAILED,
    EXIT_ERROR,
    EXIT_OK,
    EXIT_PARTIAL,
    _collect_ids,
    _exit_code,
    cli,
)
from yt_fetch.core.models import BatchResult, FetchResult, Metadata, Transcript, TranscriptSegment
from yt_fetch.services.media import MediaResult


def _make_metadata(video_id: str = "dQw4w9WgXcQ") -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title="Test",
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript(video_id: str = "dQw4w9WgXcQ") -> Transcript:
    return Transcript(
        video_id=video_id,
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=1.0, text="Hello")],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


# --- _exit_code ---


class TestExitCode:
    def test_all_ok(self):
        assert _exit_code(3, 0, strict=False) == EXIT_OK

    def test_all_failed(self):
        assert _exit_code(3, 3, strict=False) == EXIT_ALL_FAILED

    def test_partial_no_strict(self):
        assert _exit_code(3, 1, strict=False) == EXIT_OK

    def test_partial_strict(self):
        assert _exit_code(3, 1, strict=True) == EXIT_PARTIAL

    def test_empty(self):
        assert _exit_code(0, 0, strict=False) == EXIT_OK


# --- _collect_ids ---


class TestCollectIds:
    def test_from_ids(self):
        result = _collect_ids(("dQw4w9WgXcQ",), None, None, "id")
        assert result == ["dQw4w9WgXcQ"]

    def test_from_file(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("dQw4w9WgXcQ\nabc12345678\n")
        result = _collect_ids((), f, None, "id")
        assert len(result) == 2

    def test_deduplication(self):
        result = _collect_ids(("dQw4w9WgXcQ", "dQw4w9WgXcQ"), None, None, "id")
        assert result == ["dQw4w9WgXcQ"]

    def test_empty(self):
        result = _collect_ids((), None, None, "id")
        assert result == []


# --- CLI smoke tests ---


class TestCliVersion:
    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "yt_fetch" in result.output


class TestCliFetch:
    def test_no_ids_exits_1(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == EXIT_ERROR

    @patch("yt_fetch.core.pipeline.process_batch")
    def test_with_id(self, mock_batch, tmp_path):
        mock_batch.return_value = BatchResult(
            total=1, succeeded=1, failed=0,
            results=[FetchResult(video_id="dQw4w9WgXcQ", success=True)],
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["fetch", "--id", "dQw4w9WgXcQ", "--out", str(tmp_path)])
        assert result.exit_code == EXIT_OK
        mock_batch.assert_called_once()

    @patch("yt_fetch.core.pipeline.process_batch")
    def test_strict_partial_failure(self, mock_batch, tmp_path):
        mock_batch.return_value = BatchResult(
            total=2, succeeded=1, failed=1,
            results=[
                FetchResult(video_id="a", success=True),
                FetchResult(video_id="b", success=False, errors=["fail"]),
            ],
        )
        runner = CliRunner()
        result = runner.invoke(cli, [
            "fetch", "--id", "dQw4w9WgXcQ", "--id", "xxxxxxxxxxx",
            "--out", str(tmp_path), "--strict",
        ])
        assert result.exit_code == EXIT_PARTIAL


class TestCliTranscript:
    def test_no_ids_exits_1(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["transcript"])
        assert result.exit_code == EXIT_ERROR

    @patch("yt_fetch.core.writer.write_transcript_json")
    @patch("yt_fetch.services.transcript.get_transcript")
    def test_success(self, mock_get, mock_write, tmp_path):
        mock_get.return_value = _make_transcript()
        mock_write.return_value = tmp_path / "dQw4w9WgXcQ" / "transcript.json"

        runner = CliRunner()
        result = runner.invoke(cli, [
            "transcript", "--id", "dQw4w9WgXcQ", "--out", str(tmp_path),
        ])
        assert result.exit_code == EXIT_OK


class TestCliMetadata:
    def test_no_ids_exits_1(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["metadata"])
        assert result.exit_code == EXIT_ERROR

    @patch("yt_fetch.core.writer.write_metadata")
    @patch("yt_fetch.services.metadata.get_metadata")
    def test_success(self, mock_get, mock_write, tmp_path):
        mock_get.return_value = _make_metadata()
        mock_write.return_value = tmp_path / "dQw4w9WgXcQ" / "metadata.json"

        runner = CliRunner()
        result = runner.invoke(cli, [
            "metadata", "--id", "dQw4w9WgXcQ", "--out", str(tmp_path),
        ])
        assert result.exit_code == EXIT_OK


class TestCliMedia:
    def test_no_ids_exits_1(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["media"])
        assert result.exit_code == EXIT_ERROR

    @patch("yt_fetch.services.media.download_media")
    def test_success(self, mock_dl, tmp_path):
        mock_dl.return_value = MediaResult(video_id="dQw4w9WgXcQ", paths=[Path("/tmp/v.mp4")])

        runner = CliRunner()
        result = runner.invoke(cli, [
            "media", "--id", "dQw4w9WgXcQ", "--out", str(tmp_path),
        ])
        assert result.exit_code == EXIT_OK
