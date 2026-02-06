"""Tests for yt_fetch.services.media and yt_fetch.utils.ffmpeg."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_fetch.core.options import FetchOptions
from yt_fetch.services.media import (
    MediaError,
    MediaResult,
    _build_audio_format,
    _build_video_format,
    download_media,
)
from yt_fetch.utils.ffmpeg import check_ffmpeg


# --- check_ffmpeg ---


class TestCheckFfmpeg:
    @patch("yt_fetch.utils.ffmpeg.shutil.which")
    def test_found(self, mock_which):
        mock_which.return_value = "/usr/bin/ffmpeg"
        assert check_ffmpeg() is True

    @patch("yt_fetch.utils.ffmpeg.shutil.which")
    def test_not_found(self, mock_which):
        mock_which.return_value = None
        assert check_ffmpeg() is False


# --- _build_video_format ---


class TestBuildVideoFormat:
    def test_default(self):
        opts = FetchOptions()
        assert _build_video_format(opts) == "bestvideo+bestaudio/best"

    def test_max_height(self):
        opts = FetchOptions(max_height=720)
        assert _build_video_format(opts) == "bestvideo[height<=720]+bestaudio/best[height<=720]"

    def test_custom_format(self):
        opts = FetchOptions(format="mp4")
        assert _build_video_format(opts) == "mp4"


# --- _build_audio_format ---


class TestBuildAudioFormat:
    def test_default(self):
        opts = FetchOptions()
        assert _build_audio_format(opts) == "bestaudio/best"

    def test_custom_format(self):
        opts = FetchOptions(audio_format="mp3")
        assert _build_audio_format(opts) == "bestaudio[ext=mp3]/bestaudio"


# --- download_media ---


class TestDownloadMedia:
    def test_download_none_skips(self, tmp_path):
        opts = FetchOptions(download="none")
        result = download_media("dQw4w9WgXcQ", opts, tmp_path)
        assert result.skipped is True
        assert result.paths == []

    @patch("yt_fetch.services.media.check_ffmpeg", return_value=False)
    def test_no_ffmpeg_error(self, mock_ffmpeg, tmp_path):
        opts = FetchOptions(download="video", ffmpeg_fallback="error")
        with pytest.raises(MediaError, match="ffmpeg is required"):
            download_media("dQw4w9WgXcQ", opts, tmp_path)

    @patch("yt_fetch.services.media.check_ffmpeg", return_value=False)
    def test_no_ffmpeg_skip(self, mock_ffmpeg, tmp_path):
        opts = FetchOptions(download="video", ffmpeg_fallback="skip")
        result = download_media("dQw4w9WgXcQ", opts, tmp_path)
        assert result.skipped is True
        assert "ffmpeg not found" in result.errors[0]

    @patch("yt_fetch.services.media._run_yt_dlp")
    @patch("yt_fetch.services.media.check_ffmpeg", return_value=True)
    def test_video_download(self, mock_ffmpeg, mock_run, tmp_path):
        mock_run.return_value = [Path("/tmp/video.mp4")]
        opts = FetchOptions(download="video")
        result = download_media("dQw4w9WgXcQ", opts, tmp_path)
        assert result.skipped is False
        assert len(result.paths) == 1
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[1]["media_type"] if "media_type" in (call_args[1] if call_args[1] else {}) else call_args[0][3] == "video"

    @patch("yt_fetch.services.media._run_yt_dlp")
    @patch("yt_fetch.services.media.check_ffmpeg", return_value=True)
    def test_audio_download(self, mock_ffmpeg, mock_run, tmp_path):
        mock_run.return_value = [Path("/tmp/audio.m4a")]
        opts = FetchOptions(download="audio")
        result = download_media("dQw4w9WgXcQ", opts, tmp_path)
        assert result.skipped is False
        assert len(result.paths) == 1
        mock_run.assert_called_once()

    @patch("yt_fetch.services.media._run_yt_dlp")
    @patch("yt_fetch.services.media.check_ffmpeg", return_value=True)
    def test_both_download(self, mock_ffmpeg, mock_run, tmp_path):
        mock_run.side_effect = [
            [Path("/tmp/video.mp4")],
            [Path("/tmp/audio.m4a")],
        ]
        opts = FetchOptions(download="both")
        result = download_media("dQw4w9WgXcQ", opts, tmp_path)
        assert result.skipped is False
        assert len(result.paths) == 2
        assert mock_run.call_count == 2

    @patch("yt_fetch.services.media.check_ffmpeg", return_value=True)
    def test_creates_media_dir(self, mock_ffmpeg, tmp_path):
        opts = FetchOptions(download="video")
        with patch("yt_fetch.services.media._run_yt_dlp", return_value=[]):
            download_media("dQw4w9WgXcQ", opts, tmp_path)
        assert (tmp_path / "dQw4w9WgXcQ" / "media").is_dir()


# --- _run_yt_dlp ---


class TestRunYtDlp:
    @patch("yt_fetch.services.media.yt_dlp.YoutubeDL")
    def test_success(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        from yt_fetch.services.media import _run_yt_dlp

        result = _run_yt_dlp("https://youtube.com/watch?v=abc", "abc", {}, "video")
        mock_ydl.download.assert_called_once_with(["https://youtube.com/watch?v=abc"])

    @patch("yt_fetch.services.media.yt_dlp.YoutubeDL")
    def test_download_error(self, mock_ydl_class):
        import yt_dlp as real_yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = real_yt_dlp.utils.DownloadError("not found")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        from yt_fetch.services.media import _run_yt_dlp

        with pytest.raises(MediaError, match="Failed to download video"):
            _run_yt_dlp("https://youtube.com/watch?v=abc", "abc", {}, "video")
