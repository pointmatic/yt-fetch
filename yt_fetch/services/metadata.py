"""Metadata retrieval (yt-dlp + YouTube API backends)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import yt_dlp

from yt_fetch.core.models import Metadata
from yt_fetch.core.options import FetchOptions

logger = logging.getLogger("yt_fetch")


class MetadataError(Exception):
    """Raised when metadata extraction fails."""


def get_metadata(video_id: str, options: FetchOptions) -> Metadata:
    """Fetch metadata using the configured backend.

    Uses YouTube Data API v3 if yt_api_key is set, falling back to yt-dlp.
    Otherwise uses yt-dlp directly.
    """
    if options.yt_api_key:
        try:
            return _youtube_api_backend(video_id, options.yt_api_key)
        except Exception as exc:
            logger.warning(
                "YouTube API backend failed for %s, falling back to yt-dlp: %s",
                video_id,
                exc,
            )

    return _yt_dlp_backend(video_id)


def _yt_dlp_backend(video_id: str) -> Metadata:
    """Extract metadata via yt-dlp. Default, no API key required."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "no_color": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise MetadataError(f"Failed to extract metadata for {video_id}: {exc}") from exc

    if info is None:
        raise MetadataError(f"No metadata returned for {video_id}")

    return _map_yt_dlp_info(video_id, info)


def _map_yt_dlp_info(video_id: str, info: dict) -> Metadata:
    """Map yt-dlp info dict to Metadata model."""
    upload_date_raw = info.get("upload_date")
    upload_date = None
    if upload_date_raw:
        if len(upload_date_raw) == 8 and upload_date_raw.isdigit():
            upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"
        else:
            upload_date = upload_date_raw

    return Metadata(
        video_id=video_id,
        source_url=info.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}"),
        title=info.get("title") or info.get("fulltitle"),
        channel_title=info.get("channel") or info.get("uploader"),
        channel_id=info.get("channel_id"),
        upload_date=upload_date,
        duration_seconds=info.get("duration"),
        description=info.get("description"),
        tags=info.get("tags") or [],
        view_count=info.get("view_count"),
        like_count=info.get("like_count"),
        fetched_at=datetime.now(timezone.utc),
        metadata_source="yt-dlp",
        raw=info,
    )


def _youtube_api_backend(video_id: str, api_key: str) -> Metadata:
    """Extract metadata via YouTube Data API v3.

    Placeholder — will be implemented in Story 4.3.
    """
    raise NotImplementedError("YouTube API backend not yet implemented")
