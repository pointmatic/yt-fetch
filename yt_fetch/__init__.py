"""yt-fetch — YouTube video metadata, transcript, and media fetcher."""

__version__ = "0.4.2"

from yt_fetch.core.models import BatchResult, FetchResult, Metadata, Transcript
from yt_fetch.core.options import FetchOptions


def fetch_video(video_id: str, options: FetchOptions | None = None) -> FetchResult:
    """Fetch metadata, transcript, and optionally media for a single video.

    This is the primary library entry point for single-video processing.

    Args:
        video_id: YouTube video ID or URL.
        options: Configuration options. Uses defaults if not provided.

    Returns:
        FetchResult with metadata, transcript, paths, and any errors.
    """
    from yt_fetch.core.pipeline import process_video
    from yt_fetch.services.id_parser import parse_video_id

    if options is None:
        options = FetchOptions()

    parsed = parse_video_id(video_id)
    if parsed is None:
        return FetchResult(
            video_id=video_id,
            success=False,
            errors=[f"Invalid video ID or URL: {video_id}"],
        )

    return process_video(parsed, options)


def fetch_batch(video_ids: list[str], options: FetchOptions | None = None) -> BatchResult:
    """Fetch metadata, transcript, and optionally media for multiple videos.

    This is the primary library entry point for batch processing.

    Args:
        video_ids: List of YouTube video IDs or URLs.
        options: Configuration options. Uses defaults if not provided.

    Returns:
        BatchResult with per-video results and summary counts.
    """
    from yt_fetch.core.pipeline import process_batch
    from yt_fetch.services.id_parser import parse_many

    if options is None:
        options = FetchOptions()

    parsed = parse_many(video_ids)
    return process_batch(parsed, options)


__all__ = [
    "__version__",
    "fetch_video",
    "fetch_batch",
    "FetchOptions",
    "FetchResult",
    "BatchResult",
    "Metadata",
    "Transcript",
]
