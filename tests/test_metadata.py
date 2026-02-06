"""Tests for yt_fetch.services.metadata."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from yt_fetch.core.models import Metadata
from yt_fetch.core.options import FetchOptions
from yt_fetch.services.metadata import MetadataError, _map_yt_dlp_info, get_metadata


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
        mock_api.side_effect = NotImplementedError("not implemented")
        mock_ydl.return_value = _map_yt_dlp_info("dQw4w9WgXcQ", SAMPLE_YT_DLP_INFO)
        options = FetchOptions(yt_api_key="test-key")

        result = get_metadata("dQw4w9WgXcQ", options)
        mock_api.assert_called_once()
        mock_ydl.assert_called_once_with("dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"
