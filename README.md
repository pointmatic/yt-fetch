# yt-fetch

YouTube video metadata, transcript, and media fetcher.

Given one or more YouTube video IDs (or URLs), `yt-fetch` downloads metadata, transcripts, and optionally video/audio to a structured local folder. It supports batch processing, caching, retries, rate limiting, and multiple transcript export formats.

## Features

- **Metadata** — title, channel, duration, tags, upload date via yt-dlp (or YouTube Data API v3)
- **Transcripts** — fetched via youtube-transcript-api with language preference and fallback
- **Media** — optional video/audio download via yt-dlp
- **Export formats** — JSON, plain text, WebVTT (.vtt), SubRip (.srt)
- **Batch processing** — concurrent workers with per-video error isolation
- **Caching** — skip already-fetched data; selective `--force` overrides
- **Retry** — exponential backoff with jitter on transient errors
- **Rate limiting** — token bucket algorithm, shared across workers
- **CLI + Library** — use from the command line or import as a Python package

## Installation

Requires **Python 3.14+**.

```bash
pip install -e .
```

For YouTube Data API v3 support (optional):

```bash
pip install -e ".[youtube-api]"
```

> **Note:** The CLI command can be invoked as either `yt_fetch` or `yt-fetch`.

## Quick Start

### CLI

```bash
# Fetch metadata + transcript for a single video
yt_fetch fetch --id dQw4w9WgXcQ

# Fetch with media download
yt_fetch fetch --id dQw4w9WgXcQ --download video

# Batch from a file
yt_fetch fetch --file video_ids.txt --out ./output --workers 3

# Transcript only
yt_fetch transcript --id dQw4w9WgXcQ --languages en,fr

# Metadata only
yt_fetch metadata --id dQw4w9WgXcQ

# Media only
yt_fetch media --id dQw4w9WgXcQ
```

### Library API

```python
from yt_fetch import fetch_video, fetch_batch, FetchOptions

# Single video
result = fetch_video("dQw4w9WgXcQ")
print(result.metadata.title)
print(result.transcript.segments[0].text)

# With options
opts = FetchOptions(out="./output", languages=["en", "fr"], download="audio")
result = fetch_video("dQw4w9WgXcQ", opts)

# Batch
results = fetch_batch(["dQw4w9WgXcQ", "abc12345678"], opts)
print(f"{results.succeeded}/{results.total} succeeded")
```

## Output Structure

```
out/
├── <video_id>/
│   ├── metadata.json
│   ├── transcript.json
│   ├── transcript.txt
│   ├── transcript.vtt
│   ├── transcript.srt
│   └── media/
│       ├── video.mp4
│       └── audio.m4a
└── summary.json
```

## Configuration

Options are resolved in this order (first wins):

1. **CLI flags**
2. **Environment variables** (prefix `YT_FETCH_`)
3. **YAML config file** (`yt_fetch.yaml`)
4. **Defaults**

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--id` | Video ID or URL (repeatable) | — |
| `--file` | Text/CSV file with IDs | — |
| `--jsonl` | JSONL file with IDs | — |
| `--id-field` | Field name in CSV/JSONL | `id` |
| `--out` | Output directory | `./out` |
| `--languages` | Comma-separated language codes | `en` |
| `--allow-generated` | Allow auto-generated transcripts | `true` |
| `--allow-any-language` | Fall back to any language | `false` |
| `--download` | `none`, `video`, `audio`, `both` | `none` |
| `--max-height` | Max video height (e.g. 720) | — |
| `--format` | Video format | `best` |
| `--audio-format` | Audio format | `best` |
| `--force` | Force re-fetch everything | `false` |
| `--force-metadata` | Force re-fetch metadata only | `false` |
| `--force-transcript` | Force re-fetch transcript only | `false` |
| `--force-media` | Force re-download media only | `false` |
| `--retries` | Max retries per request | `3` |
| `--rate-limit` | Requests per second | `2.0` |
| `--workers` | Parallel workers for batch | `3` |
| `--fail-fast` | Stop on first failure | `false` |
| `--strict` | Exit code 2 on partial failure | `false` |
| `--verbose` | Verbose output | `false` |

### Environment Variables

All options can be set via environment variables with the `YT_FETCH_` prefix:

```bash
export YT_FETCH_OUT=./output
export YT_FETCH_LANGUAGES=en,fr
export YT_FETCH_DOWNLOAD=video
export YT_FETCH_YT_API_KEY=your-api-key
```

### YAML Config File

Create `yt_fetch.yaml` in the working directory:

```yaml
out: ./output
languages:
  - en
  - fr
download: none
allow_generated: true
retries: 3
rate_limit: 2.0
workers: 3
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (or partial failure without `--strict`) |
| 1 | Generic error (e.g. no IDs provided) |
| 2 | Partial failure with `--strict` |
| 3 | All videos failed |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=yt_fetch --cov-report=term-missing

# Run integration tests (requires network)
RUN_INTEGRATION=1 python -m pytest tests/integration/
```

## License

MPL-2.0
