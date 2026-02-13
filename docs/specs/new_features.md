# yt-fetch: Gaps, Bug Reports, and Requested Changes

> **Context:** These issues were discovered while building [yt-factify](https://github.com/pointmatic/yt-factify),
> which uses `yt-fetch` as its transcript ingestion layer via the Python library API.
>
> **yt-fetch version tested:** 0.5.1
> **Date:** 2026-02-07

---

## Bug 1: `result.transcript` is `None` without `force_transcript=True`

### Severity: **Critical** — breaks the primary library use case

### Problem

When calling `fetch_video()` with `download='none'` (the expected mode for
library consumers who don't need files on disk), `result.transcript` is always
`None` — even when the video has captions available.

The **CLI** (`yt-fetch transcript --id <id>`) works correctly for the same
videos, because it writes to disk and reads back.

### Reproduction

```python
import yt_fetch

# ❌ This returns transcript=None for ALL videos
opts = yt_fetch.FetchOptions(
    languages=["en"],
    allow_generated=True,
    download="none",
)
result = yt_fetch.fetch_video("dQw4w9WgXcQ", opts)
assert result.success is True
assert result.transcript is None  # BUG: should not be None

# ✅ Workaround: force_transcript=True populates the in-memory object
opts2 = yt_fetch.FetchOptions(
    languages=["en"],
    allow_generated=True,
    download="none",
    force_transcript=True,
)
result2 = yt_fetch.fetch_video("dQw4w9WgXcQ", opts2)
assert result2.transcript is not None  # works
assert len(result2.transcript.segments) == 61
```

### Videos tested

| Video ID | `force_transcript=False` | `force_transcript=True` | CLI |
|---|---|---|---|
| `dQw4w9WgXcQ` (Rick Astley) | `transcript=None` | ✅ 61 segments | ✅ |
| `2QzUUNFwuf4` (Forbes Breaking News) | `transcript=None` | ✅ 491 segments | ✅ |
| `8jPQjjsBbIc` (TED talk) | ✅ 260 segments | ✅ 260 segments | ✅ |

Note: `8jPQjjsBbIc` worked without `force_transcript` — the behavior is
inconsistent across videos, which makes this harder to diagnose.

### Expected behavior

`fetch_video()` should **always** populate `result.transcript` in-memory when
a transcript is available, regardless of `download` mode or `force_*` flags.
The `force_transcript` flag should only control whether a *cached* transcript
is re-fetched, not whether the result object is populated.

### Suggested fix

In the fetch pipeline, ensure the transcript is fetched and assigned to
`result.transcript` whenever `download` includes transcript capability (which
`'none'` should — "none" refers to *media* download, not transcript). The
`force_transcript` flag should only bypass the on-disk cache.

---

## Bug 2: `result.metadata` is `None` without `force_metadata=True`

### Severity: **High** — metadata is essential for diagnostics and downstream use

### Problem

Same pattern as Bug 1. When using `download='none'`, `result.metadata` is
always `None` unless `force_metadata=True` is explicitly set.

### Reproduction

```python
import yt_fetch

# ❌ metadata is None
opts = yt_fetch.FetchOptions(
    languages=["en"],
    allow_generated=True,
    download="none",
)
result = yt_fetch.fetch_video("dQw4w9WgXcQ", opts)
assert result.metadata is None  # BUG

# ✅ Workaround
opts2 = yt_fetch.FetchOptions(
    languages=["en"],
    allow_generated=True,
    download="none",
    force_metadata=True,
)
result2 = yt_fetch.fetch_video("dQw4w9WgXcQ", opts2)
assert result2.metadata is not None
assert result2.metadata.upload_date == "2009-10-25"
assert result2.metadata.channel_id == "UCuAXFkgsw1L7xaCfnd5JJOw"
```

### Expected behavior

`result.metadata` should always be populated when the fetch succeeds. Metadata
is lightweight and essential for any meaningful use of the library API.

---

## Bug 3: `success=True` with `transcript=None` and empty `errors`

### Severity: **Medium** — misleading result, makes debugging difficult

### Problem

When a transcript cannot be fetched (or isn't populated due to Bug 1),
`result.success` is `True` and `result.errors` is `[]`. The caller has no way
to distinguish "fetch succeeded but video has no captions" from "fetch
succeeded but result wasn't populated due to a bug."

### Reproduction

```python
result = yt_fetch.fetch_video("2QzUUNFwuf4", opts)
print(result.success)     # True
print(result.transcript)  # None
print(result.errors)      # []
# What happened? No way to tell.
```

### Expected behavior

Either:
- **(a)** `success=False` with a descriptive error when no transcript is
  available (e.g., `"No captions available for video 2QzUUNFwuf4"`), or
- **(b)** `success=True` with `transcript=None` and a **warning** in
  `result.errors` (e.g., `"No English captions found; available languages: []"`)

Option (b) is preferable since the metadata fetch may have succeeded — the
transcript absence is a partial failure, not a total failure.

---

## Issue 4: CLI/Library behavior discrepancy

### Severity: **Medium** — confusing for developers

### Problem

The CLI subcommands (`fetch`, `transcript`, `metadata`) and the library API
(`fetch_video`) behave differently for the same video:

| Behavior | CLI (`yt-fetch transcript`) | Library (`fetch_video`) |
|---|---|---|
| Transcript populated | ✅ Always (writes to disk) | ❌ Requires `force_transcript=True` |
| Metadata populated | ✅ With `fetch` command | ❌ Requires `force_metadata=True` |
| Error on missing transcript | ❌ Silent success | ❌ Silent success |

### Expected behavior

The library API should be the **source of truth**. The CLI should be a thin
wrapper. Both should behave identically for the same inputs.

---

## Feature Request 1: `transcript_only` or `include_metadata` fetch mode

### Priority: **Nice to have**

For library consumers who want transcript + metadata without writing files to
disk, the current API requires setting `force_metadata=True` and
`force_transcript=True` as a workaround. A clearer API would be:

```python
# Option A: A new download mode
opts = FetchOptions(download="transcript")  # transcript + metadata, no media files

# Option B: Explicit include flags (non-breaking)
opts = FetchOptions(
    download="none",
    include_metadata=True,   # always populate result.metadata
    include_transcript=True, # always populate result.transcript
)
```

---

## Feature Request 2: Report available languages on transcript failure

### Priority: **Medium**

When a transcript is not available in the requested language, the
`Transcript.available_languages` field exists but is only populated on
*success*. On failure, there's no way to know what languages *are* available.

### Suggested approach

When transcript fetch fails for the requested language, still probe for
available languages and include them in the error message or in a new
`result.available_languages` field:

```python
result = fetch_video("xyz", FetchOptions(languages=["en"]))
# If no English transcript:
# result.errors = ["No transcript in ['en']; available: ['es', 'fr', 'ja']"]
# result.available_languages = ["es", "fr", "ja"]  # NEW field on FetchResult
```

This helps yt-factify provide actionable error messages like:
> "No English transcript for XYZ. Available languages: es, fr, ja.
> Use `--language fr` to try French."

---

## Summary: Immediate Workarounds for yt-factify

Until these issues are fixed in yt-fetch, yt-factify should use:

```python
opts = FetchOptions(
    languages=config.languages,
    allow_generated=True,
    download="none",
    force_metadata=True,     # Workaround for Bug 2
    force_transcript=True,   # Workaround for Bug 1
)
```

This resolves the `transcript=None` issue and provides metadata for
upload-date heuristics and channel tracking.

### Impact on yt-factify stories

| Story | Blocked? | Notes |
|---|---|---|
| **F.d: Transcript Fetch Diagnostics** | ❌ Unblocked | Workaround (`force_transcript=True`, `force_metadata=True`) provides all needed data |
| **F.e: Channel Fetch Ledger** | ❌ Unblocked | `metadata.channel_id` and `metadata.channel_title` available via workaround |

---

## Appendix: yt-fetch v0.5.1 API Reference (as tested)

### `FetchOptions` fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `out` | `Path` | `out` | Output directory |
| `languages` | `list[str]` | `["en"]` | Preferred transcript languages |
| `allow_generated` | `bool` | `True` | Allow auto-generated captions |
| `allow_any_language` | `bool` | `False` | Fall back to any language |
| `download` | `Literal["none","video","audio","both"]` | `"none"` | Media download mode |
| `force` | `bool` | `False` | Force re-fetch everything |
| `force_metadata` | `bool` | `False` | Force re-fetch metadata |
| `force_transcript` | `bool` | `False` | Force re-fetch transcript |
| `force_media` | `bool` | `False` | Force re-download media |
| `retries` | `int` | `3` | Max retries per request |
| `rate_limit` | `float` | `2.0` | Requests per second |
| `workers` | `int` | `3` | Parallel workers for batch |
| `fail_fast` | `bool` | `False` | Stop on first failure |
| `verbose` | `bool` | `False` | Verbose console output |
| `yt_api_key` | `str \| None` | `None` | YouTube Data API key |
| `ffmpeg_fallback` | `Literal["error","skip"]` | `"error"` | FFmpeg error handling |

### `FetchResult` fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `video_id` | `str` | required | |
| `success` | `bool` | required | |
| `metadata_path` | `Path \| None` | `None` | |
| `transcript_path` | `Path \| None` | `None` | |
| `media_paths` | `list[Path]` | `[]` | |
| `metadata` | `Metadata \| None` | `None` | **Requires `force_metadata=True`** |
| `transcript` | `Transcript \| None` | `None` | **Requires `force_transcript=True`** |
| `errors` | `list[str]` | `[]` | |

### `Metadata` fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `video_id` | `str` | required | |
| `source_url` | `str` | required | |
| `title` | `str \| None` | `None` | |
| `channel_title` | `str \| None` | `None` | |
| `channel_id` | `str \| None` | `None` | |
| `upload_date` | `str \| None` | `None` | ISO 8601 date, e.g. `"2009-10-25"` |
| `duration_seconds` | `float \| None` | `None` | |
| `description` | `str \| None` | `None` | |
| `tags` | `list[str]` | `[]` | |
| `view_count` | `int \| None` | `None` | |
| `like_count` | `int \| None` | `None` | |
| `fetched_at` | `datetime` | required | |
| `metadata_source` | `str` | required | e.g. `"yt-dlp"` |
| `raw` | `dict \| None` | `None` | Raw yt-dlp response |

### `Transcript` fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `video_id` | `str` | required | |
| `language` | `str` | required | |
| `is_generated` | `bool \| None` | `None` | |
| `segments` | `list[TranscriptSegment]` | required | |
| `fetched_at` | `datetime` | required | |
| `transcript_source` | `str` | required | |
| `available_languages` | `list[str]` | `[]` | Only populated on success |
| `errors` | `list[str]` | `[]` | |

### CLI subcommands

| Command | Description |
|---|---|
| `yt-fetch fetch` | Fetch metadata + transcript (+ optional media) |
| `yt-fetch transcript` | Fetch transcript only |
| `yt-fetch metadata` | Fetch metadata only |
| `yt-fetch media` | Download media only |