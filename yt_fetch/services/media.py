"""Media download via yt-dlp."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp

from yt_fetch.core.options import FetchOptions
from yt_fetch.utils.ffmpeg import check_ffmpeg

logger = logging.getLogger("yt_fetch")


class MediaError(Exception):
    """Raised when media download fails."""


@dataclass
class MediaResult:
    """Result of a media download operation."""

    video_id: str
    paths: list[Path] = field(default_factory=list)
    skipped: bool = False
    errors: list[str] = field(default_factory=list)


def download_media(
    video_id: str,
    options: FetchOptions,
    out_dir: Path,
) -> MediaResult:
    """Download media for a video using yt-dlp.

    Respects options.download mode (none/video/audio/both),
    max_height, format, audio_format, and ffmpeg_fallback.
    """
    if options.download == "none":
        return MediaResult(video_id=video_id, skipped=True)

    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg:
        if options.ffmpeg_fallback == "skip":
            logger.warning("ffmpeg not found, skipping media download for %s", video_id)
            return MediaResult(
                video_id=video_id,
                skipped=True,
                errors=["ffmpeg not found, skipped media download"],
            )
        else:
            raise MediaError(
                f"ffmpeg is required for media download but was not found. "
                f"Install ffmpeg or set --ffmpeg-fallback=skip."
            )

    media_dir = Path(out_dir) / video_id / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    result = MediaResult(video_id=video_id)
    url = f"https://www.youtube.com/watch?v={video_id}"

    if options.download in ("video", "both"):
        paths = _download_video(url, video_id, options, media_dir)
        result.paths.extend(paths)

    if options.download in ("audio", "both"):
        paths = _download_audio(url, video_id, options, media_dir)
        result.paths.extend(paths)

    return result


def _build_video_format(options: FetchOptions) -> str:
    """Build yt-dlp format string for video download."""
    if options.format != "best":
        return options.format

    if options.max_height:
        return f"bestvideo[height<={options.max_height}]+bestaudio/best[height<={options.max_height}]"

    return "bestvideo+bestaudio/best"


def _build_audio_format(options: FetchOptions) -> str:
    """Build yt-dlp format string for audio-only download."""
    if options.audio_format != "best":
        return f"bestaudio[ext={options.audio_format}]/bestaudio"

    return "bestaudio/best"


def _download_video(
    url: str,
    video_id: str,
    options: FetchOptions,
    media_dir: Path,
) -> list[Path]:
    """Download video via yt-dlp."""
    fmt = _build_video_format(options)
    outtmpl = str(media_dir / f"{video_id}.%(ext)s")

    ydl_opts = {
        "format": fmt,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "merge_output_format": "mp4",
    }

    return _run_yt_dlp(url, video_id, ydl_opts, "video")


def _download_audio(
    url: str,
    video_id: str,
    options: FetchOptions,
    media_dir: Path,
) -> list[Path]:
    """Download audio-only via yt-dlp."""
    fmt = _build_audio_format(options)
    outtmpl = str(media_dir / f"{video_id}_audio.%(ext)s")

    ydl_opts = {
        "format": fmt,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a" if options.audio_format == "best" else options.audio_format,
            }
        ],
    }

    return _run_yt_dlp(url, video_id, ydl_opts, "audio")


def _run_yt_dlp(url: str, video_id: str, ydl_opts: dict, media_type: str) -> list[Path]:
    """Execute yt-dlp download and return list of downloaded file paths."""
    downloaded: list[Path] = []

    def progress_hook(d: dict) -> None:
        if d.get("status") == "finished":
            filename = d.get("filename")
            if filename:
                downloaded.append(Path(filename))

    ydl_opts["progress_hooks"] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise MediaError(
            f"Failed to download {media_type} for {video_id}: {exc}"
        ) from exc

    return downloaded
