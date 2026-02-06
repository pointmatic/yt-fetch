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

    Requires the optional `google-api-python-client` package.
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise MetadataError(
            "google-api-python-client is required for YouTube API backend. "
            "Install with: pip install yt-fetch[youtube-api]"
        ) from exc

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id,
        )
        response = request.execute()
    except HttpError as exc:
        raise MetadataError(
            f"YouTube API request failed for {video_id}: {exc}"
        ) from exc
    except Exception as exc:
        raise MetadataError(
            f"YouTube API error for {video_id}: {exc}"
        ) from exc

    items = response.get("items", [])
    if not items:
        raise MetadataError(f"Video not found via YouTube API: {video_id}")

    return _map_youtube_api_item(video_id, items[0], response)


def _map_youtube_api_item(video_id: str, item: dict, raw_response: dict) -> Metadata:
    """Map a YouTube Data API v3 video item to Metadata model."""
    snippet = item.get("snippet", {})
    content_details = item.get("contentDetails", {})
    statistics = item.get("statistics", {})

    duration_iso = content_details.get("duration")
    duration_seconds = _parse_iso8601_duration(duration_iso) if duration_iso else None

    upload_date = snippet.get("publishedAt", "")[:10] or None

    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title=snippet.get("title"),
        channel_title=snippet.get("channelTitle"),
        channel_id=snippet.get("channelId"),
        upload_date=upload_date,
        duration_seconds=duration_seconds,
        description=snippet.get("description"),
        tags=snippet.get("tags", []),
        view_count=int(statistics["viewCount"]) if "viewCount" in statistics else None,
        like_count=int(statistics["likeCount"]) if "likeCount" in statistics else None,
        fetched_at=datetime.now(timezone.utc),
        metadata_source="youtube-data-api",
        raw=raw_response,
    )


def _parse_iso8601_duration(duration: str) -> float | None:
    """Parse an ISO 8601 duration (e.g. PT4M13S) to seconds."""
    import re

    match = re.match(
        r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$",
        duration,
    )
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return float(hours * 3600 + minutes * 60 + seconds)
