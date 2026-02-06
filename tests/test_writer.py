"""Tests for yt_fetch.core.writer."""

import json
from datetime import datetime, timezone

import pytest

from yt_fetch.core.models import (
    BatchResult,
    FetchResult,
    Metadata,
    Transcript,
    TranscriptSegment,
)
from yt_fetch.core.writer import (
    write_metadata,
    write_summary,
    write_transcript_json,
    write_transcript_srt,
    write_transcript_txt,
    write_transcript_vtt,
)


def _make_metadata() -> Metadata:
    return Metadata(
        video_id="dQw4w9WgXcQ",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Video",
        channel_title="Test Channel",
        upload_date="2025-01-01",
        duration_seconds=120.0,
        tags=["test"],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript() -> Transcript:
    return Transcript(
        video_id="dQw4w9WgXcQ",
        language="en",
        is_generated=False,
        segments=[
            TranscriptSegment(start=0.0, duration=2.5, text="Hello world"),
            TranscriptSegment(start=2.5, duration=3.0, text="This is a test"),
            TranscriptSegment(start=5.5, duration=1.5, text="Goodbye"),
        ],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


# --- write_metadata ---


class TestWriteMetadata:
    def test_writes_json(self, tmp_path):
        meta = _make_metadata()
        path = write_metadata(meta, tmp_path)
        assert path.exists()
        assert path.name == "metadata.json"
        assert path.parent.name == "dQw4w9WgXcQ"

    def test_json_structure(self, tmp_path):
        meta = _make_metadata()
        path = write_metadata(meta, tmp_path)
        data = json.loads(path.read_text())
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert data["title"] == "Test Video"
        assert data["metadata_source"] == "yt-dlp"
        assert data["tags"] == ["test"]

    def test_overwrites_existing(self, tmp_path):
        meta = _make_metadata()
        write_metadata(meta, tmp_path)
        meta2 = _make_metadata()
        meta2.title = "Updated"
        path = write_metadata(meta2, tmp_path)
        data = json.loads(path.read_text())
        assert data["title"] == "Updated"


# --- write_transcript_json ---


class TestWriteTranscriptJson:
    def test_writes_json(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_json(t, tmp_path)
        assert path.exists()
        assert path.name == "transcript.json"

    def test_json_structure(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_json(t, tmp_path)
        data = json.loads(path.read_text())
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert data["language"] == "en"
        assert len(data["segments"]) == 3
        assert data["segments"][0]["text"] == "Hello world"
        assert data["segments"][0]["start"] == 0.0
        assert data["segments"][0]["duration"] == 2.5


# --- write_transcript_txt ---


class TestWriteTranscriptTxt:
    def test_writes_txt(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_txt(t, tmp_path)
        assert path.exists()
        assert path.name == "transcript.txt"

    def test_no_timestamps(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_txt(t, tmp_path)
        content = path.read_text()
        assert "00:" not in content
        assert "-->" not in content

    def test_plain_text_content(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_txt(t, tmp_path)
        lines = path.read_text().strip().split("\n")
        assert lines == ["Hello world", "This is a test", "Goodbye"]


# --- write_transcript_vtt ---


class TestWriteTranscriptVtt:
    def test_writes_vtt(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_vtt(t, tmp_path)
        assert path.exists()
        assert path.name == "transcript.vtt"

    def test_vtt_header(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_vtt(t, tmp_path)
        content = path.read_text()
        assert content.startswith("WEBVTT\n")

    def test_vtt_timestamps(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_vtt(t, tmp_path)
        content = path.read_text()
        assert "00:00:00.000 --> 00:00:02.500" in content
        assert "00:00:02.500 --> 00:00:05.500" in content
        assert "00:00:05.500 --> 00:00:07.000" in content

    def test_vtt_uses_dot_separator(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_vtt(t, tmp_path)
        content = path.read_text()
        assert "." in content
        assert "," not in content.replace("WEBVTT", "")


# --- write_transcript_srt ---


class TestWriteTranscriptSrt:
    def test_writes_srt(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_srt(t, tmp_path)
        assert path.exists()
        assert path.name == "transcript.srt"

    def test_srt_sequence_numbers(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_srt(t, tmp_path)
        content = path.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "1"
        assert lines[4] == "2"
        assert lines[8] == "3"

    def test_srt_timestamps(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_srt(t, tmp_path)
        content = path.read_text()
        assert "00:00:00,000 --> 00:00:02,500" in content
        assert "00:00:02,500 --> 00:00:05,500" in content

    def test_srt_uses_comma_separator(self, tmp_path):
        t = _make_transcript()
        path = write_transcript_srt(t, tmp_path)
        content = path.read_text()
        # SRT uses comma in timestamps, not dot
        assert "00:00:00,000" in content


# --- write_summary ---


class TestWriteSummary:
    def test_writes_summary(self, tmp_path):
        batch = BatchResult(
            total=2,
            succeeded=1,
            failed=1,
            results=[
                FetchResult(video_id="a", success=True),
                FetchResult(video_id="b", success=False, errors=["fail"]),
            ],
        )
        path = write_summary(batch, tmp_path)
        assert path.exists()
        assert path.name == "summary.json"

    def test_summary_structure(self, tmp_path):
        batch = BatchResult(
            total=1,
            succeeded=1,
            failed=0,
            results=[FetchResult(video_id="a", success=True)],
        )
        path = write_summary(batch, tmp_path)
        data = json.loads(path.read_text())
        assert data["total"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0
        assert len(data["results"]) == 1
