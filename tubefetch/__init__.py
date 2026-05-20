# Copyright (c) 2026 Pointmatic
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""yt-fetch — YouTube video metadata, transcript, and media fetcher."""

__version__ = "1.4.2"

from tubefetch.core.errors import FetchError, FetchErrorCode, FetchException, FetchPhase
from tubefetch.core.models import BatchResult, FetchResult, Metadata, Transcript
from tubefetch.core.options import FetchOptions
from tubefetch.services.resolver import resolve_channel, resolve_playlist


def fetch_video(video_id: str, options: FetchOptions | None = None) -> FetchResult:
    """Fetch metadata, transcript, and optionally media for a single video.

    This is the primary library entry point for single-video processing.

    Args:
        video_id: YouTube video ID or URL.
        options: Configuration options. Uses defaults if not provided.

    Returns:
        FetchResult with metadata, transcript, paths, and any errors.
    """
    from tubefetch.core.pipeline import process_video
    from tubefetch.services.id_parser import parse_video_id

    if options is None:
        options = FetchOptions()

    parsed = parse_video_id(video_id)
    if parsed is None:
        return FetchResult(
            video_id=video_id,
            success=False,
            errors=[
                FetchError(
                    code=FetchErrorCode.INVALID_VIDEO_ID,
                    message=f"Invalid video ID or URL: {video_id}",
                    phase=FetchPhase.METADATA,
                    retryable=False,
                    video_id=video_id,
                )
            ],
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
    from tubefetch.core.pipeline import process_batch
    from tubefetch.services.id_parser import parse_many

    if options is None:
        options = FetchOptions()

    parsed = parse_many(video_ids)
    return process_batch(parsed, options)


__all__ = [
    "__version__",
    "fetch_video",
    "fetch_batch",
    "resolve_playlist",
    "resolve_channel",
    "FetchOptions",
    "FetchResult",
    "BatchResult",
    "Metadata",
    "Transcript",
    "FetchError",
    "FetchErrorCode",
    "FetchPhase",
    "FetchException",
]
