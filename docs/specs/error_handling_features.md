# yt-fetch Error Handling — API Enhancement

This document specifies the structured error handling API that yt-factify needs from [yt-fetch](https://github.com/pointmatic/yt-fetch). It is written as a feature request for the yt-fetch library (v0.6.0+), intended to benefit any downstream consumer — not just yt-factify.

---

## Motivation

### The problem today (v0.5.2)

yt-fetch currently reports errors as unstructured strings in `FetchResult.errors: list[str]` and via exception classes (`TranscriptError`, `TranscriptNotFound`, `MetadataError`). The pipeline in `core/pipeline.py` catches these exceptions and serializes them as `f"transcript: {exc}"` strings.

This means callers cannot programmatically distinguish between fundamentally different failure modes:

| Failure mode | Current representation | What the caller needs to know |
|---|---|---|
| Transcripts disabled by channel owner | `TranscriptError("Transcripts are disabled for ...")` | **Content unavailable** — retrying won't help |
| No transcript in requested language | `TranscriptNotFound("TRANSCRIPT_NOT_FOUND: ...")` | **Content unavailable** — try different language or wait |
| YouTube API returns HTTP 429 | `TranscriptError("Failed to fetch transcript: ...")` | **Transient** — retry after backoff |
| YouTube API returns HTTP 500 | `TranscriptError("Failed to fetch transcript: ...")` | **Transient** — retry after backoff |
| Network timeout / DNS failure | `TranscriptError("Failed to fetch transcript: ...")` | **Transient** — retry after backoff |
| Video is private or deleted | `MetadataError("Failed to extract metadata: ...")` | **Content unavailable** — video doesn't exist |
| yt-dlp extraction fails | `MetadataError("Failed to extract metadata: ...")` | **Ambiguous** — could be transient or permanent |

All of the "transient" cases produce the same `TranscriptError` with different message strings. Callers must resort to fragile substring matching to classify errors.

### Real-world use case: channel reliability profiling

yt-factify maintains a per-channel ledger that tracks transcript fetch outcomes over time, bucketed by video age (hours since upload). This data reveals each channel's "caption readiness" profile — e.g., "this channel's videos always have captions after 48 hours but never before 24 hours."

For this to work, yt-factify must distinguish:

- **Transcript genuinely unavailable** (captions not yet generated, disabled by owner) → counts toward the channel's age-bucketed availability profile.
- **Infrastructure failure** (network down, YouTube outage, rate limiting) → says nothing about the channel; should not pollute availability counters.

Without structured error codes from yt-fetch, this distinction is impossible to make reliably.

### Who else benefits

Any yt-fetch consumer that needs to make retry/skip/alert decisions benefits from structured errors:

- **Batch processors** — skip permanently unavailable videos, retry transient failures.
- **Monitoring dashboards** — separate "YouTube is having issues" from "these channels don't have captions."
- **Scheduling systems** — re-queue transient failures with backoff, drop permanent failures.

---

## Proposed API

### 1. `FetchErrorCode` enum

A string enum classifying every error into a machine-readable category.

```python
from enum import StrEnum

class FetchErrorCode(StrEnum):
    """Machine-readable error classification for yt-fetch operations."""

    # --- Content unavailable (permanent or semi-permanent) ---
    VIDEO_NOT_FOUND = "video_not_found"
    VIDEO_PRIVATE = "video_private"
    VIDEO_DELETED = "video_deleted"
    VIDEO_AGE_RESTRICTED = "video_age_restricted"
    VIDEO_GEO_BLOCKED = "video_geo_blocked"
    TRANSCRIPTS_DISABLED = "transcripts_disabled"
    TRANSCRIPT_NOT_FOUND = "transcript_not_found"

    # --- Transient / infrastructure ---
    RATE_LIMITED = "rate_limited"
    SERVICE_ERROR = "service_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"

    # --- Client-side ---
    INVALID_VIDEO_ID = "invalid_video_id"
    MISSING_DEPENDENCY = "missing_dependency"
    CONFIGURATION_ERROR = "configuration_error"

    # --- Catch-all ---
    UNKNOWN = "unknown"
```

### 2. `FetchError` model

A structured error object replacing the current `str` entries in error lists.

```python
from enum import StrEnum
from typing import Any
from pydantic import BaseModel

class FetchPhase(StrEnum):
    """Pipeline phase where an error occurred."""
    METADATA = "metadata"
    TRANSCRIPT = "transcript"
    MEDIA = "media"

class FetchError(BaseModel):
    """A structured error from a yt-fetch operation."""

    code: FetchErrorCode
    message: str                            # Human-readable detail
    phase: FetchPhase                       # Pipeline phase (enum, not str)
    retryable: bool                         # Hint: is this worth retrying?
    video_id: str                           # Which video this error relates to
    details: dict[str, Any] | None = None   # Optional extra context
```

**`retryable`** is a hint, not a guarantee. Callers may still choose to retry non-retryable errors (e.g., `transcript_not_found` might resolve if the caller waits for YouTube to generate auto-captions). When yt-fetch is used as a library with `retries=0`, the caller is responsible for all retry logic; the `retryable` field tells the caller whether retrying is worthwhile.

**`details`** carries optional context such as:
- `{"http_status": 429, "retry_after": 30}` for rate limiting
- `{"available_languages": ["en", "es", "fr"]}` for language mismatch
- `{"reason": "Join this channel to get access"}` for membership-gated content

### 3. Updated `FetchResult`

```python
class FetchResult(BaseModel):
    video_id: str
    success: bool
    metadata_path: Path | None = None
    transcript_path: Path | None = None
    media_paths: list[Path] = []
    metadata: Metadata | None = None
    transcript: Transcript | None = None
    errors: list[FetchError] = []          # CHANGED: FetchError instead of str
```

**No backward compatibility shim.** The library is pre-1.0 and not yet published on PyPI, so there are no external consumers of the old `errors: list[str]` API. The type changes directly from `list[str]` to `list[FetchError]`.

### 4. Updated exception hierarchy

The internal exception classes gain an `error_code` attribute so that callers who catch exceptions (rather than inspecting `FetchResult`) also get structured classification.

```python
class FetchException(Exception):
    """Base exception for all yt-fetch errors."""
    def __init__(self, message: str, code: FetchErrorCode, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable

# --- Transcript exceptions ---

class TranscriptError(FetchException):
    """Transcript fetch failed."""

class TranscriptNotFound(TranscriptError):
    """No transcript available for the requested languages."""
    def __init__(self, message: str):
        super().__init__(message, code=FetchErrorCode.TRANSCRIPT_NOT_FOUND, retryable=False)

class TranscriptsDisabledError(TranscriptError):
    """Transcripts are disabled for this video."""
    def __init__(self, message: str):
        super().__init__(message, code=FetchErrorCode.TRANSCRIPTS_DISABLED, retryable=False)

class TranscriptServiceError(TranscriptError):
    """Transient service error during transcript fetch."""
    def __init__(self, message: str, code: FetchErrorCode = FetchErrorCode.SERVICE_ERROR):
        super().__init__(message, code=code, retryable=True)

# --- Metadata exceptions ---

class MetadataError(FetchException):
    """Metadata fetch failed."""

class VideoNotFoundError(MetadataError):
    """Video does not exist or is inaccessible."""
    def __init__(self, message: str, code: FetchErrorCode = FetchErrorCode.VIDEO_NOT_FOUND):
        super().__init__(message, code=code, retryable=False)

class MetadataServiceError(MetadataError):
    """Transient service error during metadata fetch."""
    def __init__(self, message: str, code: FetchErrorCode = FetchErrorCode.SERVICE_ERROR):
        super().__init__(message, code=code, retryable=True)

# --- Media exceptions ---

class MediaError(FetchException):
    """Media download failed."""

class MediaServiceError(MediaError):
    """Transient service error during media download."""
    def __init__(self, message: str, code: FetchErrorCode = FetchErrorCode.SERVICE_ERROR):
        super().__init__(message, code=code, retryable=True)
```

### 5. Error classification in `services/transcript.py`

The key change is in `get_transcript()`, which currently catches all exceptions as generic `TranscriptError`. The proposed classification:

```python
@retry(retryable=(TranscriptServiceError,))  # Only retry transient errors
def get_transcript(video_id: str, options: FetchOptions) -> Transcript:
    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)
    except TranscriptsDisabled as exc:
        raise TranscriptsDisabledError(
            f"Transcripts are disabled for {video_id}"
        ) from exc
    except ConnectionError as exc:
        raise TranscriptServiceError(
            f"Network error listing transcripts for {video_id}: {exc}",
            code=FetchErrorCode.NETWORK_ERROR,
        ) from exc
    except Exception as exc:
        # Inspect for HTTP status codes if available
        code = _classify_exception(exc)
        if code in (FetchErrorCode.RATE_LIMITED, FetchErrorCode.SERVICE_ERROR,
                     FetchErrorCode.NETWORK_ERROR, FetchErrorCode.TIMEOUT):
            raise TranscriptServiceError(
                f"Transient error for {video_id}: {exc}", code=code
            ) from exc
        raise TranscriptError(
            f"Failed to list transcripts for {video_id}: {exc}",
            code=code, retryable=False,
        ) from exc

    # ... language selection ...

    if selected is None:
        raise TranscriptNotFound(
            f"No transcript for {video_id} in languages {options.languages}. "
            f"Available: {available_languages}"
        )

    # ... fetch selected transcript ...
```

### 6. Helper: `_classify_exception()`

A utility that classifies exceptions into error codes. **Exception type is checked first** (reliable), with message-string heuristics as a fallback (fragile but better than `UNKNOWN`).

```python
from youtube_transcript_api import (
    TranscriptsDisabled,
    NoTranscriptFound,
    NoTranscriptAvailable,
    VideoUnavailable,
)

def _classify_exception(exc: Exception) -> FetchErrorCode:
    """Best-effort classification of an exception into a FetchErrorCode.

    Priority: exception type → HTTP status → exception message string.
    """
    # --- 1. Classify by exception type (most reliable) ---
    if isinstance(exc, TranscriptsDisabled):
        return FetchErrorCode.TRANSCRIPTS_DISABLED
    if isinstance(exc, (NoTranscriptFound, NoTranscriptAvailable)):
        return FetchErrorCode.TRANSCRIPT_NOT_FOUND
    if isinstance(exc, VideoUnavailable):
        return FetchErrorCode.VIDEO_NOT_FOUND
    if isinstance(exc, (ConnectionError, OSError)):
        return FetchErrorCode.NETWORK_ERROR
    if isinstance(exc, TimeoutError):
        return FetchErrorCode.TIMEOUT

    # --- 2. Classify by HTTP status code (if available) ---
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status == 429:
        return FetchErrorCode.RATE_LIMITED
    if isinstance(status, int) and 500 <= status < 600:
        return FetchErrorCode.SERVICE_ERROR

    # --- 3. Fallback: classify by message string (fragile) ---
    exc_str = str(exc).lower()
    if "timeout" in exc_str:
        return FetchErrorCode.TIMEOUT
    if "connection" in exc_str or "dns" in exc_str:
        return FetchErrorCode.NETWORK_ERROR
    if "private" in exc_str:
        return FetchErrorCode.VIDEO_PRIVATE
    if "not found" in exc_str or "not exist" in exc_str or "unavailable" in exc_str:
        return FetchErrorCode.VIDEO_NOT_FOUND
    if "age" in exc_str and "restrict" in exc_str:
        return FetchErrorCode.VIDEO_AGE_RESTRICTED
    if "disabled" in exc_str:
        return FetchErrorCode.TRANSCRIPTS_DISABLED

    return FetchErrorCode.UNKNOWN
```

Each known upstream exception type should have a dedicated unit test so that dependency upgrades that change exception types are caught immediately.

### 7. Error classification in `core/pipeline.py`

The pipeline converts caught exceptions into `FetchError` objects:

```python
except TranscriptError as exc:
    logger.error("Transcript error for %s: %s", video_id, exc)
    errors.append(FetchError(
        code=exc.code,
        message=str(exc),
        phase=FetchPhase.TRANSCRIPT,
        retryable=exc.retryable,
        video_id=video_id,
    ))
```

### 8. Updated retry decorator usage

Currently, `@retry(retryable=(TranscriptError,))` retries *all* transcript errors including "transcripts disabled." With the new hierarchy, only transient errors are retried:

```python
@retry(retryable=(TranscriptServiceError,))  # NOT TranscriptError
def get_transcript(...):
    ...
```

This prevents wasting retries on permanently unavailable content.

---

## Error code reference

| Code | Phase | Retryable | Meaning |
|------|-------|-----------|---------|
| `video_not_found` | metadata | No | Video ID does not exist on YouTube |
| `video_private` | metadata | No | Video is private |
| `video_deleted` | metadata | No | Video has been deleted |
| `video_age_restricted` | metadata | No | Age-restricted, requires authentication |
| `video_geo_blocked` | metadata | No | Not available in the requester's region |
| `transcripts_disabled` | transcript | No | Channel owner disabled captions for this video |
| `transcript_not_found` | transcript | No | No transcript in requested language(s) |
| `rate_limited` | any | Yes | YouTube returned HTTP 429 |
| `service_error` | any | Yes | YouTube returned HTTP 5xx |
| `network_error` | any | Yes | Connection, DNS, or socket-level failure |
| `timeout` | any | Yes | Request timed out |
| `invalid_video_id` | — | No | Could not parse video ID from input |
| `missing_dependency` | — | No | Required package not installed (e.g., yt-dlp, google-api-python-client) |
| `configuration_error` | — | No | Invalid options or configuration |
| `unknown` | any | No | Unclassified error (fallback) |

---

## Migration path

### For yt-fetch

1. **v0.6.0** — Add `FetchErrorCode`, `FetchPhase`, `FetchError`, updated exception hierarchy. Change `FetchResult.errors` from `list[str]` to `list[FetchError]` directly (no backward compat shim — pre-1.0, no external consumers).

### For yt-factify (and other consumers)

1. After yt-fetch v0.6.0, use `error.code` / `error.retryable` for programmatic decisions.
2. Use `error.code` to decide whether a failure counts toward channel availability profiling (only non-retryable transcript errors) vs. infrastructure monitoring (retryable errors).
3. Set `FetchOptions(retries=0)` to disable yt-fetch's internal retries and let `gentlify` (or equivalent) own the retry policy. The `retryable` hint on `FetchError` tells the external retry layer whether retrying is worthwhile.

---

## Example: yt-factify channel ledger integration

```python
from yt_fetch import FetchErrorCode

result = fetch_video(video_id, opts)

if result.transcript is not None:
    record_success(ledger, channel_id, channel_name, video_id, upload_date)
else:
    transcript_errors = [e for e in result.errors if e.phase == FetchPhase.TRANSCRIPT]
    for err in transcript_errors:
        if err.retryable:
            # Infrastructure issue — don't count against channel profile
            log.info("Transient failure for %s: %s", video_id, err.message)
        else:
            # Content unavailable — counts toward channel availability profile
            record_content_failure(ledger, channel_id, video_id, upload_date, err)
```

---

## Design principles

1. **Structured over stringly-typed** — Error codes and phases are enums, not strings to grep for.
2. **Callers decide policy** — yt-fetch classifies errors and provides `retryable` hints; callers decide what to do with them.
3. **Exception type first** — `_classify_exception()` checks exception types before falling back to message-string heuristics. Each known upstream exception type has a dedicated unit test.
4. **Configurable retries** — Internal retries default to 3 for CLI convenience but can be set to 0 (`FetchOptions(retries=0)`) for library consumers that manage their own retry policy (e.g., via `gentlify`).
5. **Fail-safe classification** — Unknown errors default to `FetchErrorCode.UNKNOWN` with `retryable=False`. The `_classify_exception()` heuristic improves over time without API changes.
6. **No silent swallowing** — Every error is captured in `FetchResult.errors` regardless of classification. Nothing is lost.
