# stories.md — YouTube Fetch + Transcript Collector (Python)

This is a detailed breakdown of the step-by-step stories (tasks) with detailed checklists that can be completed independently. Stories are organized by phase (identified A, B, C and reference modules defined in `tech_spec.md`).

Each story is numbered (e.g. A.a, A.b, etc. according to the phase), followed by an application version number (e.g. v0.0.1) that will be bumped in the app when the story is completed. Stories that have no code changes will have no version number and no bump. Story titles are suffixed with [Planned] initially and [Done] when completed.

---

## Phase A: Foundation

### Story A.a: v0.0.1 Hello World [Done]

Minimal runnable package with CLI entry point.

- [x] Create `pyproject.toml` with project metadata and dependencies (see tech_spec.md)
- [x] Create `yt_fetch/__init__.py` with `__version__`
- [x] Create `yt_fetch/__main__.py` for `python -m yt_fetch` support
- [x] Create `yt_fetch/cli.py` with a Click group and a `--version` flag
- [x] Verify: `python -m yt_fetch --version` prints version and exits

### Story A.b: v0.0.2 Project Structure [Done]

Full package layout per tech_spec.md.

- [x] Create all package directories: `yt_fetch/core/`, `yt_fetch/services/`, `yt_fetch/utils/`
- [x] Create all `__init__.py` files
- [x] Create `tests/` directory with `conftest.py`
- [x] Create `tests/integration/` directory
- [x] Verify: package imports work (`from yt_fetch.core import models`)

### Story A.c: v0.0.3 Core Models and Options [Done]

Pydantic data models and settings.

- [x] Implement `yt_fetch/core/models.py`:
  - [x] `Metadata` model with all fields per tech_spec.md
  - [x] `TranscriptSegment` model
  - [x] `Transcript` model
  - [x] `FetchResult` model
  - [x] `BatchResult` model
- [x] Implement `yt_fetch/core/options.py`:
  - [x] `FetchOptions` Pydantic `BaseSettings` with all fields per tech_spec.md
  - [x] Environment variable prefix `YT_FETCH_`
  - [x] YAML config file support (`yt_fetch.yaml`)
- [x] Write `tests/test_models.py`:
  - [x] Validation tests for each model
  - [x] Serialization round-trip tests
  - [x] Default values tests for `FetchOptions`

### Story A.d: v0.0.4 Configuration System [Done]

CLI flags, env vars, and YAML config file integration.

- [x] Wire `FetchOptions` into `cli.py` Click commands
- [x] Implement config precedence: CLI flags → env vars → YAML → defaults
- [x] Create a sample `yt_fetch.yaml.example` file
- [x] Verify: CLI flag overrides env var overrides YAML overrides default

### Story A.e: v0.0.5 Logging Framework [Done]

Console and structured JSONL logging.

- [x] Implement `yt_fetch/core/logging.py`:
  - [x] Console logger using `rich` (concise by default, verbose with `--verbose`)
  - [x] Structured JSONL logger with fields: `timestamp`, `level`, `video_id`, `event`, `details`, `error`
- [x] Wire logging into CLI (respect `--verbose` flag)
- [x] Verify: console output is clean; JSONL output is valid JSON per line

---

## Phase B: Core Services

### Story B.a: v0.1.0 Video ID Parsing and Validation [Done]

- [x] Implement `yt_fetch/services/id_parser.py`:
  - [x] `parse_video_id(input_str) -> str | None` — extract ID from URL or raw string
  - [x] `parse_many(inputs) -> list[str]` — parse, deduplicate, preserve order
  - [x] `load_ids_from_file(path) -> list[str]` — load from text, CSV, or JSONL
- [x] Supported URL patterns:
  - [x] `https://www.youtube.com/watch?v=<id>`
  - [x] `https://youtu.be/<id>`
  - [x] `https://www.youtube.com/shorts/<id>`
  - [x] URLs with extra query parameters
  - [x] Raw 11-character IDs
- [x] Validation: 11 chars, alphanumeric + `-` + `_`
- [x] Write `tests/test_id_parser.py`:
  - [x] All URL forms
  - [x] Raw IDs
  - [x] Invalid inputs return `None`
  - [x] Deduplication preserves order
  - [x] File loading (text, CSV, JSONL)

### Story B.b: v0.1.1 Metadata Retrieval (yt-dlp) [Done]

- [x] Implement `yt_fetch/services/metadata.py`:
  - [x] `get_metadata(video_id, options) -> Metadata`
  - [x] `_yt_dlp_backend(video_id) -> dict` — extract metadata via yt-dlp
- [x] Map yt-dlp raw output to `Metadata` model fields
- [x] Store raw payload in `Metadata.raw`
- [x] Handle errors: video not found, private video, network failure
- [x] Write unit tests with mocked yt-dlp responses

### Story B.c: v0.1.2 Metadata Retrieval (YouTube Data API v3, optional) [Done]

- [x] Implement `_youtube_api_backend(video_id, api_key) -> dict` in `metadata.py`
- [x] Add `google-api-python-client` as optional dependency
- [x] Implement automatic fallback to yt-dlp backend on API failure
- [x] Guard behind `yt_api_key` option — skip if not configured
- [x] Write unit tests with mocked API responses

### Story B.d: v0.1.3 Transcript Fetching [Done]

- [x] Implement `yt_fetch/services/transcript.py`:
  - [x] `get_transcript(video_id, options) -> Transcript`
  - [x] `list_available_transcripts(video_id) -> list[TranscriptInfo]`
- [x] Language selection algorithm:
  - [x] Try preferred languages in order
  - [x] Prefer manual over generated (when `allow_generated` is false)
  - [x] Fall back to any language (when `allow_any_language` is true)
  - [x] Return structured `TRANSCRIPT_NOT_FOUND` error when none available
- [x] Edge cases:
  - [x] Video has no transcript
  - [x] Transcripts blocked by region/permissions
  - [x] Multiple language variants
- [x] Write unit tests with mocked `youtube-transcript-api` responses

### Story B.e: v0.1.4 Media Download [Done]

- [x] Implement `yt_fetch/services/media.py`:
  - [x] `download_media(video_id, options, out_dir) -> MediaResult`
  - [x] `check_ffmpeg() -> bool`
- [x] Implement `yt_fetch/utils/ffmpeg.py` — ffmpeg detection helper
- [x] Download modes: `none`, `video`, `audio`, `both`
- [x] Respect `max_height` and format preferences
- [x] Handle missing ffmpeg: error or skip based on `ffmpeg_fallback` option
- [x] Write unit tests with mocked yt-dlp download calls

---

## Phase 3: Pipeline & Orchestration

### Story C.a: v0.2.0 Per-Video Pipeline [Done]

- [x] Implement `yt_fetch/core/pipeline.py`:
  - [x] `process_video(video_id, options) -> FetchResult`
- [x] Workflow steps:
  - [x] Create output folder `<out_dir>/<video_id>/`
  - [x] Check cache — skip steps where output exists (unless `--force*`)
  - [x] Fetch metadata → pass to writer
  - [x] Fetch transcript → pass to writer
  - [x] Download media (if enabled) → write to `media/` subfolder
  - [x] Return structured `FetchResult`
- [x] Write `tests/test_pipeline.py` with mocked services

### Story C.b: v0.2.1 Output File Writing [Done]

- [x] Implement `yt_fetch/core/writer.py`:
  - [x] `write_metadata(metadata, out_dir) -> Path`
  - [x] `write_transcript_json(transcript, out_dir) -> Path`
  - [x] `write_transcript_txt(transcript, out_dir) -> Path` — plain text, no timestamps
  - [x] `write_transcript_vtt(transcript, out_dir) -> Path`
  - [x] `write_transcript_srt(transcript, out_dir) -> Path`
  - [x] `write_summary(results, out_dir) -> Path`
- [x] Implement `yt_fetch/utils/time_fmt.py` — VTT/SRT timestamp formatting
- [x] All writes are atomic: write to `.tmp`, then `os.rename()`
- [x] Write `tests/test_writer.py`:
  - [x] Verify JSON output structure
  - [x] Verify transcript.txt has no timestamps
  - [x] Verify VTT/SRT timestamp formatting correctness
- [x] Write `tests/test_transcript_format.py` for timestamp edge cases

### Story C.c: v0.2.2 Caching and Idempotency [Done]

- [x] Before each pipeline step, check if output file exists
- [x] If exists and no `--force*` flag: skip that step, log skip
- [x] Selective force: `--force-metadata`, `--force-transcript`, `--force-media`
- [x] `--force` overrides all selective flags
- [x] Write idempotency tests:
  - [x] Re-run without `--force` skips work
  - [x] Re-run with `--force` overwrites

### Story C.d: v0.2.3 Batch Processing with Concurrency [Done]

- [x] Implement `process_batch(video_ids, options) -> BatchResult` in `pipeline.py`
- [x] Use `asyncio` with semaphore for concurrency (`--workers N`, default 3)
- [x] Per-video error isolation: one failure does not stop the batch
- [x] `--fail-fast` mode: stop on first error
- [x] Write batch tests:
  - [x] Mixed valid/invalid IDs
  - [x] Error isolation
  - [x] Fail-fast behavior

### Story C.e: v0.2.4 Error Handling and Retry [Done]

- [x] Implement `yt_fetch/utils/retry.py`:
  - [x] Exponential backoff with jitter (base 1s, multiplier 2x, jitter ±25%)
  - [x] Configurable max retries (default 3)
  - [x] Applies to network errors, HTTP 429/5xx
- [x] Apply retry decorator to metadata, transcript, and media service calls
- [x] Write retry tests with simulated failures

### Story C.f: v0.2.5 Rate Limiting [Done]

