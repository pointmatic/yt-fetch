# tech_spec.md — yt-fetch: AI-Ready YouTube Content Extraction

## Overview

This document defines the technical architecture, dependencies, module design, and implementation details for yt-fetch. For feature requirements see `features.md`; for task breakdown see `stories.md`.

---

## Runtime & Tooling

- **Python**: 3.14.3 (per `.tool-versions`)
- **Virtual environment**: Pyve (https://github.com/pointmatic/pyve)
- **Package manager**: `pip` with `pyproject.toml` (PEP 621)
- **Linting/formatting**: `ruff`
- **Testing**: `pytest`

---

## Dependencies

### Runtime Dependencies

| Package | Purpose |
|---|---|
| `yt-dlp` | Metadata extraction and media download |
| `youtube-transcript-api` | Transcript fetching (no API key required) |
| `pydantic` >= 2.0 | Typed data models, settings, and validation |
| `click` | CLI framework with subcommands |
| `pyyaml` | Config file parsing (`yt_fetch.yaml`) |
| `rich` | Console output, progress bars, and logging |

### Optional Runtime Dependencies

| Package | Purpose |
|---|---|
| `google-api-python-client` | YouTube Data API v3 metadata (requires API key) |
| `tiktoken` | Token count estimation for LLM context window planning |

### System Dependencies (optional)

| Tool | Purpose |
|---|---|
| `ffmpeg` | Audio extraction and media transcoding |

### Development Dependencies

| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support (if needed) |
| `ruff` | Linting and formatting |
| `pyve` | Virtual environment management (https://github.com/pointmatic/pyve) |

---

## Package Structure

```
yt_fetch/
    __init__.py              # version, public API exports
    __main__.py              # python -m yt_fetch support
    cli.py                   # Click CLI entry point and subcommands
    core/
        __init__.py
        models.py            # Pydantic models (Metadata, Transcript, FetchResult, etc.)
        errors.py            # FetchErrorCode, FetchPhase, FetchError, exception hierarchy
        options.py           # FetchOptions Pydantic settings model
        pipeline.py          # per-video orchestration
        writer.py            # output file writing (JSON, txt, VTT, SRT)
        logging.py           # structured logging setup (console + JSONL)
    services/
        __init__.py
        id_parser.py         # URL/ID parsing and validation
        resolver.py          # playlist/channel URL → video ID list resolution
        metadata.py          # metadata retrieval (yt-dlp + YouTube API backends)
        transcript.py        # transcript fetching with language selection
        media.py             # media download via yt-dlp
    utils/
        __init__.py
        time_fmt.py          # VTT/SRT timestamp formatting
        txt_formatter.py     # LLM-ready transcript.txt formatting (paragraph chunking, timestamps)
        hashing.py           # SHA-256 content hashing for change detection
        token_counter.py     # token count estimation via tiktoken (optional dep)
        retry.py             # exponential backoff retry decorator
        rate_limit.py        # token bucket rate limiter
        ffmpeg.py            # ffmpeg detection and helpers
tests/
    __init__.py
    conftest.py              # shared fixtures, mocks
    test_id_parser.py        # URL/ID parsing for all forms
    test_models.py           # model validation
    test_transcript_format.py # VTT/SRT timestamp correctness
    test_writer.py           # output file generation
    test_pipeline.py         # pipeline idempotency, error handling
    test_errors.py           # error classification, exception hierarchy
    test_resolver.py         # playlist/channel URL resolution
    test_txt_formatter.py    # LLM-ready transcript formatting
    test_hashing.py          # content hash computation
    test_token_counter.py    # token count estimation
    test_bundle.py           # video bundle output
    test_cli.py              # CLI smoke tests
    integration/
        __init__.py
        test_fetch_live.py   # live network tests (guarded by RUN_INTEGRATION=1)
```

---

## Key Component Design

### ID Parser (`services/id_parser.py`)

```python
def parse_video_id(input_str: str) -> str | None
    """Extract a YouTube video ID from a URL or raw ID string.
    Returns None if input cannot be parsed."""

def parse_many(inputs: list[str]) -> list[str]
    """Parse multiple inputs, deduplicate, preserve order."""

def load_ids_from_file(path: Path) -> list[str]
    """Load IDs from a text file (one per line), CSV, or JSONL."""
```

Supported URL patterns:
- `https://www.youtube.com/watch?v=<id>`
- `https://youtu.be/<id>`
- `https://www.youtube.com/shorts/<id>`
- URLs with extra query parameters
- Raw 11-character IDs

Validation: 11 characters, alphanumeric plus `-` and `_`. Do not over-reject.

### Resolver Service (`services/resolver.py`)

```python
def resolve_playlist(url: str, max_videos: int | None = None) -> list[str]
    """Resolve a playlist URL to an ordered list of video IDs."""

def resolve_channel(url: str, max_videos: int | None = None) -> list[str]
    """Resolve a channel URL to a list of video IDs (uploads)."""

def resolve_input(input_str: str, max_videos: int | None = None) -> list[str]
    """Detect input type (video ID, URL, playlist, channel) and resolve to video IDs."""
```

- Uses `yt-dlp`'s `extract_info(url, download=False)` with `extract_flat=True` for efficient ID-only extraction
- Supports playlist URLs (`/playlist?list=...`) and channel URLs (`/@handle`, `/channel/...`)
- `max_videos` limits the number of IDs returned (useful for large channels)
- Writes resolved IDs to `<out>/resolved_ids.json` for reproducibility
- Resolved IDs feed into the standard pipeline (deduplication via `parse_many()` applies)

### Metadata Service (`services/metadata.py`)

```python
def get_metadata(video_id: str, options: FetchOptions) -> Metadata
    """Fetch metadata using the configured backend."""

def _yt_dlp_backend(video_id: str) -> dict
    """Extract metadata via yt-dlp. Default, no API key required."""

def _youtube_api_backend(video_id: str, api_key: str) -> dict
    """Extract metadata via YouTube Data API v3. Fallback to yt-dlp on failure."""
```

- Mode A (default): `yt-dlp` — no API key, no login required
- Mode B (optional): YouTube Data API v3 — richer data, requires `YT_FETCH_YT_API_KEY`
- If Mode B fails, automatically fall back to Mode A
- Metadata retrieval is independent from media download

### Transcript Service (`services/transcript.py`)

```python
def get_transcript(video_id: str, options: FetchOptions) -> Transcript
    """Fetch transcript with language selection and fallback logic."""

def list_available_transcripts(video_id: str) -> list[TranscriptInfo]
    """List all available transcripts for a video."""
```

Language selection algorithm:
1. Try each language in `preferred_languages` in order
2. For each language, prefer manual over generated (if `allow_generated` is false)
3. If none found and `allow_any_language` is true, pick best available (manual > generated, prefer English variants)
4. If still none, raise `TranscriptNotFound` (code `TRANSCRIPT_NOT_FOUND`, `retryable=False`)

Edge cases handled:
- Video has no transcript → `TranscriptNotFound` (code `TRANSCRIPT_NOT_FOUND`, `retryable=False`)
- Transcripts disabled by owner → `TranscriptsDisabledError` (code `TRANSCRIPTS_DISABLED`, `retryable=False`)
- Transcripts blocked by region/permissions → `TranscriptError` with appropriate code
- Multiple language variants → follow selection algorithm
- Network failures → `TranscriptServiceError` (code `NETWORK_ERROR`, `retryable=True`); retried internally unless `retries=0`

### Media Service (`services/media.py`)

```python
def download_media(video_id: str, options: FetchOptions, out_dir: Path) -> MediaResult
    """Download video and/or audio via yt-dlp."""

def check_ffmpeg() -> bool
    """Detect whether ffmpeg is installed and accessible."""
```

- Download modes: `none`, `video`, `audio`, `both`
- Respects `max_height` (e.g., 720p) and format preferences
- If ffmpeg is missing and conversion is requested: fail with actionable error or skip conversion (configurable via `ffmpeg_fallback` option)

### Pipeline (`core/pipeline.py`)

```python
async def process_video(video_id: str, options: FetchOptions) -> FetchResult
    """Orchestrate the full per-video workflow."""

async def process_batch(video_ids: list[str], options: FetchOptions) -> BatchResult
    """Process multiple videos with concurrency and error isolation."""
```

Per-video workflow:
1. Create output folder `<out_dir>/<video_id>/`
2. Check cache — skip network fetch where output exists (unless `--force*`)
3. Fetch metadata → write `metadata.json`; if cached, read `metadata.json` back into `Metadata` object
4. Fetch transcript → write `transcript.json`, `transcript.txt`, optionally `.vtt`/`.srt`; if cached, read `transcript.json` back into `Transcript` object
5. Download media (if enabled) → write to `media/` subfolder
6. Return structured `FetchResult` with in-memory `metadata` and `transcript` always populated (when available)

Batch orchestration:
- Use `asyncio` with a semaphore for concurrency (`--workers N`, default 3)
- Per-video error isolation: one failure does not stop the batch (unless `--fail-fast`)
- Rate limiter shared across all workers

### Output Writer (`core/writer.py`)

```python
def write_metadata(metadata: Metadata, out_dir: Path) -> Path
def read_metadata(out_dir: Path, video_id: str) -> Metadata | None
def write_transcript_json(transcript: Transcript, out_dir: Path) -> Path
def read_transcript_json(out_dir: Path, video_id: str) -> Transcript | None
def write_transcript_txt(transcript: Transcript, out_dir: Path) -> Path
def write_transcript_vtt(transcript: Transcript, out_dir: Path) -> Path
def write_transcript_srt(transcript: Transcript, out_dir: Path) -> Path
def write_summary(results: BatchResult, out_dir: Path) -> Path
```

- All writes are **atomic**: write to a temp file, then rename. This prevents partial outputs on crash.
- `transcript.txt` uses LLM-ready formatting (see `utils/txt_formatter.py`)

```python
def write_bundle(result: FetchResult, out_dir: Path) -> Path
    """Write video_bundle.json combining metadata + transcript + errors."""
```

- `video_bundle.json` is written after all other outputs, reflecting the final state
- Only emitted when `FetchOptions.bundle` is `True`

---

## Data Models (`core/models.py`)

All models use Pydantic v2 `BaseModel`.

### `Metadata`
```python
class Metadata(BaseModel):
    video_id: str
    source_url: str
    title: str | None = None
    channel_title: str | None = None
    channel_id: str | None = None
    upload_date: str | None = None          # ISO 8601
    duration_seconds: float | None = None
    description: str | None = None
    tags: list[str] = []
    view_count: int | None = None
    like_count: int | None = None
    fetched_at: datetime
    metadata_source: str                    # "yt-dlp" or "youtube-data-api"
    content_hash: str | None = None         # SHA-256 of canonical fields
    raw: dict | None = None                 # unmodified raw payload
```

### `Transcript`
```python
class TranscriptSegment(BaseModel):
    start: float                            # seconds
    duration: float                         # seconds
    text: str

class Transcript(BaseModel):
    video_id: str
    language: str
    is_generated: bool | None = None
    segments: list[TranscriptSegment]
    fetched_at: datetime
    transcript_source: str                  # "youtube-transcript-api"
    available_languages: list[str] = []
    content_hash: str | None = None         # SHA-256 of concatenated segment text
    token_count: int | None = None          # estimated token count (if tokenizer configured)
    errors: list[str] = []

class VideoBundle(BaseModel):
    """Unified envelope combining all structured data for a single video."""
    video_id: str
    metadata: Metadata | None = None
    transcript: Transcript | None = None
    errors: list[FetchError] = []
    content_hash: str | None = None         # SHA-256 of combined metadata + transcript
    token_count: int | None = None
    fetched_at: datetime
```

### `FetchResult`
```python
class FetchResult(BaseModel):
    video_id: str
    success: bool
    metadata_path: Path | None = None
    transcript_path: Path | None = None
    media_paths: list[Path] = []
    metadata: Metadata | None = None
    transcript: Transcript | None = None
    errors: list[FetchError] = []          # Structured errors (see core/errors.py)

class BatchResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[FetchResult]
```

---

## Error Handling (`core/errors.py`)

Structured error classification for all yt-fetch operations. See `error_handling_features.md` for full motivation and design.

### `FetchErrorCode`
```python
class FetchErrorCode(StrEnum):
    # Content unavailable (permanent or semi-permanent)
    VIDEO_NOT_FOUND = "video_not_found"
    VIDEO_PRIVATE = "video_private"
    VIDEO_DELETED = "video_deleted"
    VIDEO_AGE_RESTRICTED = "video_age_restricted"
    VIDEO_GEO_BLOCKED = "video_geo_blocked"
    TRANSCRIPTS_DISABLED = "transcripts_disabled"
    TRANSCRIPT_NOT_FOUND = "transcript_not_found"

    # Transient / infrastructure
    RATE_LIMITED = "rate_limited"
    SERVICE_ERROR = "service_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"

    # Client-side
    INVALID_VIDEO_ID = "invalid_video_id"
    MISSING_DEPENDENCY = "missing_dependency"
    CONFIGURATION_ERROR = "configuration_error"

    # Catch-all
    UNKNOWN = "unknown"
```

### `FetchPhase`
```python
class FetchPhase(StrEnum):
    METADATA = "metadata"
    TRANSCRIPT = "transcript"
    MEDIA = "media"
```

### `FetchError`
```python
class FetchError(BaseModel):
    code: FetchErrorCode
    message: str
    phase: FetchPhase
    retryable: bool
    video_id: str
    details: dict[str, Any] | None = None
```

### Exception hierarchy
```python
class FetchException(Exception):
    """Base exception for all yt-fetch errors."""
    code: FetchErrorCode
    retryable: bool

# Transcript
class TranscriptError(FetchException): ...
class TranscriptNotFound(TranscriptError): ...       # TRANSCRIPT_NOT_FOUND, retryable=False
class TranscriptsDisabledError(TranscriptError): ...  # TRANSCRIPTS_DISABLED, retryable=False
class TranscriptServiceError(TranscriptError): ...    # SERVICE_ERROR/NETWORK_ERROR/etc, retryable=True

# Metadata
class MetadataError(FetchException): ...
class VideoNotFoundError(MetadataError): ...          # VIDEO_NOT_FOUND, retryable=False
class MetadataServiceError(MetadataError): ...        # SERVICE_ERROR/NETWORK_ERROR/etc, retryable=True

# Media
class MediaError(FetchException): ...
class MediaServiceError(MediaError): ...              # SERVICE_ERROR/NETWORK_ERROR/etc, retryable=True
```

### `_classify_exception()`
Centralized helper that maps upstream exceptions to `FetchErrorCode`. Classification priority:
1. **Exception type** — `youtube-transcript-api` types (`TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable`, etc.) and stdlib types (`ConnectionError`, `TimeoutError`)
2. **HTTP status code** — via `status_code` or `code` attribute (429 → `RATE_LIMITED`, 5xx → `SERVICE_ERROR`)
3. **Message string** — fragile fallback for untyped exceptions

Each known upstream exception type has a dedicated unit test.

---

## Configuration (`core/options.py`)

Uses Pydantic `BaseSettings` for layered config resolution.

```python
class FetchOptions(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="YT_FETCH_",
        yaml_file="yt_fetch.yaml",
    )

    out: Path = Path("./out")
    languages: list[str] = ["en"]
    allow_generated: bool = True
    allow_any_language: bool = False
    download: Literal["none", "video", "audio", "both"] = "none"
    max_height: int | None = None
    format: str = "best"
    audio_format: str = "best"
    force: bool = False
    force_metadata: bool = False
    force_transcript: bool = False
    force_media: bool = False
    retries: int = 3
    rate_limit: float = 2.0                 # requests per second
    workers: int = 3
    fail_fast: bool = False
    verbose: bool = False
    yt_api_key: str | None = None
    ffmpeg_fallback: Literal["error", "skip"] = "error"
    max_videos: int | None = None           # limit videos from playlist/channel
    txt_timestamps: bool = False            # include [MM:SS] markers in transcript.txt
    txt_raw: bool = False                   # bare concatenation (no paragraph formatting)
    txt_gap_threshold: float = 2.0          # silence gap (seconds) for paragraph breaks
    bundle: bool = False                    # emit video_bundle.json per video
    tokenizer: str | None = None            # tiktoken tokenizer name (None = disabled)
```

Precedence: CLI flags → environment variables → `yt_fetch.yaml` → defaults.

---

## CLI Design (`cli.py`)

Built with `click`. Entry point: `yt_fetch` (or `python -m yt_fetch`).

### Subcommands

| Command | Description |
|---|---|
| `yt_fetch fetch` | Full pipeline: metadata + transcript + media |
| `yt_fetch transcript` | Transcript only |
| `yt_fetch metadata` | Metadata only |
| `yt_fetch media` | Media download only |

### Input flags (shared)
- `--id <id>` (repeatable)
- `--file <path>` (text file, one ID per line)
- `--jsonl <path> --id-field <field>` (JSONL input)
- `--playlist <url>` (resolve playlist to video IDs)
- `--channel <url>` (resolve channel to video IDs)
- `--max-videos N` (limit resolved IDs from playlist/channel)

### Exit codes
| Code | Meaning |
|---|---|
| `0` | Success (all IDs processed, or partial failure without `--strict`) |
| `1` | Generic error (bad args, unable to initialize) |
| `2` | Partial failure (some IDs failed, `--strict` mode) |
| `3` | All IDs failed |

---

## Library API (`__init__.py`)

```python
from yt_fetch import fetch_video, fetch_batch, resolve_playlist, resolve_channel

result: FetchResult = fetch_video("dQw4w9WgXcQ", options=FetchOptions(...))
batch: BatchResult = fetch_batch(["id1", "id2"], options=FetchOptions(...))

# Resolve playlist/channel to video IDs
ids: list[str] = resolve_playlist("https://www.youtube.com/playlist?list=PLxxx", max_videos=50)
ids: list[str] = resolve_channel("https://www.youtube.com/@handle", max_videos=100)
```

---

## Cross-Cutting Concerns

### Retry Strategy (`utils/retry.py`)

Exponential backoff with jitter:
- Base delay: 1 second
- Multiplier: 2x
- Max retries: configurable (default 3); set `retries=0` to disable internal retries entirely
- Jitter: ±25%
- Applies to: **transient errors only** (`TranscriptServiceError`, `MetadataServiceError`, `MediaServiceError`)
- Permanently unavailable content (`TranscriptNotFound`, `TranscriptsDisabledError`, `VideoNotFoundError`) is **never retried**
- Library consumers that manage their own retry policy (e.g., via `gentlify`) should set `retries=0`

### Rate Limiting (`utils/rate_limit.py`)

Token bucket algorithm:
- Configurable rate (default 2 RPS); set `rate_limit=0` to disable internal rate limiting
- Shared across all workers in a batch
- Thread-safe implementation
- Library consumers that manage their own throttling externally should set `rate_limit=0`

### LLM Text Formatting (`utils/txt_formatter.py`)

Produces LLM-ready `transcript.txt` from transcript segments.

```python
def format_transcript_txt(
    segments: list[TranscriptSegment],
    is_generated: bool | None = None,
    gap_threshold: float = 2.0,
    timestamps: bool = False,
    raw: bool = False,
) -> str
    """Format transcript segments into LLM-ready plain text."""
```

- **Default mode**: concatenates segment text, inserting paragraph breaks (`\n\n`) when the gap between consecutive segments exceeds `gap_threshold` seconds. Within a paragraph, segments are joined with a single space.
- **Timestamped mode** (`timestamps=True`): prepends `[MM:SS]` at each paragraph boundary for citation support.
- **Raw mode** (`raw=True`): bare concatenation of segment text with spaces, no paragraph formatting. Backward-compatible with pre-v0.6 behavior.
- **Auto-generated notice**: when `is_generated` is true, prepends `[Auto-generated transcript]\n\n` to the output.
- Modes are mutually exclusive: `raw=True` overrides `timestamps`.

### Content Hashing (`utils/hashing.py`)

Deterministic SHA-256 hashing for change detection.

```python
def hash_metadata(metadata: Metadata) -> str
    """SHA-256 of canonical metadata fields (title, description, tags, upload_date, duration_seconds)."""

def hash_transcript(transcript: Transcript) -> str
    """SHA-256 of concatenated segment text."""

def hash_bundle(metadata: Metadata | None, transcript: Transcript | None) -> str
    """SHA-256 of combined metadata + transcript content."""
```

- Canonical field selection ensures hashes are stable across re-fetches when content hasn't changed (e.g., `view_count` changes don't affect the hash).
- All hashes are hex-encoded lowercase strings.

### Token Counting (`utils/token_counter.py`)

Optional token count estimation using `tiktoken`.

```python
def count_tokens(text: str, tokenizer: str = "cl100k_base") -> int
    """Count tokens in text using the specified tiktoken tokenizer."""

def is_tokenizer_available() -> bool
    """Check if tiktoken is installed."""
```

- `tiktoken` is an **optional dependency** — installed via `pip install yt-fetch[tokens]`
- When `tiktoken` is not installed and a tokenizer is requested, a warning is logged and `token_count` is set to `None` (no crash)
- Supported tokenizers: any name accepted by `tiktoken.encoding_for_model()` or `tiktoken.get_encoding()`

### Logging (`core/logging.py`)

- **Console**: concise by default, verbose with `--verbose`. Uses `rich` for formatting.
- **Structured JSONL** (optional): per-video log events with fields:
  - `timestamp`, `level`, `video_id`, `event`, `details`, `error`
- Per-video `logs.jsonl` written to the video's output folder

### Atomic File Writes

All output files are written atomically:
1. Write to `<filename>.tmp` in the same directory
2. `os.rename()` to final path
3. Prevents partial/corrupt files on crash or interrupt

### Caching / Idempotency

- Before each step, check if the output file already exists
- If exists and no `--force*` flag: skip the network fetch for that step
- When skipping a fetch, **read the cached file from disk** and populate the in-memory object (`Metadata` or `Transcript`) so that `FetchResult` always contains the data for library consumers
- Selective force flags: `--force-metadata`, `--force-transcript`, `--force-media`
- `--force` overrides all selective flags

---

## Testing Strategy

### Unit Tests (no network)
- **ID parsing**: all URL forms, raw IDs, invalid inputs, deduplication
- **Models**: Pydantic validation, serialization round-trips
- **Transcript formatting**: VTT/SRT timestamp correctness
- **LLM text formatting**: paragraph chunking at silence gaps, timestamp markers, raw mode, auto-generated notice
- **Content hashing**: deterministic SHA-256 for metadata and transcript, hash changes when content changes
- **Token counting**: correct counts with mock tokenizer, graceful handling when tiktoken not installed
- **Video bundle**: correct structure, includes all fields, written only when `bundle=True`
- **Writer**: output file content verification
- **Rate limiter**: token bucket behavior
- **Error classification**: one test per known upstream exception type (`TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable`, `ConnectionError`, `TimeoutError`, etc.) plus HTTP status code classification and message-string fallback

### Integration Tests (guarded by `RUN_INTEGRATION=1`)
- Fetch metadata for a known video
- Fetch transcript for a known video
- Full pipeline end-to-end
- Batch with mixed valid/invalid IDs
- Resolve a known public playlist to video IDs
- Resolve a known public channel to video IDs

### Pipeline Tests
- Idempotency: re-run without `--force` skips work
- Force flags: re-run with `--force` overwrites
- Error isolation: one bad ID doesn't stop batch
- `--fail-fast`: stops on first error
- Content hashes present in output files
- Token counts present when tokenizer configured, absent when not
- Bundle output present when `--bundle` set, absent when not

---

## Security & Compliance

- No cookies, credentials, or personal tokens stored by default
- API keys read from environment or config file, never logged
- Respect YouTube Terms of Service
- No DRM circumvention or paywalled content access