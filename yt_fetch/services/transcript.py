"""Transcript fetching via youtube-transcript-api."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api import TranscriptsDisabled

from yt_fetch.core.models import Transcript, TranscriptSegment
from yt_fetch.core.options import FetchOptions

logger = logging.getLogger("yt_fetch")


class TranscriptError(Exception):
    """Raised when transcript fetching fails."""


class TranscriptNotFound(TranscriptError):
    """No transcript available for the requested languages."""


def get_transcript(video_id: str, options: FetchOptions) -> Transcript:
    """Fetch a transcript for a video using the configured language preferences.

    Language selection algorithm:
    1. Try preferred languages in order.
    2. Prefer manual over generated (when allow_generated is False).
    3. Fall back to any available language (when allow_any_language is True).
    4. Raise TranscriptNotFound when nothing is available.
    """
    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)
    except TranscriptsDisabled as exc:
        raise TranscriptError(
            f"Transcripts are disabled for {video_id}"
        ) from exc
    except Exception as exc:
        raise TranscriptError(
            f"Failed to list transcripts for {video_id}: {exc}"
        ) from exc

    available = list(transcript_list)
    available_languages = [t.language_code for t in available]

    selected = _select_transcript(
        available,
        languages=options.languages,
        allow_generated=options.allow_generated,
        allow_any_language=options.allow_any_language,
    )

    if selected is None:
        raise TranscriptNotFound(
            f"TRANSCRIPT_NOT_FOUND: No transcript for {video_id} "
            f"in languages {options.languages}. "
            f"Available: {available_languages}"
        )

    try:
        fetched = selected.fetch()
    except Exception as exc:
        raise TranscriptError(
            f"Failed to fetch transcript for {video_id}: {exc}"
        ) from exc

    segments = [
        TranscriptSegment(
            start=snippet.start,
            duration=snippet.duration,
            text=snippet.text,
        )
        for snippet in fetched
    ]

    return Transcript(
        video_id=video_id,
        language=fetched.language_code,
        is_generated=fetched.is_generated,
        segments=segments,
        fetched_at=datetime.now(timezone.utc),
        transcript_source="youtube-transcript-api",
        available_languages=available_languages,
    )


def list_available_transcripts(video_id: str) -> list[dict]:
    """List available transcripts for a video.

    Returns a list of dicts with keys: language_code, language, is_generated.
    """
    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)
    except TranscriptsDisabled as exc:
        raise TranscriptError(
            f"Transcripts are disabled for {video_id}"
        ) from exc
    except Exception as exc:
        raise TranscriptError(
            f"Failed to list transcripts for {video_id}: {exc}"
        ) from exc

    return [
        {
            "language_code": t.language_code,
            "language": t.language,
            "is_generated": t.is_generated,
        }
        for t in transcript_list
    ]


def _select_transcript(
    available: list,
    *,
    languages: list[str],
    allow_generated: bool,
    allow_any_language: bool,
) -> object | None:
    """Select the best transcript from available options.

    Priority:
    1. Manual transcript in a preferred language (in order).
    2. Generated transcript in a preferred language (if allow_generated).
    3. Any manual transcript (if allow_any_language).
    4. Any generated transcript (if allow_any_language and allow_generated).
    5. None.
    """
    by_lang: dict[str, list] = {}
    for t in available:
        by_lang.setdefault(t.language_code, []).append(t)

    for lang in languages:
        candidates = by_lang.get(lang, [])
        manual = [t for t in candidates if not t.is_generated]
        generated = [t for t in candidates if t.is_generated]

        if manual:
            return manual[0]
        if allow_generated and generated:
            return generated[0]

    if allow_any_language:
        all_manual = [t for t in available if not t.is_generated]
        all_generated = [t for t in available if t.is_generated]

        if all_manual:
            return all_manual[0]
        if allow_generated and all_generated:
            return all_generated[0]

    return None