- [x] Implement `yt_fetch/utils/rate_limit.py`:
  - [x] Token bucket algorithm
  - [x] Configurable rate (default 2 RPS)
  - [x] Thread-safe, shared across all workers
- [x] Integrate rate limiter into pipeline before each external call
- [x] Write rate limiter unit tests

### Story C.g: v0.2.6 Summary Reporting [Done]

- [x] At end of batch run, print summary to console:
  - [x] Total IDs processed, successes, failures
  - [x] Transcript successes/failures
  - [x] Media downloads
  - [x] Output directory path
- [x] Optionally write `out/summary.json` with list of results and status
- [x] Write summary output tests

---

## Phase 4: CLI & Library API

### Story D.a: v0.3.0 CLI Subcommands [Done]

- [x] Implement Click subcommands in `yt_fetch/cli.py`:
  - [x] `yt_fetch fetch` — full pipeline (metadata + transcript + media)
  - [x] `yt_fetch transcript` — transcript only
  - [x] `yt_fetch metadata` — metadata only
  - [x] `yt_fetch media` — media download only
- [x] Shared input flags: `--id`, `--file`, `--jsonl` + `--id-field`
- [x] All option flags per features.md (--out, --languages, --download, etc.)
- [x] Exit codes: 0 (success), 1 (generic error), 2 (partial failure + --strict), 3 (all failed)
- [x] Write `tests/test_cli.py` — smoke tests for each subcommand

### Story D.b: v0.3.1 Library API [Done]

- [x] Export public API from `yt_fetch/__init__.py`:
  - [x] `fetch_video(video_id, options) -> FetchResult`
  - [x] `fetch_batch(video_ids, options) -> BatchResult`
- [x] Ensure library usage does not require CLI context
- [x] Write library API tests

---

## Phase E: Testing & Quality

### Story E.a: v0.4.0 Unit Test Suite [Done]

- [x] Ensure all unit tests pass: ID parsing, models, transcript formatting, writer, rate limiter
- [x] Achieve meaningful coverage across core modules (96% overall)
- [x] All tests run without network access

### Story E.b: v0.4.1 Integration Tests [Done]

- [x] Implement `tests/integration/test_fetch_live.py`:
  - [x] Fetch metadata for a known public video
  - [x] Fetch transcript for a known public video
  - [x] Full pipeline end-to-end
  - [x] Batch with mixed valid/invalid IDs
- [x] Guard all integration tests behind `RUN_INTEGRATION=1` env var

### Story E.c: v0.4.2 Pipeline and Error Tests [Done]

- [x] Idempotency: verify skip behavior and force overwrite
- [x] Error isolation: one bad ID doesn't crash batch
- [x] Fail-fast: verify early termination
- [x] Retry: verify backoff on transient failures

---

## Phase F: Documentation & Release

### Story F.a: README and Documentation [Done]

- [x] Create `README.md` with:
  - [x] Project description and features
  - [x] Installation instructions
  - [x] Quick start / usage examples
  - [x] Configuration reference
  - [x] Library API usage
- [x] Create `CHANGELOG.md`

### Story F.b: v0.5.0 Final Testing and Refinement [Done]

- [x] Run full test suite (unit + integration)
- [x] Fix any remaining bugs
- [x] Review and clean up code
- [x] Verify acceptance criteria from features.md:
  - [x] `yt_fetch fetch --id dQw4w9WgXcQ` produces metadata + transcript
  - [x] Batch mode with summary and per-video isolation
  - [x] Re-run without `--force` skips completed work
  - [x] Transcript exports (.txt, .json, .vtt, .srt) are correct
  - [x] Errors are structured and do not crash the run

### Story F.c: v0.5.1 Hyphen or Underscore CLI Command [Done]

- [x] Ensure `yt_fetch` and `yt-fetch` both work
- [x] Correct license and add copyright/license headers to all files

### Story F.d: v0.5.2 Bugfixes and API Feature Improvements [Done]

Bug 1 & 2: Pipeline must always populate in-memory metadata/transcript objects.
Bug 3: Transcript failures must be reported in result.errors.
Issue 4: CLI and library API must behave identically.
Feature Requests: Report available languages on transcript failure.

- [x] Add `read_metadata(out_dir, video_id) -> Metadata | None` to `core/writer.py`
  - [x] Read and parse `<out_dir>/<video_id>/metadata.json` into a `Metadata` model
  - [x] Return `None` if file does not exist or is unparseable
- [x] Add `read_transcript_json(out_dir, video_id) -> Transcript | None` to `core/writer.py`
  - [x] Read and parse `<out_dir>/<video_id>/transcript.json` into a `Transcript` model
  - [x] Return `None` if file does not exist or is unparseable
- [x] Fix `process_video()` in `core/pipeline.py` — metadata cache branch
  - [x] When metadata is cached (skip fetch), call `read_metadata()` to populate the in-memory `metadata` object
  - [x] Assign the loaded `Metadata` to `FetchResult.metadata`
- [x] Fix `process_video()` in `core/pipeline.py` — transcript cache branch
  - [x] When transcript is cached (skip fetch), call `read_transcript_json()` to populate the in-memory `transcript` object
  - [x] Assign the loaded `Transcript` to `FetchResult.transcript`
- [x] Fix error reporting when transcript is unavailable
  - [x] When `get_transcript()` raises `TranscriptError`, probe for available languages and include them in the error message
  - [x] Append a descriptive warning to `result.errors` (e.g., `"No transcript in ['en']; available: ['es', 'fr']"`)
  - [x] Keep `result.success = True` when metadata succeeded but transcript failed (partial failure)
- [x] Update `FetchResult` success logic in `core/pipeline.py`
  - [x] `success` should be `False` only when metadata fetch fails (critical failure)
  - [x] Transcript absence is a warning, not a failure — append to `errors` but do not set `success = False`
- [x] Write/update unit tests
  - [x] Test `read_metadata()` round-trip: write then read back
  - [x] Test `read_transcript_json()` round-trip: write then read back
  - [x] Test pipeline populates `result.metadata` from cache (no force flag)
  - [x] Test pipeline populates `result.transcript` from cache (no force flag)
  - [x] Test `result.errors` contains descriptive message when transcript unavailable
  - [x] Test `result.success` is `True` when metadata succeeds but transcript fails
- [x] Update `features.md`, `tech_spec.md` to reflect the changes
- [x] Verify: `fetch_video("dQw4w9WgXcQ", FetchOptions(download="none"))` returns non-None `metadata` and `transcript` on both first run and cached re-run
- [x] Bump version to `0.5.2` in `__init__.py` and `pyproject.toml`

---

## Phase G: Structured Error Handling

### Story G.a: v0.6.0 Error Models and Exception Hierarchy [Done]

Create `core/errors.py` with all error enums, the `FetchError` model, and the full exception hierarchy.

- [x] Create `yt_fetch/core/errors.py`:
  - [x] `FetchErrorCode(StrEnum)` with all codes per `error_handling_features.md`
  - [x] `FetchPhase(StrEnum)` — `METADATA`, `TRANSCRIPT`, `MEDIA`
  - [x] `FetchError(BaseModel)` — `code`, `message`, `phase`, `retryable`, `video_id`, `details: dict[str, Any] | None`
  - [x] `FetchException(Exception)` base class with `code: FetchErrorCode` and `retryable: bool`
  - [x] Transcript exceptions: `TranscriptError`, `TranscriptNotFound`, `TranscriptsDisabledError`, `TranscriptServiceError`
  - [x] Metadata exceptions: `MetadataError`, `VideoNotFoundError`, `MetadataServiceError`
  - [x] Media exceptions: `MediaError`, `MediaServiceError`
- [x] Add copyright/license header to `core/errors.py`
- [x] Export public types from `yt_fetch/__init__.py`: `FetchErrorCode`, `FetchPhase`, `FetchError`, `FetchException`
- [x] Update `FetchResult.errors` in `core/models.py` from `list[str]` to `list[FetchError]`
- [x] Write `tests/test_errors.py`:
  - [x] Test `FetchErrorCode` enum values and serialization
  - [x] Test `FetchPhase` enum values
  - [x] Test `FetchError` model creation and JSON round-trip
  - [x] Test exception hierarchy: `TranscriptNotFound` is a `TranscriptError` is a `FetchException`
  - [x] Test each exception subclass carries the correct default `code` and `retryable`
- [x] Verify: all existing tests still pass (no regressions from model type change)
- [x] Bump version to `0.6.0` in `__init__.py` and `pyproject.toml`

---

## Phase H: Replace Custom Retry with Gentlify

### Story H.a: v0.6.7 Add Gentlify as Core Dependency [Done]

Replace custom retry implementation with gentlify as the primary retry mechanism.

