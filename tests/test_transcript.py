"""Tests for yt_fetch.services.transcript."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from yt_fetch.core.models import Transcript
from yt_fetch.core.options import FetchOptions
from yt_fetch.services.transcript import (
    TranscriptError,
    TranscriptNotFound,
    _select_transcript,
    get_transcript,
    list_available_transcripts,
)


# --- Helpers for mocking youtube-transcript-api objects ---


@dataclass
class FakeTranscriptEntry:
    """Mimics a Transcript object from youtube-transcript-api's TranscriptList."""

    language_code: str
    language: str
    is_generated: bool

    def fetch(self):
        return FakeFetchedTranscript(
            video_id="test_vid",
            language_code=self.language_code,
            is_generated=self.is_generated,
            snippets=[
                FakeSnippet(text="Hello", start=0.0, duration=2.0),
                FakeSnippet(text="World", start=2.0, duration=3.0),
            ],
        )


@dataclass
class FakeSnippet:
    text: str
    start: float
    duration: float


@dataclass
class FakeFetchedTranscript:
    video_id: str
    language_code: str
    is_generated: bool
    snippets: list

    def __iter__(self):
        return iter(self.snippets)


# --- _select_transcript ---


class TestSelectTranscript:
    """Test the language selection algorithm."""

    def _make_entries(self, specs):
        """Create FakeTranscriptEntry list from (lang, is_generated) tuples."""
        return [
            FakeTranscriptEntry(
                language_code=lang,
                language=lang,
                is_generated=gen,
            )
            for lang, gen in specs
        ]

    def test_prefers_manual_in_preferred_language(self):
        available = self._make_entries([("en", False), ("en", True), ("es", False)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=True, allow_any_language=False
        )
        assert result.language_code == "en"
        assert result.is_generated is False

    def test_falls_back_to_generated_when_allowed(self):
        available = self._make_entries([("en", True), ("es", False)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=True, allow_any_language=False
        )
        assert result.language_code == "en"
        assert result.is_generated is True

    def test_skips_generated_when_not_allowed(self):
        available = self._make_entries([("en", True), ("es", False)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=False, allow_any_language=False
        )
        assert result is None

    def test_language_priority_order(self):
        available = self._make_entries([("es", False), ("en", False)])
        result = _select_transcript(
            available, languages=["en", "es"], allow_generated=True, allow_any_language=False
        )
        assert result.language_code == "en"

    def test_second_language_fallback(self):
        available = self._make_entries([("es", False), ("de", False)])
        result = _select_transcript(
            available, languages=["en", "es"], allow_generated=True, allow_any_language=False
        )
        assert result.language_code == "es"

    def test_allow_any_language_manual_first(self):
        available = self._make_entries([("ja", False), ("ja", True)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=True, allow_any_language=True
        )
        assert result.language_code == "ja"
        assert result.is_generated is False

    def test_allow_any_language_generated_fallback(self):
        available = self._make_entries([("ja", True)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=True, allow_any_language=True
        )
        assert result.language_code == "ja"
        assert result.is_generated is True

    def test_allow_any_language_no_generated(self):
        available = self._make_entries([("ja", True)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=False, allow_any_language=True
        )
        assert result is None

    def test_no_transcripts_available(self):
        result = _select_transcript(
            [], languages=["en"], allow_generated=True, allow_any_language=True
        )
        assert result is None

    def test_preferred_language_beats_any_language(self):
        available = self._make_entries([("ja", False), ("en", True)])
        result = _select_transcript(
            available, languages=["en"], allow_generated=True, allow_any_language=True
        )
        assert result.language_code == "en"


# --- get_transcript ---


class TestGetTranscript:
    """Test get_transcript with mocked youtube-transcript-api."""

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_success(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        entries = [
            FakeTranscriptEntry(language_code="en", language="English", is_generated=False),
        ]
        mock_api.list.return_value = iter(entries)

        options = FetchOptions(languages=["en"])
        result = get_transcript("dQw4w9WgXcQ", options)

        assert isinstance(result, Transcript)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.language == "en"
        assert result.is_generated is False
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello"
        assert result.transcript_source == "youtube-transcript-api"
        assert result.available_languages == ["en"]

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_transcript_not_found(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.list.return_value = iter([])

        options = FetchOptions(languages=["en"])
        with pytest.raises(TranscriptNotFound, match="TRANSCRIPT_NOT_FOUND"):
            get_transcript("xxxxxxxxxxx", options)

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_transcripts_disabled(self, mock_api_class):
        from youtube_transcript_api import TranscriptsDisabled

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.list.side_effect = TranscriptsDisabled("xxxxxxxxxxx")

        options = FetchOptions(languages=["en"])
        with pytest.raises(TranscriptError, match="Transcripts are disabled"):
            get_transcript("xxxxxxxxxxx", options)

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_generated_transcript_when_allowed(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        entries = [
            FakeTranscriptEntry(language_code="en", language="English (auto)", is_generated=True),
        ]
        mock_api.list.return_value = iter(entries)

        options = FetchOptions(languages=["en"], allow_generated=True)
        result = get_transcript("dQw4w9WgXcQ", options)
        assert result.is_generated is True

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_generated_rejected_when_not_allowed(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        entries = [
            FakeTranscriptEntry(language_code="en", language="English (auto)", is_generated=True),
        ]
        mock_api.list.return_value = iter(entries)

        options = FetchOptions(languages=["en"], allow_generated=False)
        with pytest.raises(TranscriptNotFound):
            get_transcript("dQw4w9WgXcQ", options)

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_any_language_fallback(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        entries = [
            FakeTranscriptEntry(language_code="ja", language="Japanese", is_generated=False),
        ]
        mock_api.list.return_value = iter(entries)

        options = FetchOptions(languages=["en"], allow_any_language=True)
        result = get_transcript("dQw4w9WgXcQ", options)
        assert result.language == "ja"


# --- list_available_transcripts ---


class TestListAvailableTranscripts:
    """Test list_available_transcripts."""

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_lists_all(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        entries = [
            FakeTranscriptEntry(language_code="en", language="English", is_generated=False),
            FakeTranscriptEntry(language_code="en", language="English (auto)", is_generated=True),
            FakeTranscriptEntry(language_code="es", language="Spanish", is_generated=False),
        ]
        mock_api.list.return_value = iter(entries)

        result = list_available_transcripts("dQw4w9WgXcQ")
        assert len(result) == 3
        assert result[0] == {"language_code": "en", "language": "English", "is_generated": False}
        assert result[1]["is_generated"] is True
        assert result[2]["language_code"] == "es"

    @patch("yt_fetch.services.transcript.YouTubeTranscriptApi")
    def test_disabled(self, mock_api_class):
        from youtube_transcript_api import TranscriptsDisabled

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.list.side_effect = TranscriptsDisabled("xxxxxxxxxxx")

        with pytest.raises(TranscriptError, match="Transcripts are disabled"):
            list_available_transcripts("xxxxxxxxxxx")
