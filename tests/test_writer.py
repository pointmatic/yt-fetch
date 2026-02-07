# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
    read_metadata,
    read_transcript_json,
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


# --- read_metadata ---


class TestReadMetadata:
    def test_round_trip(self, tmp_path):
        meta = _make_metadata()
        write_metadata(meta, tmp_path)
        loaded = read_metadata(tmp_path, "dQw4w9WgXcQ")
        assert loaded is not None
        assert loaded.video_id == "dQw4w9WgXcQ"
        assert loaded.title == "Test Video"
        assert loaded.metadata_source == "yt-dlp"
        assert loaded.tags == ["test"]

    def test_missing_file_returns_none(self, tmp_path):
        loaded = read_metadata(tmp_path, "nonexistent")
        assert loaded is None

    def test_invalid_json_returns_none(self, tmp_path):
        video_dir = tmp_path / "bad"
        video_dir.mkdir()
        (video_dir / "metadata.json").write_text("not json")
        loaded = read_metadata(tmp_path, "bad")
        assert loaded is None

    def test_incomplete_json_returns_none(self, tmp_path):
        video_dir = tmp_path / "bad2"
        video_dir.mkdir()
        (video_dir / "metadata.json").write_text('{"video_id": "bad2"}')
        loaded = read_metadata(tmp_path, "bad2")
        assert loaded is None


# --- read_transcript_json ---


class TestReadTranscriptJson:
    def test_round_trip(self, tmp_path):
        trans = _make_transcript()
        write_transcript_json(trans, tmp_path)
        loaded = read_transcript_json(tmp_path, "dQw4w9WgXcQ")
        assert loaded is not None
        assert loaded.video_id == "dQw4w9WgXcQ"
        assert loaded.language == "en"
        assert len(loaded.segments) == 3
        assert loaded.segments[0].text == "Hello world"

    def test_missing_file_returns_none(self, tmp_path):
        loaded = read_transcript_json(tmp_path, "nonexistent")
        assert loaded is None

    def test_invalid_json_returns_none(self, tmp_path):
        video_dir = tmp_path / "bad"
        video_dir.mkdir()
        (video_dir / "transcript.json").write_text("not json")
        loaded = read_transcript_json(tmp_path, "bad")
        assert loaded is None


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
