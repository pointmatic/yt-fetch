# tech_spec.md — YouTube Fetch + Transcript Collector (Python)

## Overview

This document defines the technical architecture, dependencies, module design, and implementation details for the YouTube Fetch + Transcript Collector project. For feature requirements see `features.md`; for task breakdown see `stories.md`.

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
        options.py           # FetchOptions Pydantic settings model
        pipeline.py          # per-video orchestration
        writer.py            # output file writing (JSON, txt, VTT, SRT)
        logging.py           # structured logging setup (console + JSONL)
    services/
        __init__.py
        id_parser.py         # URL/ID parsing and validation
        metadata.py          # metadata retrieval (yt-dlp + YouTube API backends)
        transcript.py        # transcript fetching with language selection
        media.py             # media download via yt-dlp
    utils/
        __init__.py
        time_fmt.py          # VTT/SRT timestamp formatting
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
4. If still none, return structured `TRANSCRIPT_NOT_FOUND` error

Edge cases handled:
- Video has no transcript → structured error in output
- Transcripts blocked by region/permissions → structured error
- Multiple language variants → follow selection algorithm
- Network failures → retry per retry policy

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
2. Check cache — skip steps where output exists (unless `--force*`)
3. Fetch metadata → write `metadata.json`
4. Fetch transcript → write `transcript.json`, `transcript.txt`, optionally `.vtt`/`.srt`
5. Download media (if enabled) → write to `media/` subfolder
6. Return structured `FetchResult`

Batch orchestration:
- Use `asyncio` with a semaphore for concurrency (`--workers N`, default 3)
- Per-video error isolation: one failure does not stop the batch (unless `--fail-fast`)
- Rate limiter shared across all workers

### Output Writer (`core/writer.py`)

```python
def write_metadata(metadata: Metadata, out_dir: Path) -> Path
def write_transcript_json(transcript: Transcript, out_dir: Path) -> Path
def write_transcript_txt(transcript: Transcript, out_dir: Path) -> Path
def write_transcript_vtt(transcript: Transcript, out_dir: Path) -> Path
def write_transcript_srt(transcript: Transcript, out_dir: Path) -> Path
def write_summary(results: BatchResult, out_dir: Path) -> Path
```

- All writes are **atomic**: write to a temp file, then rename. This prevents partial outputs on crash.
- `transcript.txt` is plain text without timestamps (for human reading and LLM ingestion)

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
    errors: list[str] = []
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
    errors: list[str] = []

class BatchResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[FetchResult]
```

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
from yt_fetch import fetch_video, fetch_batch

result: FetchResult = fetch_video("dQw4w9WgXcQ", options=FetchOptions(...))
batch: BatchResult = fetch_batch(["id1", "id2"], options=FetchOptions(...))
```

---

## Cross-Cutting Concerns

### Retry Strategy (`utils/retry.py`)

Exponential backoff with jitter:
- Base delay: 1 second
- Multiplier: 2x
- Max retries: configurable (default 3)
- Jitter: ±25%
- Applies to: network errors, HTTP 429/5xx

### Rate Limiting (`utils/rate_limit.py`)

Token bucket algorithm:
- Configurable rate (default 2 RPS)
- Shared across all workers in a batch
- Thread-safe implementation

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
- If exists and no `--force*` flag: skip that step
- Selective force flags: `--force-metadata`, `--force-transcript`, `--force-media`
- `--force` overrides all selective flags

---

## Testing Strategy

### Unit Tests (no network)
- **ID parsing**: all URL forms, raw IDs, invalid inputs, deduplication
- **Models**: Pydantic validation, serialization round-trips
- **Transcript formatting**: VTT/SRT timestamp correctness
- **Writer**: output file content verification
- **Rate limiter**: token bucket behavior

### Integration Tests (guarded by `RUN_INTEGRATION=1`)
- Fetch metadata for a known video
- Fetch transcript for a known video
- Full pipeline end-to-end
- Batch with mixed valid/invalid IDs

### Pipeline Tests
- Idempotency: re-run without `--force` skips work
- Force flags: re-run with `--force` overwrites
- Error isolation: one bad ID doesn't stop batch
- `--fail-fast`: stops on first error

---

## Security & Compliance

- No cookies, credentials, or personal tokens stored by default
- API keys read from environment or config file, never logged
- Respect YouTube Terms of Service
- No DRM circumvention or paywalled content access