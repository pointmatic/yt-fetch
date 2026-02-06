"""Tests for yt_fetch.services.metadata."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from yt_fetch.core.models import Metadata
from yt_fetch.core.options import FetchOptions
from yt_fetch.services.metadata import (
    MetadataError,
    _map_yt_dlp_info,
    _map_youtube_api_item,
    _parse_iso8601_duration,
    get_metadata,
)


SAMPLE_YT_DLP_INFO = {
    "id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
    "fulltitle": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "channel": "Rick Astley",
    "uploader": "Rick Astley",
    "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "upload_date": "20091025",
    "duration": 212,
    "description": "The official video for Never Gonna Give You Up",
    "tags": ["rick astley", "never gonna give you up"],
    "view_count": 1_500_000_000,
    "like_count": 15_000_000,
}


class TestMapYtDlpInfo:
    """Test _map_yt_dlp_info field mapping."""

    def test_full_mapping(self):
        m = _map_yt_dlp_info("dQw4w9WgXcQ", SAMPLE_YT_DLP_INFO)
        assert m.video_id == "dQw4w9WgXcQ"
        assert m.title == "Rick Astley - Never Gonna Give You Up (Official Music Video)"
        assert m.source_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert m.channel_title == "Rick Astley"
        assert m.channel_id == "UCuAXFkgsw1L7xaCfnd5JJOw"
        assert m.upload_date == "2009-10-25"
        assert m.duration_seconds == 212
        assert m.description == "The official video for Never Gonna Give You Up"
        assert m.tags == ["rick astley", "never gonna give you up"]
        assert m.view_count == 1_500_000_000
        assert m.like_count == 15_000_000
        assert m.metadata_source == "yt-dlp"
        assert isinstance(m.fetched_at, datetime)
        assert m.raw == SAMPLE_YT_DLP_INFO

    def test_minimal_info(self):
        info = {
            "id": "xxxxxxxxxxx",
            "webpage_url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
        }
        m = _map_yt_dlp_info("xxxxxxxxxxx", info)
        assert m.video_id == "xxxxxxxxxxx"
        assert m.title is None
        assert m.channel_title is None
        assert m.upload_date is None
        assert m.duration_seconds is None
        assert m.tags == []
        assert m.raw == info

    def test_upload_date_formatting(self):
        info = {"id": "abc", "upload_date": "20231215"}
        m = _map_yt_dlp_info("abc", info)
        assert m.upload_date == "2023-12-15"

    def test_upload_date_non_standard(self):
        info = {"id": "abc", "upload_date": "2023-12-15"}
        m = _map_yt_dlp_info("abc", info)
        assert m.upload_date == "2023-12-15"

    def test_fallback_to_uploader(self):
        info = {"id": "abc", "uploader": "Some Uploader"}
        m = _map_yt_dlp_info("abc", info)
        assert m.channel_title == "Some Uploader"

    def test_fallback_to_fulltitle(self):
        info = {"id": "abc", "fulltitle": "Full Title Here"}
        m = _map_yt_dlp_info("abc", info)
        assert m.title == "Full Title Here"

    def test_none_tags_becomes_empty_list(self):
        info = {"id": "abc", "tags": None}
        m = _map_yt_dlp_info("abc", info)
        assert m.tags == []

    def test_source_url_fallback(self):
        info = {"id": "abc"}
        m = _map_yt_dlp_info("abc", info)
        assert m.source_url == "https://www.youtube.com/watch?v=abc"


class TestYtDlpBackend:
    """Test _yt_dlp_backend with mocked yt-dlp."""

    @patch("yt_fetch.services.metadata.yt_dlp.YoutubeDL")
    def test_success(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = SAMPLE_YT_DLP_INFO
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        from yt_fetch.services.metadata import _yt_dlp_backend

        result = _yt_dlp_backend("dQw4w9WgXcQ")
        assert isinstance(result, Metadata)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.title == "Rick Astley - Never Gonna Give You Up (Official Music Video)"

    @patch("yt_fetch.services.metadata.yt_dlp.YoutubeDL")
    def test_download_error(self, mock_ydl_class):
        import yt_dlp as real_yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = real_yt_dlp.utils.DownloadError("Video not found")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        from yt_fetch.services.metadata import _yt_dlp_backend

        with pytest.raises(MetadataError, match="Failed to extract metadata"):
            _yt_dlp_backend("nonexistent123")

    @patch("yt_fetch.services.metadata.yt_dlp.YoutubeDL")
    def test_none_result(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = None
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        from yt_fetch.services.metadata import _yt_dlp_backend

        with pytest.raises(MetadataError, match="No metadata returned"):
            _yt_dlp_backend("xxxxxxxxxxx")


class TestGetMetadata:
    """Test get_metadata with backend selection."""

    @patch("yt_fetch.services.metadata._yt_dlp_backend")
    def test_default_uses_yt_dlp(self, mock_backend):
        mock_backend.return_value = _map_yt_dlp_info("dQw4w9WgXcQ", SAMPLE_YT_DLP_INFO)
        options = FetchOptions()

        result = get_metadata("dQw4w9WgXcQ", options)
        assert result.video_id == "dQw4w9WgXcQ"
        mock_backend.assert_called_once_with("dQw4w9WgXcQ")

    @patch("yt_fetch.services.metadata._yt_dlp_backend")
    @patch("yt_fetch.services.metadata._youtube_api_backend")
    def test_api_key_tries_api_first(self, mock_api, mock_ydl):
        mock_api.return_value = _map_yt_dlp_info("dQw4w9WgXcQ", SAMPLE_YT_DLP_INFO)
        options = FetchOptions(yt_api_key="test-key")

        result = get_metadata("dQw4w9WgXcQ", options)
        mock_api.assert_called_once_with("dQw4w9WgXcQ", "test-key")
        mock_ydl.assert_not_called()

    @patch("yt_fetch.services.metadata._yt_dlp_backend")
    @patch("yt_fetch.services.metadata._youtube_api_backend")
    def test_api_failure_falls_back_to_yt_dlp(self, mock_api, mock_ydl):
        mock_api.side_effect = MetadataError("API quota exceeded")
        mock_ydl.return_value = _map_yt_dlp_info("dQw4w9WgXcQ", SAMPLE_YT_DLP_INFO)
        options = FetchOptions(yt_api_key="test-key")

        result = get_metadata("dQw4w9WgXcQ", options)
        mock_api.assert_called_once()
        mock_ydl.assert_called_once_with("dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"


# --- ISO 8601 Duration Parsing ---


class TestParseIso8601Duration:
    """Test _parse_iso8601_duration."""

    def test_minutes_and_seconds(self):
        assert _parse_iso8601_duration("PT4M13S") == 253.0

    def test_hours_minutes_seconds(self):
        assert _parse_iso8601_duration("PT1H2M3S") == 3723.0

    def test_seconds_only(self):
        assert _parse_iso8601_duration("PT30S") == 30.0

    def test_minutes_only(self):
        assert _parse_iso8601_duration("PT5M") == 300.0

    def test_hours_only(self):
        assert _parse_iso8601_duration("PT2H") == 7200.0

    def test_invalid_format(self):
        assert _parse_iso8601_duration("not a duration") is None

    def test_empty_string(self):
        assert _parse_iso8601_duration("") is None


# --- YouTube API Item Mapping ---


SAMPLE_API_RESPONSE = {
    "items": [
        {
            "id": "dQw4w9WgXcQ",
            "snippet": {
                "title": "Rick Astley - Never Gonna Give You Up",
                "channelTitle": "Rick Astley",
                "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "publishedAt": "2009-10-25T06:57:33Z",
                "description": "The official video",
                "tags": ["rick", "astley"],
            },
            "contentDetails": {
                "duration": "PT3M33S",
            },
            "statistics": {
                "viewCount": "1500000000",
                "likeCount": "15000000",
            },
        }
    ]
}


class TestMapYoutubeApiItem:
    """Test _map_youtube_api_item field mapping."""

    def test_full_mapping(self):
        item = SAMPLE_API_RESPONSE["items"][0]
        m = _map_youtube_api_item("dQw4w9WgXcQ", item, SAMPLE_API_RESPONSE)
        assert m.video_id == "dQw4w9WgXcQ"
        assert m.title == "Rick Astley - Never Gonna Give You Up"
        assert m.channel_title == "Rick Astley"
        assert m.channel_id == "UCuAXFkgsw1L7xaCfnd5JJOw"
        assert m.upload_date == "2009-10-25"
        assert m.duration_seconds == 213.0
        assert m.description == "The official video"
        assert m.tags == ["rick", "astley"]
        assert m.view_count == 1_500_000_000
        assert m.like_count == 15_000_000
        assert m.metadata_source == "youtube-data-api"
        assert m.raw == SAMPLE_API_RESPONSE

    def test_minimal_item(self):
        item = {"id": "xxxxxxxxxxx", "snippet": {}, "contentDetails": {}, "statistics": {}}
        m = _map_youtube_api_item("xxxxxxxxxxx", item, {"items": [item]})
        assert m.video_id == "xxxxxxxxxxx"
        assert m.title is None
        assert m.channel_title is None
        assert m.duration_seconds is None
        assert m.view_count is None
        assert m.tags == []

    def test_missing_statistics(self):
        item = {
            "id": "abc",
            "snippet": {"title": "Test"},
            "contentDetails": {"duration": "PT1M"},
        }
        m = _map_youtube_api_item("abc", item, {"items": [item]})
        assert m.view_count is None
        assert m.like_count is None
        assert m.duration_seconds == 60.0


# --- YouTube API Backend ---


class TestYoutubeApiBackend:
    """Test _youtube_api_backend with mocked Google API client."""

    @pytest.fixture(autouse=True)
    def _mock_google_api(self):
        """Inject fake googleapiclient modules into sys.modules."""
        import sys
        import types

        mock_build = MagicMock()
        self.mock_build = mock_build

        fake_discovery = types.ModuleType("googleapiclient.discovery")
        fake_discovery.build = mock_build

        fake_errors = types.ModuleType("googleapiclient.errors")
        fake_errors.HttpError = type("HttpError", (Exception,), {})

        fake_googleapiclient = types.ModuleType("googleapiclient")
        fake_googleapiclient.discovery = fake_discovery
        fake_googleapiclient.errors = fake_errors

        saved = {}
        for mod_name in ("googleapiclient", "googleapiclient.discovery", "googleapiclient.errors"):
            saved[mod_name] = sys.modules.get(mod_name)
        sys.modules["googleapiclient"] = fake_googleapiclient
        sys.modules["googleapiclient.discovery"] = fake_discovery
        sys.modules["googleapiclient.errors"] = fake_errors

        yield

        for mod_name, original in saved.items():
            if original is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original

    def test_success(self):
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = SAMPLE_API_RESPONSE
        mock_videos.list.return_value = mock_list
        mock_service = MagicMock()
        mock_service.videos.return_value = mock_videos
        self.mock_build.return_value = mock_service

        from yt_fetch.services.metadata import _youtube_api_backend

        result = _youtube_api_backend("dQw4w9WgXcQ", "fake-key")
        assert isinstance(result, Metadata)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.metadata_source == "youtube-data-api"
        self.mock_build.assert_called_once_with("youtube", "v3", developerKey="fake-key")

    def test_video_not_found(self):
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {"items": []}
        mock_videos.list.return_value = mock_list
        mock_service = MagicMock()
        mock_service.videos.return_value = mock_videos
        self.mock_build.return_value = mock_service

        from yt_fetch.services.metadata import _youtube_api_backend

        with pytest.raises(MetadataError, match="Video not found via YouTube API"):
            _youtube_api_backend("nonexistent11", "fake-key")

    def test_api_error(self):
        self.mock_build.side_effect = Exception("API key invalid")

        from yt_fetch.services.metadata import _youtube_api_backend

        with pytest.raises(MetadataError, match="YouTube API error"):
            _youtube_api_backend("dQw4w9WgXcQ", "bad-key")