- [x] Add `gentlify` to core `dependencies` in `pyproject.toml`
- [x] Remove `gentlify` from any optional dependencies (it's now required)
- [x] Update documentation to reflect gentlify as the retry engine (completed in H.c)
- [x] No version bump (dependency-only change)

### Story H.b: v0.6.8 Replace Custom Retry with Gentlify [Done]

Remove `utils/retry.py` and replace all retry decorators with gentlify. Since gentlify is async-native and yt-fetch services are synchronous, use gentlify's `Throttle.execute()` within async wrappers.

- [x] Remove `yt_fetch/utils/retry.py` entirely
- [x] Create `yt_fetch/utils/gentlify_config.py`:
  - [x] `create_throttle(options: FetchOptions) -> Throttle` — creates configured gentlify Throttle instance
  - [x] Configure retry based on `FetchOptions.retries` (0 = no retry, N = max N attempts)
  - [x] Use `RetryConfig(backoff="exponential_jitter", retryable=...)` with custom retryable filter
  - [x] Retryable filter checks `FetchException.retryable` attribute on caught exceptions
  - [x] Exponential backoff for transient errors (retryable=True)
  - [x] No retry for permanent errors (retryable=False)
  - [x] `async_retry_wrapper(func, throttle) -> callable` — wraps sync function for gentlify execution
- [x] Update `services/metadata.py`:
  - [x] Remove `@retry` decorator
  - [x] Keep functions synchronous (no async conversion)
  - [x] Retry logic will be applied at pipeline level via gentlify wrapper
- [x] Update `services/transcript.py`:
  - [x] Remove `@retry` decorator
  - [x] Keep functions synchronous
  - [x] Retry logic will be applied at pipeline level via gentlify wrapper
- [x] Update `services/media.py`:
  - [x] Remove `@retry` decorator
  - [x] Keep functions synchronous
  - [x] Retry logic will be applied at pipeline level via gentlify wrapper
- [x] Update `core/pipeline.py`:
  - [x] Create throttle instance from `FetchOptions` at start of `process_video()`
  - [x] Wrap service calls (get_metadata, get_transcript, download_media) with gentlify async executor
  - [x] Use `asyncio.run()` or existing async context to execute wrapped calls
  - [x] Maintain synchronous pipeline API (internal async execution only)
- [x] Add copyright/license header to `utils/gentlify_config.py`
- [x] Update all tests that mock or test retry behavior:
  - [x] Update `tests/test_pipeline_errors.py` to work with gentlify
  - [x] Remove `tests/test_retry.py` if it exists
  - [x] Add `tests/test_gentlify_config.py` to test throttle configuration (completed in H.c)
- [x] Verify all existing tests pass with gentlify
- [x] Bump version to `0.6.8`

### Story H.c: v0.6.9 Gentlify Integration Testing and Documentation [Done]

Comprehensive testing and documentation for gentlify integration.

- [x] Write `tests/test_gentlify_config.py`:
  - [x] Test retryable errors are retried with exponential backoff
  - [x] Test non-retryable errors fail immediately
  - [x] Test retry exhaustion after max attempts
  - [x] Test `retries=0` disables all retries
  - [x] Test `retries=N` respects max retry count
  - [x] Test different error codes map to correct retry strategies
- [x] Update `README.md`:
  - [x] Document that yt-fetch uses gentlify for retry management
  - [x] Add examples showing retry configuration via `FetchOptions(retries=N)`
  - [x] Explain how `retries=0` disables retries for external retry management
- [x] Update `features.md` and `tech_spec.md`:
  - [x] Replace custom retry documentation with gentlify-based retry
  - [x] Document gentlify configuration and error code mapping
  - [x] Update retry strategy section to reference gentlify
- [x] Verify: all retry behavior works identically to previous custom implementation
- [x] Bump version to `0.6.9`

### Story H.d: v0.7.0 Service Error Classification and Exception Migration [Done]

Migrate services to use centralized exception hierarchy and implement exception classification helper.

- [x] Implement `_classify_exception(exc: Exception) -> FetchErrorCode` in `core/errors.py`:
  - [x] Priority 1: classify by exception type (upstream exceptions from `youtube-transcript-api`, `yt-dlp`)
  - [x] Priority 2: classify by HTTP status code (`status_code` or `code` attribute)
  - [x] Priority 3: classify by message string (fragile fallback)
  - [x] Default: `FetchErrorCode.UNKNOWN`
- [x] Update `services/transcript.py`:
  - [x] Remove local `TranscriptError` and `TranscriptNotFound` class definitions
  - [x] Import exception classes from `core/errors.py`
  - [x] Update error handling to use `_classify_exception()` and raise appropriate exceptions
  - [x] Map `TranscriptsDisabled` → `TranscriptsDisabledError`
  - [x] Map `NoTranscriptFound` → `TranscriptNotFound`
  - [x] Map network/service errors → `TranscriptServiceError` with proper error codes
- [x] Update `services/metadata.py`:
  - [x] Remove local `MetadataError` class definition
  - [x] Import exception classes from `core/errors.py`
  - [x] Update error handling to classify `yt_dlp.utils.DownloadError` properly
  - [x] Raise `VideoNotFoundError`, `MetadataServiceError`, or `MetadataError` as appropriate
- [x] Update `services/media.py`:
  - [x] Remove local `MediaError` class definition
  - [x] Import exception classes from `core/errors.py`
  - [x] Update error handling to classify `yt_dlp.utils.DownloadError` properly
  - [x] Raise `MediaServiceError` or `MediaError` as appropriate
- [x] Write tests in `tests/test_errors.py`:
  - [x] Test `_classify_exception()` for known upstream exception types (already implemented in core/errors.py)
  - [x] Test HTTP status code classification (already implemented)
  - [x] Test message-string fallback (already implemented)
  - [x] Test unknown exception → UNKNOWN (already implemented)
- [x] Update service tests to expect new exception types
- [x] Verify all tests pass (329 passed, 9 skipped)
- [x] Bump version to `0.7.0`

---

## Phase I: CI/CD & Automation

### Story I.a: v0.7.0 CI Workflow [Done]

GitHub Actions workflow for linting, testing, and coverage on every push and PR.

- [x] Create `.github/workflows/ci.yml`
  - [x] Trigger on `push` (all branches) and `pull_request` (all branches)
  - [x] Job: `lint` — install dev deps, run `ruff check .` and `ruff format --check .`
  - [x] Job: `test` — Python version matrix (3.14)
    - [x] Install package with dev extras (`pip install -e ".[dev]"`)
    - [x] Install `pytest-cov`
    - [x] Run `pytest --cov=yt_fetch --cov-report=xml --cov-report=term-missing`
    - [x] Upload `coverage.xml` to Codecov via `codecov/codecov-action@v4`
  - [x] Job: `integration` (optional, manual trigger via `workflow_dispatch` or gated by `RUN_INTEGRATION` secret)
    - [x] Run `RUN_INTEGRATION=1 pytest tests/integration/`
- [x] Add `pytest-cov` to `[project.optional-dependencies] dev` in `pyproject.toml`
- [x] Verify: coverage command works locally (94% coverage, 329 tests passed)

### Story I.b: Codecov Configuration [Done]

Configure Codecov for coverage thresholds and dynamic badge.

- [x] Create `codecov.yml` at repo root
  - [x] Set project coverage target (90%)
  - [x] Set patch coverage target (80%)
  - [x] Exclude `tests/` and `docs/` from coverage reporting
- [x] Enable the Codecov GitHub App on the `pointmatic/yt-fetch` repository (manual step - requires user action)
- [x] Verify: Codecov receives coverage data after a CI run and the badge URL resolves (94.15% coverage reported)

### Story I.c: v0.7.1 License Migration to Apache-2.0 [Done]

Migrate project license from MPL-2.0 to Apache-2.0 to align with current licensing preference.

- [x] Replace `LICENSE` file with Apache-2.0 license text
- [x] Update `pyproject.toml`:
  - [x] Change `license = "MPL-2.0"` to `license = "Apache-2.0"`
  - [x] Bump version to `0.7.1`
- [x] Update all source file headers to use Apache-2.0 boilerplate:
  - [x] Python files (`yt_fetch/**/*.py`, `tests/**/*.py`) - 42 files updated
  - [x] Replace MPL-2.0 header with Apache-2.0 header
  - [x] Keep copyright year and holder unchanged: `Copyright (c) 2026 Pointmatic`
- [x] Verify: all files have consistent Apache-2.0 headers (0 MPL-2.0 references remaining)
- [x] Run linting and tests to ensure no issues introduced (329 passed, 9 skipped)

### Story I.d: v0.7.2 Release Workflow — Auto-Publish to PyPI [Done]

Automated build and publish to PyPI on version tags using OIDC trusted publishing.

- [ ] Configure PyPI trusted publisher (manual step in PyPI project settings - requires user action)
  - [ ] Set GitHub repository: `pointmatic/yt-fetch`
  - [ ] Set workflow file: `release.yml`
  - [ ] Set environment: `pypi`
- [x] Create `.github/workflows/release.yml`
  - [x] Trigger on `push` tags matching `v*`
  - [x] Job: `build`
    - [x] Checkout code
    - [x] Install `build` package
    - [x] Run `python -m build` to produce sdist + wheel in `dist/`
    - [x] Upload `dist/` as a workflow artifact
  - [x] Job: `publish` (depends on `build`)
    - [x] Use environment `pypi` (for OIDC trusted publishing)
    - [x] Download the `dist/` artifact
    - [x] Use `pypa/gh-action-pypi-publish@release/v1` to publish to PyPI
- [x] Add `build` to `[project.optional-dependencies] dev` in `pyproject.toml`
- [ ] Verify: tagging `v0.7.2` and pushing triggers the release workflow; package appears on PyPI (requires PyPI setup and tag push)

### Story I.e: v0.7.3 README Badges [Done]

Add dynamic badges to the top of `README.md`.

- [x] Add badge block immediately after the `# yt-fetch` heading:
  - [x] **CI status** — `![CI](https://github.com/pointmatic/yt-fetch/actions/workflows/ci.yml/badge.svg)`
  - [x] **Codecov** — `[![codecov](https://codecov.io/gh/pointmatic/yt-fetch/graph/badge.svg)](https://codecov.io/gh/pointmatic/yt-fetch)`
  - [x] **PyPI version** — `[![PyPI](https://img.shields.io/pypi/v/yt-fetch)](https://pypi.org/project/yt-fetch/)`
  - [x] **Python versions** — `![Python](https://img.shields.io/pypi/pyversions/yt-fetch)`
  - [x] **License** — `![License](https://img.shields.io/github/license/pointmatic/yt-fetch)`
  - [ ] **Typed** — `![Typed](https://img.shields.io/badge/typed-py.typed-blue)` (deferred - py.typed created in Story J.a, badge can be added later)
- [x] Verify: badges render correctly on GitHub (CI and Codecov badges rendering; PyPI badges will render after first publish)

---

## Phase J: Production Polish

### Story J.a: v0.8.0 PyPI Metadata & Package Quality [Done]

Polish `pyproject.toml` for discoverability and PEP 561 compliance.

- [x] Add `[project.urls]` section to `pyproject.toml`:
  - [x] `Homepage = "https://github.com/pointmatic/yt-fetch"`
  - [x] `Repository = "https://github.com/pointmatic/yt-fetch"`
  - [x] `Bug Tracker = "https://github.com/pointmatic/yt-fetch/issues"`
  - [x] `Changelog = "https://github.com/pointmatic/yt-fetch/blob/main/CHANGELOG.md"`
- [x] Add `keywords` to `[project]`: `["youtube", "transcript", "metadata", "yt-dlp", "video", "ai", "llm", "content-extraction"]`
- [x] Add Trove `classifiers` to `[project]`:
  - [x] `"Development Status :: 4 - Beta"`
  - [x] `"License :: OSI Approved :: Apache Software License"`
  - [x] `"Programming Language :: Python :: 3"`
  - [x] `"Programming Language :: Python :: 3.14"`
  - [x] `"Topic :: Multimedia :: Video"`
  - [x] `"Typing :: Typed"`
- [x] Create `yt_fetch/py.typed` marker file (empty, PEP 561)
- [x] Ensure `py.typed` is included in the built package (setuptools auto-includes package data)
- [x] Bump version to `0.8.0`

### Story J.b: Dependency Management & Maintenance [Done]

Automated dependency updates and contribution guidelines.

- [x] Create `.github/dependabot.yml`
  - [x] Enable `pip` ecosystem updates (weekly schedule)
  - [x] Enable `github-actions` ecosystem updates (weekly schedule)
- [x] Create `CONTRIBUTING.md` with:
  - [x] Development setup instructions (clone, install dev deps, run tests)
  - [x] Code style expectations (ruff, license headers)
  - [x] PR process (branch, test, review)
- [x] Create `SECURITY.md` with vulnerability reporting instructions

### Story J.c: Branch Protection & Repo Settings [Done]

Manual configuration steps for repository hardening.

- [x] Enable branch protection on `main`:
  - [x] Require CI status checks to pass before merge
  - [x] Require at least one review (if collaborators exist)
  - [x] Require branches to be up to date before merge
- [x] Verify: PRs to `main` cannot be merged without passing CI

### Story J.d: Changelog Automation [Done]

Streamline release notes generation.

- [x] Add a `release` section to the release workflow (`.github/workflows/release.yml`):
  - [x] After successful PyPI publish, create a GitHub Release from the tag
  - [x] Auto-generate release notes from merged PR titles since the last tag
- [x] Document the release process in `CONTRIBUTING.md`:
  - [x] Bump version in `pyproject.toml` and `yt_fetch/__init__.py`
  - [x] Update `CHANGELOG.md`
  - [x] Commit, tag `vX.Y.Z`, push tag
  - [x] CI builds and publishes automatically

---

## Phase K: GitHub Pages Documentation

### Story K.a: MkDocs Configuration & Project Structure [Done]

Set up MkDocs with Material theme and create documentation directory structure.

- [x] Install MkDocs dependencies locally:
  - [x] `pip install mkdocs-material mkdocs-git-revision-date-localized-plugin`
- [x] Create `mkdocs.yml` at repository root:
  - [x] Set `site_name: yt-fetch`
  - [x] Set `site_description` from descriptions.md (Friendly Brief Description)
  - [x] Set `site_url: https://pointmatic.github.io/yt-fetch`
  - [x] Set `repo_url: https://github.com/pointmatic/yt-fetch`
  - [x] Configure Material theme with teal/cyan palette (matching brand color `#3ee8c8`)
  - [x] Enable dark/light mode toggle
  - [x] Enable navigation features (instant, tracking, tabs, sections, expand, top)
  - [x] Enable search features (suggest, highlight)
  - [x] Enable content features (code.copy, code.annotate)
  - [x] Set `docs_dir: docs/site`
  - [x] Set `site_dir: site`
  - [x] Configure `nav` structure with Home (index.html) and placeholder pages
  - [x] Add markdown extensions (admonition, pymdownx.details, pymdownx.superfences, pymdownx.highlight, pymdownx.tabbed, tables, toc)
  - [x] Add plugins (search, git-revision-date-localized)
- [x] Create `docs/site/` directory structure
- [x] Create placeholder documentation pages (getting-started.md, usage.md, api.md, advanced.md)
- [x] Add `mkdocs-material` and `mkdocs-git-revision-date-localized-plugin` to `[project.optional-dependencies] dev` in `pyproject.toml`
- [x] Update `.gitignore` to ignore `site/` build output
- [ ] Verify: `mkdocs serve` runs locally and shows placeholder site (requires user to run locally)

### Story K.b: Custom Landing Page [Done]

Create a branded landing page with hero section, quick start, and feature cards.

- [x] Create `docs/site/index.html`:
  - [x] Add HTML5 boilerplate with meta tags (title, description, keywords from descriptions.md)
  - [x] Add inline CSS with dark theme (background `#0a0f14`, accent `#3ee8c8`)
  - [x] Create sticky navigation bar with logo and links (Features, Quick Start, Docs, GitHub)
  - [x] Create hero section:
    - [x] Use wide banner image from `docs/site/images/tubefetch_banner_wide.png`
    - [x] Use One-liner from descriptions.md as `<h1>` with accent color on "AI-ready"
    - [x] Use Friendly Brief Description from descriptions.md as subtitle
    - [x] Add CTA buttons (View on GitHub, Get Started, Documentation)
  - [x] Create Quick Start section:
    - [x] Installation command: `pip install tubefetch`
    - [x] Basic usage example: `yt_fetch fetch --id VIDEO_ID`
    - [x] Styled code block with syntax highlighting
  - [x] Create Features section:
    - [x] Use Feature Cards from descriptions.md (8 cards in responsive grid)
    - [x] Each card with title and description
    - [x] Styled with dark theme and teal accents
  - [x] Ensure responsive design (mobile-friendly)
  - [x] Use system fonts (no external font dependencies)
- [x] Update `README.md` to include header image from `docs/site/images/tubefetch_header_readme.png`
- [ ] Verify: Landing page renders correctly with `mkdocs serve` (requires user to test locally)

### Story K.c: Documentation Pages [Done]

Create markdown documentation pages for getting started, usage, and API reference.

- [x] Create `docs/site/getting-started.md`:
  - [x] Installation section (pip, from source, optional dependencies)
  - [x] Prerequisites (Python 3.14+, optional: ffmpeg for media download)
  - [x] Quick start examples (single video, batch processing, library usage)
  - [x] Configuration overview (CLI flags, config file)
  - [x] Next steps (links to usage guide, API reference)
- [x] Create `docs/site/usage.md`:
  - [x] CLI commands overview (`fetch`, `batch`)
  - [x] Common options (--id, --file, --jsonl, --output, --format, --download)
  - [x] Metadata extraction (yt-dlp vs YouTube API)
  - [x] Transcript fetching (language preference, fallback)
  - [x] Media download (video, audio, both)
  - [x] Caching and force re-fetch
  - [x] Examples for each use case
- [x] Create `docs/site/api.md`:
  - [x] Library API overview
  - [x] `fetch_video()` function signature and examples
  - [x] `FetchOptions` configuration class
  - [x] `FetchResult` output model
  - [x] `Metadata`, `Transcript` models
  - [x] Error handling (`FetchException`, `FetchErrorCode`)
  - [x] Batch processing with `process_batch()`
- [x] Create `docs/site/advanced.md`:
  - [x] Retry configuration (gentlify integration)
  - [x] Rate limiting (token bucket algorithm)
  - [x] Playlist and channel resolution
  - [x] Custom output formats
  - [x] Integration with AI/LLM pipelines
- [x] Update `mkdocs.yml` nav to include all pages
- [x] Verify: All pages render correctly with proper navigation and cross-links (created in Story K.a)

### Story K.d: GitHub Actions Deployment Workflow [Done]

Automate MkDocs deployment to GitHub Pages via GitHub Actions.

- [x] Create `.github/workflows/deploy-docs.yml`:
  - [x] Trigger on push to `main` branch
  - [x] Trigger on manual `workflow_dispatch`
  - [x] Set permissions: `contents: read`, `pages: write`, `id-token: write`
  - [x] Set concurrency group: `pages` (cancel-in-progress: false)
  - [x] Job: `build`
    - [x] Checkout code
    - [x] Set up Python 3.11
    - [x] Install MkDocs dependencies (`mkdocs-material`, `mkdocs-git-revision-date-localized-plugin`)
    - [x] Run `mkdocs build`
    - [x] Upload site artifact
  - [x] Job: `deploy` (depends on `build`)
    - [x] Use `actions/deploy-pages@v4` to deploy to GitHub Pages
    - [x] Set environment: `github-pages`
- [x] Update `.gitignore` to properly ignore `site/` build output
- [x] Configure GitHub Pages (manual step - requires user action):
  - [x] Go to repository Settings → Pages
  - [x] Set Source to "GitHub Actions"
- [x] Verify: Push to main triggers deployment; site available at `https://pointmatic.github.io/yt-fetch`

### Story K.e: Rename yt-fetch to tubefetch everywhere [Done]

Update all repository references from `yt-fetch` to `tubefetch` in preparation for GitHub repository rename.

- [x] Update `mkdocs.yml`:
  - [x] Change `site_url` to `https://pointmatic.github.io/tubefetch`
  - [x] Change `repo_url` to `https://github.com/pointmatic/tubefetch`
  - [x] Change `repo_name` to `pointmatic/tubefetch`
- [x] Update `pyproject.toml`:
  - [x] Change `Homepage` URL to `https://github.com/pointmatic/tubefetch`
  - [x] Change `Repository` URL to `https://github.com/pointmatic/tubefetch`
  - [x] Change `Bug Tracker` URL to `https://github.com/pointmatic/tubefetch/issues`
  - [x] Change `Changelog` URL to `https://github.com/pointmatic/tubefetch/releases`
- [x] Update `README.md`:
  - [x] Change CI badge URL to `https://github.com/pointmatic/tubefetch/actions/workflows/ci.yml/badge.svg`
  - [x] Change Codecov badge URLs to `codecov.io/gh/pointmatic/tubefetch`
  - [x] Change License badge URL to `https://img.shields.io/github/license/pointmatic/tubefetch`
- [x] Update `CONTRIBUTING.md`:
  - [x] Change clone URL to `https://github.com/pointmatic/tubefetch.git`
  - [x] Change directory name to `cd tubefetch`
- [x] Update `SECURITY.md`:
  - [x] Change issues URL to `https://github.com/pointmatic/tubefetch/issues`
- [x] Update `docs/site/index.html`:
  - [x] Change navigation GitHub link to `https://github.com/pointmatic/tubefetch`
  - [x] Change CTA button GitHub link to `https://github.com/pointmatic/tubefetch`
  - [x] Change footer LICENSE link to `https://github.com/pointmatic/tubefetch/blob/main/LICENSE`
- [x] Update `.github/workflows/release.yml`:
  - [x] Change PyPI environment URL to `https://pypi.org/project/tubefetch/`
- [x] Update `.gitignore`:
  - [x] Change `site/` to `/site/` (only ignore at repository root)
- [x] Update `docs/guides/documentation-setup-guide.md`:
  - [x] Remove Step 5 creating `docs/site/.gitignore` (redundant)
  - [x] Update to instruct adding `/site/` to main `.gitignore` at repository root
  - [x] Add note explaining `/site/` vs `site/` difference
- [x] Remove redundant `docs/site/.gitignore` file
- [x] Rename GitHub repository from `yt-fetch` to `tubefetch` (manual step in GitHub Settings)
- [x] Verify: GitHub Pages site moves to `https://pointmatic.github.io/tubefetch`

### Story K.f: Update documentation site commands [Done]

Replace old `yt-fetch` references with `tubefetch` in all documentation pages.

- [x] Update `docs/site/advanced.md`:
  - [x] Replace "yt-fetch uses" with "tubefetch uses" (line 7)
  - [x] Replace "yt-fetch automatically caches" with "tubefetch automatically caches" (line 136)
  - [x] Replace all Python imports `from yt_fetch import` with `from tubefetch import` (14 occurrences)
- [x] Update `docs/site/usage.md`:
  - [x] Replace "using yt-fetch from" with "using tubefetch from" (line 3)
  - [x] Replace all CLI commands `yt_fetch fetch` with `tubefetch fetch` (24 occurrences)
- [x] Update `docs/site/getting-started.md`:
  - [x] Replace "Welcome to yt-fetch!" with "Welcome to tubefetch!" (line 3)
  - [x] Replace "Install yt-fetch using pip" with "Install tubefetch using pip" (line 7)
  - [x] Replace all CLI commands `yt_fetch fetch` with `tubefetch fetch` (3 occurrences)
- [x] Update `docs/site/index.html`:
  - [x] Replace "yt-fetch fetches" with "tubefetch fetches" in meta description (line 7)
  - [x] Replace "yt-fetch fetches" with "tubefetch fetches" in hero paragraph (line 252)
  - [x] Replace CLI command `yt_fetch fetch` with `tubefetch fetch` (line 271)
- [x] Update `docs/site/api.md`:
  - [x] Replace "Use yt-fetch as" with "Use tubefetch as" (line 3)
  - [x] Replace all Python imports `from yt_fetch import` with `from tubefetch import` (9 occurrences)
- [x] Verify: All documentation examples use correct `tubefetch` command and package name

### Story K.g: v0.8.1 Fix CLI command entry point [Done]

Fix `pyproject.toml` to register `tubefetch` command instead of `yt_fetch`/`yt-fetch`.

- [x] Update `pyproject.toml`:
  - [x] Change `[project.scripts]` from `yt_fetch` and `yt-fetch` to `tubefetch`
  - [x] Remove duplicate entry point (keep only `tubefetch`)
- [x] Verify: `pip install tubefetch` registers the `tubefetch` CLI command
- [x] Bump version to `0.8.1` in `pyproject.toml`

### Story K.h: v0.8.2 Fix README references to yt-fetch [Done]

Update README.md to use `tubefetch` instead of `yt-fetch`/`yt_fetch` throughout.

- [x] Update `README.md`:
  - [x] Change title from `# yt-fetch` to `# tubefetch`
  - [x] Replace "yt-fetch is a Python tool" with "tubefetch is a Python tool"
  - [x] Update CLI note to remove `yt_fetch`/`yt-fetch` aliases
  - [x] Replace all CLI examples `yt_fetch` with `tubefetch` (7 occurrences)
  - [x] Replace all Python imports `from yt_fetch import` with `from tubefetch import` (2 occurrences)
  - [x] Replace environment variable prefix `YT_FETCH_` with `TUBEFETCH_`
  - [x] Replace config file name `yt_fetch.yaml` with `tubefetch.yaml`
  - [x] Replace `` `yt-fetch` uses`` with `` `tubefetch` uses`` in retry section
  - [x] Replace test coverage `--cov=yt_fetch` with `--cov=tubefetch`
- [x] Bump version to `0.8.2` in `pyproject.toml`

### Story K.i: v0.9.0 Improve CLI UX with parallel commands and positional args [Done]

Simplify CLI by making commands parallel (all nouns) and accepting video IDs/URLs as positional arguments.

**Current issues:**
- `tubefetch fetch` is redundant (verb + verb)
- `--id` flag is verbose for single/multiple videos
- Commands are inconsistent: `fetch` (verb) vs `metadata`, `transcript`, `media` (nouns)

**Implemented changes:**
- [x] Rename `fetch` command to `all` (fetches everything: metadata + transcript + optional media)
- [x] Accept video IDs/URLs as positional arguments (no `--id` flag needed)
- [x] Support mixed input: IDs, full URLs, short URLs
- [x] Keep `--file`, `--jsonl` flags for batch processing
- [x] Update CLI argument parsing in `cli.py`:
  - [x] Add positional argument `videos` (nargs=-1)
  - [x] Validate and normalize IDs/URLs (via existing `parse_many`)
  - [x] Maintain backward compatibility with `--id` flag (deprecated but functional)
- [x] Update all commands to use consistent pattern:
  - [x] `tubefetch all <videos...>` - fetch metadata + transcript + optional media
  - [x] `tubefetch metadata <videos...>` - fetch metadata only
  - [x] `tubefetch transcript <videos...>` - fetch transcript only
  - [x] `tubefetch media <videos...>` - download media only
- [x] Update help text and examples
- [x] Update README.md with new CLI examples
- [x] Update documentation site pages:
  - [x] Update `getting-started.md` with new command syntax
  - [x] **Rewrite `usage.md` to comprehensively document all four commands:**
    - [x] Add section for `all` command (replaces `fetch`)
    - [x] Add section for `metadata` command with use cases and examples
    - [x] Add section for `transcript` command with language options and examples
    - [x] Add section for `media` command with download modes:
      - [x] Explain `--download video` (merged video+audio MP4)
      - [x] Explain `--download audio` (audio-only M4A extraction)
      - [x] Explain `--download both` (separate video and audio files)
      - [x] Document default behavior (video if no flag specified)
    - [x] Add comparison table showing when to use each command
    - [x] Add examples for common workflows (metadata-only, transcript-only, media-only, everything)
  - [x] Update `index.html` with new command syntax
- [x] Add deprecation warning for `fetch` command (suggest `all` instead)
- [x] Add deprecation warning for `--id` flag (suggest positional args instead)
- [x] Backward compatibility maintained (old syntax still works with warnings)
- [x] Rename package directory from `yt_fetch` to `tubefetch`
- [x] Update all internal imports from `yt_fetch` to `tubefetch`
- [x] Update environment variable prefix from `YT_FETCH_` to `TUBEFETCH_`
- [x] Update config file name from `yt_fetch.yaml` to `tubefetch.yaml`
- [x] Update logger names from `yt_fetch` to `tubefetch`
- [x] Update CLI entry point in `pyproject.toml`
- [x] Update test imports and patch decorators
- [x] Update `CONTRIBUTING.md` to remove `CHANGELOG.md` references (using GitHub Releases instead)
- [x] Update `mkdocs.yml` site name and description from `yt-fetch` to `TubeFetch`
- [x] Delete `CHANGELOG.md` (replaced by auto-generated GitHub Releases)
- [x] Bump version to `0.9.0` (breaking change in CLI UX and package name)

**Examples:**
```bash
# New style (preferred)
tubefetch all dQw4w9WgXcQ abc123def https://www.youtube.com/watch?v=QNPPEB64QbI
tubefetch metadata dQw4w9WgXcQ
tubefetch transcript https://youtu.be/dQw4w9WgXcQ
tubefetch media dQw4w9WgXcQ --download video

# Old style (deprecated but still works)
tubefetch fetch --id dQw4w9WgXcQ
tubefetch metadata --id dQw4w9WgXcQ

# Batch processing (unchanged)
tubefetch all --file videos.txt
tubefetch metadata --jsonl videos.jsonl
```

### Story K.j: v0.9.0 Part 2 - Simplify CLI with Default Command [Done]

Eliminate the `all` command in favor of a default command pattern for better UX.

**Issue:**
- `tubefetch all VIDEO_ID --download both` creates cognitive dissonance ("all" + "both")
- The most common use case (fetch everything) should be the default, not require a subcommand
- Current pattern is verbose for the primary workflow

**Implemented changes:**
- [x] Refactor CLI group to support default command:
  - [x] Add `invoke_without_command=True` to `@click.group()`
  - [x] Add `@click.pass_context` to CLI group
  - [x] Detect when no subcommand is provided and invoke default fetch behavior
  - [x] Add positional arguments and common options to the group itself
- [x] Remove `all` and `fetch` commands entirely (breaking change)
- [x] Make fetch behavior the default (no command name):
  - [x] `tubefetch VIDEO_ID [VIDEO_ID...]` - fetch metadata + transcript
  - [x] `tubefetch VIDEO_ID --download video` - + download video
  - [x] `tubefetch VIDEO_ID --download both` - + download video and audio
- [x] Keep specialized commands for exceptional cases:
  - [x] `tubefetch metadata VIDEO_ID` - metadata only
  - [x] `tubefetch transcript VIDEO_ID` - transcript only
  - [x] `tubefetch media VIDEO_ID` - media only
- [x] Update all documentation:
  - [x] Update README.md examples to use default command
  - [x] Update usage.md to document default command pattern
  - [x] Update getting-started.md examples
  - [x] Update index.html quick start
  - [x] Update CLI help text and docstrings

**New CLI pattern:**
```bash
# Default command (most common - no subcommand needed)
tubefetch dQw4w9WgXcQ
tubefetch dQw4w9WgXcQ abc123def xyz789
tubefetch dQw4w9WgXcQ --download video
tubefetch --file videos.txt

# Specialized commands (exceptional cases)
tubefetch metadata dQw4w9WgXcQ
tubefetch transcript dQw4w9WgXcQ
tubefetch media dQw4w9WgXcQ
```

**Rationale:**
- Cleaner, more intuitive CLI
- Follows common patterns (git, docker, etc.)
- Reduces cognitive load for primary use case
- Specialized commands still available when needed
- Breaking change: `all` and `fetch` commands removed

### Story K.k: v0.9.1 Fix PyPI README Header Image [Done]

Fix broken header image on PyPI package page by using absolute GitHub URL.

**Issue:**
- Header image broken on https://pypi.org/project/tubefetch/
- README used relative path: `docs/site/images/tubefetch_header_readme.png`
- PyPI doesn't have access to repository file structure

**Implemented changes:**
- [x] Update `README.md` header image to use absolute GitHub URL:
  - [x] Changed from `docs/site/images/tubefetch_header_readme.png`
  - [x] Changed to `https://raw.githubusercontent.com/pointmatic/tubefetch/main/docs/site/images/tubefetch_header_readme.png`
- [x] Bump version to `0.9.1` in `pyproject.toml`
- [x] Verify: Image displays correctly on both GitHub and PyPI

**Rationale:**
- External-facing bug affecting package presentation on PyPI
- Absolute URLs work on both GitHub and PyPI
- Improves first impression for potential users browsing PyPI

### Story K.l: v0.9.2 Improve Summary Output Visibility [Done]

Add metadata status to default command summary and add summaries to all specialized commands.

**Issue:**
- Default command summary didn't show metadata fetch status (only transcripts)
- Specialized commands (`metadata`, `transcript`, `media`) had no summary output for batch operations
- Users couldn't easily tell if all 12+ videos were successfully processed

**Implemented changes:**
- [x] Update `tubefetch/core/pipeline.py`:
  - [x] Add "Metadata: X ok, Y failed" line to `print_summary()`
  - [x] Matches format of "Transcripts: X ok, Y failed"
- [x] Update `tubefetch/cli.py`:
  - [x] Add `_print_simple_summary()` helper function
  - [x] Track `succeeded` and `failed` counts in all specialized commands
  - [x] Print summary at end of `metadata` command
  - [x] Print summary at end of `transcript` command
  - [x] Print summary at end of `media` command
- [x] Bump version to `0.9.2` in `pyproject.toml`
- [x] Verify: All 329 tests passing

**Example output:**
```
========================================
  Metadata Summary
========================================
  Total:        12
  Succeeded:    12
  Failed:       0
  Output:       /path/to/out
========================================
```

**Rationale:**
- Improves batch operation visibility across all commands
- Consistent UX between default and specialized commands
- Users can quickly verify success/failure counts without counting log lines
- Better user experience for common workflows (fetching 10+ videos)

### Story K.m: v0.9.3 Fix Stale References and Add Troubleshooting Docs [Done]

Fix remaining `yt-fetch` references and add comprehensive troubleshooting documentation for YouTube API usage.

**Issues:**
- Error message in `metadata.py` still referenced `pip install yt-fetch[youtube-api]`
- Documentation references `yt-fetch` in tech-spec.md and features.md
- No troubleshooting guide for "This video is not available" errors
- YouTube Data API usage not well documented (when/why to use it)
- Missing setup instructions for API key and quota considerations

**Implemented changes:**
- [x] Fix stale references:
  - [x] `tubefetch/services/metadata.py` - Change error message to `pip install tubefetch[youtube-api]`
  - [x] `docs/specs/tech-spec.md` - Change `yt-fetch[tokens]` to `tubefetch[tokens]`
  - [x] `docs/specs/features.md` - Change `yt-fetch[tokens]` to `tubefetch[tokens]`
- [x] Add troubleshooting documentation:
  - [x] Create `docs/site/troubleshooting.md`:
    - [x] Section: "Video Not Available" errors
    - [x] Explain yt-dlp vs YouTube Data API backends
    - [x] When to use YouTube Data API (age-restricted, geo-restricted, bot detection)
    - [x] How to get API key from Google Cloud Console
    - [x] How to set up IP restrictions and API restrictions
    - [x] Quota limits explanation (10,000 units/day default)
    - [x] Example: Handling age-restricted videos
    - [x] Example: Handling geo-restricted videos
  - [x] Update `docs/site/usage.md`:
    - [x] Add "Troubleshooting" section with link to troubleshooting.md
    - [x] Add note about optional YouTube API backend
  - [x] Update `README.md`:
    - [x] Expand YouTube API section with use case explanation
    - [x] Add link to troubleshooting guide
  - [x] Update `mkdocs.yml`:
    - [x] Add troubleshooting.md to navigation
- [x] Bump version to `0.9.3` in `pyproject.toml`
- [x] Verify: All tests passing, documentation complete

**Rationale:**
- Eliminates confusion from stale package name references
- Helps users understand when and why to use YouTube Data API
- Reduces support burden by documenting common issues
- Improves onboarding for users hitting yt-dlp restrictions

### Story K.n: v0.9.4 Improve Warning Messages and zsh Compatibility [Done]

Fix truncated warning messages and add zsh compatibility for pip install commands.

**Issues:**
- Warning message for missing YouTube API dependency was truncated in logs
- pip install commands with square brackets fail in zsh without quotes
- Users see `zsh: no matches found: tubefetch[youtube-api]` error

**Implemented changes:**
- [x] Fix warning message in `tubefetch/services/metadata.py`:
  - [x] Check for `MISSING_DEPENDENCY` error code specifically
  - [x] Show concise, complete message: "Install with 'pip install tubefetch[youtube-api]'"
  - [x] Prevents truncation in log output
  - [x] Include quotes in command for zsh compatibility
- [x] Update all documentation to use quoted pip install commands:
  - [x] `README.md` - Add quotes: `pip install 'tubefetch[youtube-api]'`
  - [x] `docs/site/getting-started.md` - Add quotes
  - [x] `docs/site/usage.md` - Add quotes
  - [x] `docs/site/troubleshooting.md` - Add quotes + zsh note explaining the issue
- [x] Update error message in `tubefetch/services/metadata.py`:
  - [x] Add quotes to pip install command in ImportError exception
- [x] Bump version to `0.9.4` in `pyproject.toml`
- [x] Verify: All tests passing

**Example warning output:**
```
WARNING  YouTube API backend unavailable for VIDEO_ID: Install with "pip install 'tubefetch[youtube-api]'". Falling back to yt-dlp.
```

**Rationale:**
- Prevents user frustration with truncated install commands
- Eliminates zsh compatibility issues (common on macOS)
- Provides complete, copy-pastable commands in all documentation
- Improves first-time user experience when encountering missing dependencies

---

## Phase L: Code Quality & Documentation

### Story L.a: v0.9.5 Type Safety Improvements [Done]

Address mypy strict mode errors to improve type safety and code quality.

**Current state:** All 41 mypy errors fixed - `mypy tubefetch --strict` passes with 0 errors

**Tasks:**
- [x] Fix missing type parameters for generic types:
  - [x] `tubefetch/core/logging.py:34` - Add type params to `dict`
  - [x] `tubefetch/core/models.py:41` - Add type params to `dict`
  - [x] `tubefetch/core/writer.py:137` - Add type params to `dict`
  - [x] `tubefetch/services/transcript.py` - Add type params to `dict` and `list` (multiple locations)
  - [x] `tubefetch/services/metadata.py` - Add type params to `dict` (multiple locations)
  - [x] `tubefetch/services/media.py` - Add type params to `dict` (multiple locations)
- [x] Add type annotations to CLI functions:
  - [x] `tubefetch/cli.py` - Add return type annotations to decorators and helper functions
  - [x] Fix method assignment issue with `cli.main` wrapper
- [x] Fix module export issues:
  - [x] Add `__all__` exports to `tubefetch/services/metadata.py` for `MetadataError`
  - [x] Add `__all__` exports to `tubefetch/services/transcript.py` for `TranscriptError`
  - [x] Add `__all__` exports to `tubefetch/services/media.py` for `MediaError`
- [x] Address external library stub issues:
  - [x] Install `types-yt-dlp` stub package (or add to dev dependencies)
  - [x] Add type ignore comments for `googleapiclient` imports (optional dependency)
  - [x] Fix `youtube_transcript_api` import issue (removed non-existent `NoTranscriptAvailable`)
- [x] Fix `tubefetch/utils/gentlify_config.py` type issues:
  - [x] Add proper type annotations to functions
  - [x] Fix `RetryConfig` argument type compatibility
- [x] Verify: Run `mypy tubefetch --strict` with 0 errors (SUCCESS - all tests passing, 94% coverage)

**Rationale:**
- Improves code maintainability and catches potential bugs at type-check time
- Makes IDE autocomplete and type hints more reliable
- Demonstrates code quality commitment
- Non-urgent: Can be addressed in v0.9.1 or v0.10.0

### Story L.b: v0.9.6 Documentation Polish & SEO [Done]

Add final touches, SEO optimization, and cross-references.

- [x] Update `index.html`:
  - [x] Add Open Graph meta tags (og:title, og:description, og:image, og:url)
  - [x] Add Twitter Card meta tags
  - [x] Ensure all links are correct (internal and external)
- [x] Update all markdown pages:
  - [x] Add cross-references between related pages
  - [x] Use admonitions for notes, warnings, tips
  - [x] Ensure consistent formatting and style
- [x] Create `docs/site/changelog.md`:
  - [x] Link to GitHub releases
  - [x] Summarize major version changes (0.9.0 through 0.9.6)
- [x] Update `mkdocs.yml`:
  - [x] Add `extra` section with social links (GitHub, PyPI)
  - [x] Add copyright notice
  - [x] Add Changelog to navigation
  - [x] Verify all nav links are correct
- [x] Test locally:
  - [x] Run `mkdocs build --strict` successfully
- [x] Verify: Documentation site is complete, polished, and ready for public use

**Rationale:**
- Improves SEO and social media sharing with Open Graph/Twitter Card meta tags
- Enhances user experience with admonitions and cross-references
- Provides clear version history and upgrade guidance
- Professional appearance with social links and copyright notice

### Story L.c: Update Core Documentation to Reflect Current Implementation [Done]

Bring `README.md`, `features.md`, and `tech-spec.md` up to date with the v0.9.x implementation.

**Documentation Gaps Identified:**

1. **README.md** - Missing Phase M planned features documentation
2. **features.md** - Outdated package name (`yt-fetch` → `tubefetch`)
3. **tech-spec.md** - Outdated package name, structure, CLI commands, env vars, config file name
4. **All specs** - Missing v0.9.x CLI UX changes (default command, positional args, removed commands)

**Tasks:**

- [x] Update `README.md`:
  - [x] Add note about Phase M features (planned for v1.x releases)
  - [x] Document that LLM-ready formatting, content hashing, token counting, playlist resolution, and video bundles are planned features
  - [x] Add "Roadmap" or "Upcoming Features" section referencing Phase M in stories.md
  - [x] Ensure all current features (v0.9.6) are accurately documented
  - [x] Verify CLI examples use current syntax (default command with positional args)
  - [x] Fix license from MPL-2.0 to Apache-2.0

- [x] Update `docs/specs/features.md`:
  - [x] Change title from "yt-fetch" to "tubefetch" (line 1)
  - [x] Update all references to package name from `yt-fetch`/`yt_fetch` to `tubefetch`
  - [x] Update CLI command examples from `yt_fetch fetch` to `tubefetch` (default command)
  - [x] Update environment variable prefix from `YT_FETCH_` to `TUBEFETCH_`
  - [x] Update config file name from `yt_fetch.yaml` to `tubefetch.yaml`
  - [x] Add note distinguishing implemented features (v0.9.6) from planned features (Phase M)
  - [x] Update CLI interface section (line 263-299) to reflect current command structure:
    - [x] Default command: `tubefetch VIDEO_ID [VIDEO_ID...]` (no subcommand)
    - [x] Specialized commands: `metadata`, `transcript`, `media`
    - [x] Positional arguments for video IDs/URLs
    - [x] Remove references to removed `fetch` and `all` commands
  - [x] Mark Phase M features as "Planned" where applicable (LLM text formatting, content hashing, token counting, playlist resolution, video bundles)

- [x] Update `docs/specs/tech-spec.md`:
  - [x] Change title from "yt-fetch" to "tubefetch" (line 1)
  - [x] Update package structure section (lines 59-108):
    - [x] Change `yt_fetch/` to `tubefetch/` throughout
    - [x] Mark Phase M modules as "Planned" (resolver.py, txt_formatter.py, hashing.py, token_counter.py)
    - [x] Update test file references
  - [x] Update CLI design section (lines 460-488):
    - [x] Document default command pattern (no subcommand for common case)
    - [x] Update command table to show current structure
    - [x] Remove references to removed `fetch` and `all` commands
    - [x] Document positional argument support
  - [x] Update configuration section (lines 418-456):
    - [x] Change environment variable prefix from `YT_FETCH_` to `TUBEFETCH_`
    - [x] Change config file name from `yt_fetch.yaml` to `tubefetch.yaml`
    - [x] Update `FetchOptions` field list to match current implementation
  - [x] Update library API section (lines 490-502):
    - [x] Change imports from `yt_fetch` to `tubefetch`
    - [x] Mark `resolve_playlist` and `resolve_channel` as "Planned" (Phase M)
  - [x] Add note at top of document indicating which features are implemented (v0.9.6) vs planned (Phase M)

- [x] Verify consistency:
  - [x] Cross-check all three documents for consistent terminology
  - [x] Ensure version numbers align with stories.md
  - [x] Verify all code examples are syntactically correct
  - [x] Check that planned features are clearly marked as such

**Rationale:**
- Eliminates confusion between current implementation and planned features
- Ensures developers and users have accurate reference documentation
- Maintains consistency across all specification documents
- Provides clear roadmap for future development (Phase M)

---

## Phase M: AI-Ready Content Extraction

### Story M.a: v1.0.0 LLM-Ready Transcript Text Formatting [Done]

Replace bare concatenation in `transcript.txt` with intelligent paragraph chunking and optional features.

- [x] Create `tubefetch/utils/txt_formatter.py`:
  - [x] `format_transcript_txt(segments, is_generated, gap_threshold, timestamps, raw) -> str`
  - [x] **Default mode**: join segment text with spaces; insert `\n\n` paragraph breaks when the gap between consecutive segments exceeds `gap_threshold` (default 2.0 seconds)
  - [x] **Timestamped mode** (`timestamps=True`): prepend `[MM:SS]` at each paragraph boundary
  - [x] **Raw mode** (`raw=True`): bare concatenation with spaces, no paragraph formatting (backward-compatible)
  - [x] **Auto-generated notice**: when `is_generated` is true, prepend `[Auto-generated transcript]\n\n`
  - [x] `raw=True` overrides `timestamps`
- [x] Add copyright/license header
- [x] Update `core/writer.py`:
  - [x] `write_transcript_txt()` calls `format_transcript_txt()` with options from `FetchOptions`
- [x] Add `txt_timestamps`, `txt_raw`, `txt_gap_threshold` fields to `FetchOptions` in `core/options.py`
- [x] Add `--txt-timestamps`, `--txt-raw`, `--txt-gap-threshold` CLI flags in `cli.py`
- [x] Write `tests/test_txt_formatter.py`:
  - [x] Test default paragraph chunking: segments with >2s gap produce paragraph breaks
  - [x] Test segments with <2s gap are joined in same paragraph
  - [x] Test custom gap threshold
  - [x] Test timestamped mode produces `[MM:SS]` markers
  - [x] Test raw mode produces bare concatenation
  - [x] Test auto-generated notice is prepended when `is_generated=True`
  - [x] Test auto-generated notice is absent when `is_generated=False` or `None`
- [x] Update existing `test_writer.py` to verify new formatting is used
- [x] Verify: `transcript.txt` output is readable, paragraph-chunked text by default
- [x] Bump version to `1.0.0`

### Story M.b: v1.1.0 Content Hashing [Done]

Add SHA-256 content hashes to metadata and transcript outputs for change detection.

- [x] Create `tubefetch/utils/hashing.py`:
  - [x] `hash_metadata(metadata: Metadata) -> str` — SHA-256 of canonical fields (title, description, tags, upload_date, duration_seconds)
  - [x] `hash_transcript(transcript: Transcript) -> str` — SHA-256 of concatenated segment text
  - [x] `hash_bundle(metadata, transcript) -> str` — SHA-256 of combined content
  - [x] All hashes are hex-encoded lowercase strings
  - [x] Canonical field selection: exclude volatile fields (`view_count`, `like_count`, `fetched_at`, `raw`) so hashes are stable when content hasn't changed
- [x] Add `content_hash: str | None = None` field to `Metadata` model in `core/models.py`
- [x] Add `content_hash: str | None = None` field to `Transcript` model in `core/models.py`
- [x] Update `services/metadata.py`: compute and set `content_hash` after metadata extraction
- [x] Update `services/transcript.py`: compute and set `content_hash` after transcript extraction
- [x] Write `tests/test_hashing.py`:
  - [x] Test `hash_metadata` produces consistent hash for same content
  - [x] Test `hash_metadata` produces different hash when title/description changes
  - [x] Test `hash_metadata` produces same hash when only `view_count` changes
  - [x] Test `hash_transcript` produces consistent hash for same segments
  - [x] Test `hash_transcript` produces different hash when segment text changes
  - [x] Test `hash_bundle` combines metadata and transcript hashes
- [x] Verify: `metadata.json` and `transcript.json` contain `content_hash` field
- [x] Bump version to `1.1.0`

### Story M.c: v1.2.0 Token Count Estimation [Done]

Optionally estimate token counts for transcript text using `tiktoken`.

- [x] Create `tubefetch/utils/token_counter.py`:
  - [x] `count_tokens(text: str, tokenizer: str = "cl100k_base") -> int`
  - [x] `is_tokenizer_available() -> bool` — check if `tiktoken` is installed
  - [x] Graceful degradation: if `tiktoken` not installed and tokenizer requested, log warning and return `None`
- [x] Add `tiktoken` to `[project.optional-dependencies]` as `tokens` extra in `pyproject.toml`:
  - [x] `tokens = ["tiktoken"]`
- [x] Add `token_count: int | None = None` field to `Transcript` model in `core/models.py`
- [x] Add `tokenizer: str | None = None` field to `FetchOptions` in `core/options.py`
- [x] Add `--tokenizer` CLI flag in `cli.py`
- [x] Update `services/transcript.py`: after fetching transcript, compute `token_count` if `options.tokenizer` is set
- [x] Write `tests/test_token_counter.py`:
  - [x] Test `count_tokens` returns correct count (mock `tiktoken` if needed)
  - [x] Test `is_tokenizer_available` returns `False` when `tiktoken` not installed
  - [x] Test graceful degradation: `token_count` is `None` when `tiktoken` unavailable
  - [x] Test `token_count` is `None` when `tokenizer` option is not set
  - [x] Test `token_count` is populated when `tokenizer` option is set and `tiktoken` available
- [x] Verify: `transcript.json` contains `token_count` when tokenizer configured
- [x] Bump version to `1.2.0`

### Story M.d: v1.3.0 Playlist and Channel Resolution [Done]

Accept playlist and channel URLs as batch input sources.

- [x] Create `tubefetch/services/resolver.py`:
  - [x] `resolve_playlist(url: str, max_videos: int | None = None) -> list[str]`
  - [x] `resolve_channel(url: str, max_videos: int | None = None) -> list[str]`
  - [x] `resolve_input(input_str: str, max_videos: int | None = None) -> list[str]` — auto-detect input type
  - [x] Use `yt-dlp`'s `extract_info(url, download=False)` with `extract_flat=True` for efficient ID-only extraction
  - [x] `max_videos` limits the number of IDs returned
  - [x] Write resolved IDs to `<out>/resolved_ids.json` for reproducibility
- [x] Add `max_videos: int | None = None` field to `FetchOptions` in `core/options.py`
- [x] Add `--playlist`, `--channel`, `--max-videos` CLI flags in `cli.py`
- [x] Update `core/pipeline.py` `process_batch()`: accept playlist/channel URLs, resolve to IDs, then process
- [x] Export `resolve_playlist` and `resolve_channel` from `tubefetch/__init__.py`
- [x] Write `tests/test_resolver.py`:
  - [x] Test `resolve_playlist` with mocked `yt-dlp` returns ordered video IDs
  - [x] Test `resolve_channel` with mocked `yt-dlp` returns video IDs
  - [x] Test `max_videos` limits the returned list
  - [x] Test `resolve_input` auto-detects playlist vs channel vs video URL
  - [x] Test `resolved_ids.json` is written to output directory
  - [x] Test invalid URL raises appropriate error
- [x] Add integration tests (guarded by `RUN_INTEGRATION=1`):
  - [x] Resolve a known public playlist
  - [x] Resolve a known public channel (with `max_videos=5`)
- [x] Bump version to `1.3.0`

### Story M.e: v1.4.0 Video Bundle Output [Done]

Optionally emit a unified `video_bundle.json` per video.

- [x] Add `VideoBundle` model to `core/models.py`:
  - [x] Fields: `video_id`, `metadata`, `transcript`, `errors`, `content_hash`, `token_count`, `fetched_at`
- [x] Add `write_bundle(result: FetchResult, out_dir: Path) -> Path` to `core/writer.py`
- [x] Add `bundle: bool = False` field to `FetchOptions` in `core/options.py`
- [x] Add `--bundle` CLI flag in `cli.py`
- [x] Update `core/pipeline.py` `process_video()`:
  - [x] After all other outputs are written, if `options.bundle` is `True`, call `write_bundle()`
  - [x] Bundle `content_hash` uses `hash_bundle()` from `utils/hashing.py`
  - [x] Bundle `token_count` comes from `transcript.token_count`
- [x] Write `tests/test_bundle.py`:
  - [x] Test bundle contains correct `video_id`, `metadata`, `transcript`, `errors`
  - [x] Test bundle `content_hash` matches `hash_bundle()` output
  - [x] Test bundle `token_count` matches transcript `token_count`
  - [x] Test bundle is NOT written when `bundle=False`
  - [x] Test bundle IS written when `bundle=True`
  - [x] Test bundle JSON round-trip (write + read back)
- [x] Verify: `video_bundle.json` appears in output when `--bundle` is set
- [x] Bump version to `1.4.0`

### Story M.f: v1.4.1 README and Documentation Update [Done]

Update README and documentation to reflect the AI-ready positioning with comprehensive examples and guides.

- [x] Update `descriptions.md`:
  - [x] Categorize Feature Cards into: AI-Ready Features (4), Core Features (3), Operational Features (4)
  - [x] Add category headers to Feature Cards table
- [x] Update `README.md`:
  - [x] Update Features list (lines 18-26) to match updated Benefits from `descriptions.md`
  - [x] Add "AI Pipeline" usage example showing `FetchOptions(tokenizer="cl100k_base", bundle=True)`
  - [x] Add "Playlist Processing" usage example showing `--playlist` and `--channel` flags
  - [x] Update CLI flags table with new flags (`--tokenizer`, `--max-videos`, `--bundle`, `--playlist`, `--channel`, `--txt-timestamps`, `--txt-raw`, `--txt-gap-threshold`)
  - [x] Add `[tokens]` optional dependency to installation section with `pip install tubefetch[tokens]`
- [x] Update `pyproject.toml`:
  - [x] Update description to match Long Tagline from `descriptions.md`
- [x] Create MkDocs AI-ready features guide (`docs/guides/ai-ready-features.md`):
  - [x] Overview of AI-ready capabilities
  - [x] Quick start for AI pipelines
  - [x] Links to detailed feature guides
- [x] Create MkDocs LLM text formatting guide (`docs/guides/llm-text-formatting.md`):
  - [x] Explain paragraph chunking with `--txt-gap-threshold`
  - [x] Show timestamp markers with `--txt-timestamps`
  - [x] Compare raw vs formatted output
  - [x] Best practices for different LLM use cases
- [x] Create MkDocs content hashing guide (`docs/guides/content-hashing.md`):
  - [x] Explain SHA-256 hashing for metadata and transcripts
  - [x] Show how to detect content changes
  - [x] Example workflow for monitoring video updates
  - [x] Explain canonical field selection (excludes view_count, like_count)
- [x] Create MkDocs token counting guide (`docs/guides/token-counting.md`):
  - [x] Explain tiktoken integration
  - [x] Show `--tokenizer` flag usage
  - [x] Cost estimation examples for different LLMs (GPT-4, Claude, etc.)
  - [x] Graceful degradation when tiktoken not installed
- [x] Create MkDocs playlist/channel resolution guide (`docs/guides/playlist-resolution.md`):
  - [x] Show `--playlist` and `--channel` flag usage
  - [x] Explain `--max-videos` limiting
  - [x] Show `resolved_ids.json` output format
  - [x] Batch processing workflows
- [x] Create MkDocs video bundles guide (`docs/guides/video-bundles.md`):
  - [x] Explain unified `video_bundle.json` format
  - [x] Show `--bundle` flag usage
  - [x] Example bundle structure with all fields
  - [x] Integration with AI pipelines
- [x] Create MkDocs use cases guide (`docs/guides/use-cases.md`):
  - [x] RAG pipeline example (vector database indexing)
  - [x] Content monitoring example (change detection workflow)
  - [x] Batch analysis example (channel analytics)
  - [x] Training data preparation example
  - [x] Fact-checking pipeline example
- [x] Update MkDocs CLI reference (`docs/reference/cli.md`):
  - [x] Add all new Phase M flags with descriptions
  - [x] Organize flags by category (Input, Output, AI Features, Processing)
- [x] Update MkDocs API reference (`docs/reference/api.md`):
  - [x] Document `resolve_playlist()` and `resolve_channel()` functions
  - [x] Update `FetchOptions` with new fields
  - [x] Add `VideoBundle` model documentation
- [x] Update MkDocs navigation (`mkdocs.yml`):
  - [x] Add "AI-Ready Features" section
  - [x] Add "Use Cases" section
  - [x] Ensure logical flow from getting started → guides → reference
- [x] Verify: README renders correctly on GitHub
- [x] Verify: MkDocs builds without errors
- [x] Bump version to `1.4.1`

### Story M.g: v1.4.2 Update Pyve, migrate to Project-Guide [Done]

Update Pyve tooling and migrate documentation from `guides/project-guides` to the new `project-guide` layout.

- [x] Migrate from `guides/project-guides` to `project-guide`
- [x] Update Pyve to latest version
- [x] Bump version to `1.4.2` in `pyproject.toml`
- [x] Delete stale `v1.4.1a` tag (local and remote)
- [x] Tag `v1.4.2` and push to trigger PyPI publish workflow
- [x] Verify: PyPI publish succeeds (new filename, no 400 conflict)
- [x] Verify: GitHub release created for `v1.4.2`
