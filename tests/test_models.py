"""Tests for yt_fetch.core.models and yt_fetch.core.options."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from yt_fetch.core.models import (
    BatchResult,
    FetchResult,
    Metadata,
    Transcript,
    TranscriptSegment,
)
from yt_fetch.core.options import FetchOptions


# --- Metadata ---


class TestMetadata:
    def test_minimal(self):
        m = Metadata(
            video_id="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            metadata_source="yt-dlp",
        )
        assert m.video_id == "dQw4w9WgXcQ"
        assert m.title is None
        assert m.tags == []
        assert m.raw is None

    def test_full(self):
        m = Metadata(
            video_id="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            channel_title="Rick Astley",
            channel_id="UCuAXFkgsw1L7xaCfnd5JJOw",
            upload_date="2009-10-25",
            duration_seconds=212.0,
            description="The official video",
            tags=["rick", "astley"],
            view_count=1_500_000_000,
            like_count=15_000_000,
            fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            metadata_source="yt-dlp",
            raw={"id": "dQw4w9WgXcQ"},
        )
        assert m.title == "Never Gonna Give You Up"
        assert m.duration_seconds == 212.0
        assert len(m.tags) == 2

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Metadata()

    def test_round_trip(self):
        m = Metadata(
            video_id="abc",
            source_url="https://youtu.be/abc",
            fetched_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            metadata_source="yt-dlp",
        )
        data = m.model_dump()
        m2 = Metadata.model_validate(data)
        assert m == m2

    def test_json_round_trip(self):
        m = Metadata(
            video_id="abc",
            source_url="https://youtu.be/abc",
            fetched_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            metadata_source="yt-dlp",
        )
        json_str = m.model_dump_json()
        m2 = Metadata.model_validate_json(json_str)
        assert m == m2


# --- TranscriptSegment ---


class TestTranscriptSegment:
    def test_valid(self):
        seg = TranscriptSegment(start=0.0, duration=5.5, text="Hello world")
        assert seg.start == 0.0
        assert seg.duration == 5.5
        assert seg.text == "Hello world"

    def test_missing_text(self):
        with pytest.raises(ValidationError):
            TranscriptSegment(start=0.0, duration=1.0)


# --- Transcript ---


class TestTranscript:
    def test_minimal(self):
        t = Transcript(
            video_id="abc",
            language="en",
            segments=[],
            fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            transcript_source="youtube-transcript-api",
        )
        assert t.is_generated is None
        assert t.available_languages == []
        assert t.errors == []

    def test_with_segments(self):
        t = Transcript(
            video_id="abc",
            language="en",
            is_generated=False,
            segments=[
                TranscriptSegment(start=0.0, duration=2.0, text="Hello"),
                TranscriptSegment(start=2.0, duration=3.0, text="World"),
            ],
            fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            transcript_source="youtube-transcript-api",
            available_languages=["en", "es"],
        )
        assert len(t.segments) == 2
        assert t.segments[0].text == "Hello"
        assert t.available_languages == ["en", "es"]

    def test_round_trip(self):
        t = Transcript(
            video_id="abc",
            language="en",
            segments=[TranscriptSegment(start=0.0, duration=1.0, text="Hi")],
            fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            transcript_source="youtube-transcript-api",
        )
        data = t.model_dump()
        t2 = Transcript.model_validate(data)
        assert t == t2


# --- FetchResult ---


class TestFetchResult:
    def test_success(self):
        r = FetchResult(
            video_id="abc",
            success=True,
            metadata_path=Path("out/abc/metadata.json"),
        )
        assert r.success is True
        assert r.errors == []
        assert r.media_paths == []

    def test_failure(self):
        r = FetchResult(
            video_id="abc",
            success=False,
            errors=["Video not found"],
        )
        assert r.success is False
        assert len(r.errors) == 1

    def test_round_trip(self):
        r = FetchResult(video_id="abc", success=True)
        data = r.model_dump()
        r2 = FetchResult.model_validate(data)
        assert r == r2


# --- BatchResult ---


class TestBatchResult:
    def test_valid(self):
        b = BatchResult(
            total=3,
            succeeded=2,
            failed=1,
            results=[
                FetchResult(video_id="a", success=True),
                FetchResult(video_id="b", success=True),
                FetchResult(video_id="c", success=False, errors=["fail"]),
            ],
        )
        assert b.total == 3
        assert b.succeeded == 2
        assert b.failed == 1
        assert len(b.results) == 3

    def test_missing_results(self):
        with pytest.raises(ValidationError):
            BatchResult(total=0, succeeded=0, failed=0)


# --- FetchOptions ---


class TestFetchOptions:
    def test_defaults(self):
        opts = FetchOptions()
        assert opts.out == Path("./out")
        assert opts.languages == ["en"]
        assert opts.allow_generated is True
        assert opts.allow_any_language is False
        assert opts.download == "none"
        assert opts.max_height is None
        assert opts.format == "best"
        assert opts.audio_format == "best"
        assert opts.force is False
        assert opts.force_metadata is False
        assert opts.force_transcript is False
        assert opts.force_media is False
        assert opts.retries == 3
        assert opts.rate_limit == 2.0
        assert opts.workers == 3
        assert opts.fail_fast is False
        assert opts.verbose is False
        assert opts.yt_api_key is None
        assert opts.ffmpeg_fallback == "error"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("YT_FETCH_RETRIES", "5")
        monkeypatch.setenv("YT_FETCH_VERBOSE", "true")
        monkeypatch.setenv("YT_FETCH_DOWNLOAD", "audio")
        opts = FetchOptions()
        assert opts.retries == 5
        assert opts.verbose is True
        assert opts.download == "audio"

    def test_invalid_download_value(self):
        with pytest.raises(ValidationError):
            FetchOptions(download="invalid")

    def test_invalid_ffmpeg_fallback(self):
        with pytest.raises(ValidationError):
            FetchOptions(ffmpeg_fallback="invalid")

    def test_explicit_values(self):
        opts = FetchOptions(
            out=Path("/tmp/test"),
            languages=["es", "en"],
            workers=8,
            yt_api_key="test-key-123",
        )
        assert opts.out == Path("/tmp/test")
        assert opts.languages == ["es", "en"]
        assert opts.workers == 8
        assert opts.yt_api_key == "test-key-123"
