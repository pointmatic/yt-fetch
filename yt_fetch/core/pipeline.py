"""Per-video orchestration pipeline."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from yt_fetch.core.models import BatchResult, FetchResult
from yt_fetch.core.options import FetchOptions
from yt_fetch.core.writer import write_metadata, write_transcript_json
from yt_fetch.services.media import download_media
from yt_fetch.services.metadata import MetadataError, get_metadata
from yt_fetch.services.transcript import TranscriptError, get_transcript
from yt_fetch.utils.rate_limit import TokenBucket

logger = logging.getLogger("yt_fetch")


def process_video(
    video_id: str,
    options: FetchOptions,
    rate_limiter: TokenBucket | None = None,
) -> FetchResult:
    """Run the full fetch pipeline for a single video.

    Steps:
    1. Create output folder <out>/<video_id>/
    2. Fetch metadata (skip if cached, unless --force/--force-metadata)
    3. Fetch transcript (skip if cached, unless --force/--force-transcript)
    4. Download media if enabled (skip if cached, unless --force/--force-media)
    5. Return structured FetchResult
    """
    out_dir = Path(options.out)
    video_dir = out_dir / video_id
    video_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    metadata = None
    transcript = None
    metadata_path: Path | None = None
    transcript_path: Path | None = None
    media_paths: list[Path] = []

    # --- Metadata ---
    metadata_path_candidate = video_dir / "metadata.json"
    should_fetch_metadata = (
        options.force
        or options.force_metadata
        or not metadata_path_candidate.exists()
    )

    if should_fetch_metadata:
        try:
            if rate_limiter:
                rate_limiter.acquire()
            metadata = get_metadata(video_id, options)
            metadata_path = write_metadata(metadata, out_dir)
            logger.info("Wrote metadata for %s", video_id)
        except MetadataError as exc:
            logger.error("Metadata error for %s: %s", video_id, exc)
            errors.append(f"metadata: {exc}")
    else:
        metadata_path = metadata_path_candidate
        logger.debug("Skipping metadata for %s (cached)", video_id)

    # --- Transcript ---
    transcript_path_candidate = video_dir / "transcript.json"
    should_fetch_transcript = (
        options.force
        or options.force_transcript
        or not transcript_path_candidate.exists()
    )

    if should_fetch_transcript:
        try:
            if rate_limiter:
                rate_limiter.acquire()
            transcript = get_transcript(video_id, options)
            transcript_path = write_transcript_json(transcript, out_dir)
            logger.info("Wrote transcript for %s", video_id)
        except TranscriptError as exc:
            logger.error("Transcript error for %s: %s", video_id, exc)
            errors.append(f"transcript: {exc}")
    else:
        transcript_path = transcript_path_candidate
        logger.debug("Skipping transcript for %s (cached)", video_id)

    # --- Media ---
    if options.download != "none":
        media_dir = video_dir / "media"
        should_download_media = (
            options.force
            or options.force_media
            or not media_dir.exists()
            or (media_dir.exists() and not any(media_dir.iterdir()))
        )

        if should_download_media:
            try:
                if rate_limiter:
                    rate_limiter.acquire()
                result = download_media(video_id, options, out_dir)
                media_paths = result.paths
                if result.errors:
                    errors.extend(result.errors)
                if not result.skipped:
                    logger.info("Downloaded media for %s", video_id)
            except Exception as exc:
                logger.error("Media error for %s: %s", video_id, exc)
                errors.append(f"media: {exc}")
        else:
            media_paths = list(media_dir.iterdir()) if media_dir.exists() else []
            logger.debug("Skipping media for %s (cached)", video_id)

    success = len(errors) == 0
    return FetchResult(
        video_id=video_id,
        success=success,
        metadata_path=metadata_path,
        transcript_path=transcript_path,
        media_paths=media_paths,
        metadata=metadata,
        transcript=transcript,
        errors=errors,
    )


def process_batch(video_ids: list[str], options: FetchOptions) -> BatchResult:
    """Process multiple videos with concurrency.

    Uses asyncio with a semaphore to limit concurrent workers.
    Each video is processed in isolation — one failure does not stop others
    unless --fail-fast is set.
    A shared TokenBucket rate limiter is used across all workers.
    """
    rate_limiter = TokenBucket(rate=options.rate_limit)
    return asyncio.run(_async_process_batch(video_ids, options, rate_limiter))


async def _async_process_batch(
    video_ids: list[str], options: FetchOptions, rate_limiter: TokenBucket
) -> BatchResult:
    """Async batch processor with semaphore-based concurrency."""
    semaphore = asyncio.Semaphore(options.workers)
    results: list[FetchResult] = []
    fail_fast_triggered = False

    async def _worker(vid: str) -> FetchResult | None:
        nonlocal fail_fast_triggered
        if fail_fast_triggered:
            return None
        async with semaphore:
            if fail_fast_triggered:
                return None
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, process_video, vid, options, rate_limiter,
            )
            if not result.success and options.fail_fast:
                fail_fast_triggered = True
            return result

    tasks = [asyncio.create_task(_worker(vid)) for vid in video_ids]
    completed = await asyncio.gather(*tasks)

    results = [r for r in completed if r is not None]

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    return BatchResult(
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )
