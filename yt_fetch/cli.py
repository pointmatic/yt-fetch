# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CLI entry point for yt-fetch."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from yt_fetch import __version__
from yt_fetch.core.logging import setup_logging, get_logger
from yt_fetch.core.options import FetchOptions
from yt_fetch.services.id_parser import load_ids_from_file, parse_many


# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_PARTIAL = 2
EXIT_ALL_FAILED = 3


def _input_options(fn):
    """Shared input source options."""
    decorators = [
        click.option("--id", "ids", multiple=True, help="YouTube video ID or URL (repeatable)."),
        click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), default=None, help="Text/CSV file with IDs."),
        click.option("--jsonl", "jsonl_path", type=click.Path(exists=True, path_type=Path), default=None, help="JSONL file with video IDs."),
        click.option("--id-field", default="id", help="Field name for video ID in CSV/JSONL input."),
    ]
    for decorator in reversed(decorators):
        fn = decorator(fn)
    return fn


def _common_options(fn):
    """Shared Click options that map to FetchOptions fields."""
    decorators = [
        click.option("--out", type=click.Path(path_type=Path), default=None, help="Output directory."),
        click.option("--languages", type=str, default=None, help="Comma-separated language codes."),
        click.option("--allow-generated/--no-allow-generated", default=None, help="Allow auto-generated transcripts."),
        click.option("--allow-any-language/--no-allow-any-language", default=None, help="Fall back to any language."),
        click.option("--download", type=click.Choice(["none", "video", "audio", "both"]), default=None, help="Media download mode."),
        click.option("--max-height", type=int, default=None, help="Max video height (e.g. 720)."),
        click.option("--format", "format_", type=str, default=None, help="Video format."),
        click.option("--audio-format", type=str, default=None, help="Audio format."),
        click.option("--force", is_flag=True, default=None, help="Force re-fetch everything."),
        click.option("--force-metadata", is_flag=True, default=None, help="Force re-fetch metadata."),
        click.option("--force-transcript", is_flag=True, default=None, help="Force re-fetch transcript."),
        click.option("--force-media", is_flag=True, default=None, help="Force re-download media."),
        click.option("--retries", type=int, default=None, help="Max retries per request."),
        click.option("--rate-limit", type=float, default=None, help="Requests per second."),
        click.option("--workers", type=int, default=None, help="Parallel workers for batch."),
        click.option("--fail-fast", is_flag=True, default=None, help="Stop on first failure."),
        click.option("--strict", is_flag=True, default=False, help="Exit 2 on partial failure."),
        click.option("--verbose", is_flag=True, default=None, help="Verbose console output."),
    ]
    for decorator in reversed(decorators):
        fn = decorator(fn)
    return fn


def _build_options(strict: bool = False, **cli_kwargs) -> FetchOptions:
    """Build FetchOptions from CLI kwargs, filtering out unset (None) values.

    Only explicitly-provided CLI flags are passed to FetchOptions as init
    overrides. Unset flags fall through to env vars → YAML → defaults.
    """
    overrides = {}
    for key, value in cli_kwargs.items():
        if value is None:
            continue
        if key == "format_":
            overrides["format"] = value
        elif key == "languages":
            overrides["languages"] = [lang.strip() for lang in value.split(",")]
        else:
            overrides[key] = value
    return FetchOptions(**overrides)


def _collect_ids(
    ids: tuple[str, ...],
    file_path: Path | None,
    jsonl_path: Path | None,
    id_field: str,
) -> list[str]:
    """Collect and deduplicate video IDs from all input sources."""
    raw: list[str] = list(ids)
    if file_path:
        raw.extend(load_ids_from_file(file_path, id_field=id_field))
    if jsonl_path:
        raw.extend(load_ids_from_file(jsonl_path, id_field=id_field))
    return parse_many(raw)


def _exit_code(total: int, failed: int, strict: bool) -> int:
    """Determine exit code from batch results."""
    if total == 0:
        return EXIT_OK
    if failed == 0:
        return EXIT_OK
    if failed == total:
        return EXIT_ALL_FAILED
    if strict:
        return EXIT_PARTIAL
    return EXIT_OK


@click.group()
@click.version_option(version=__version__, prog_name="yt_fetch")
def cli() -> None:
    """YouTube video metadata, transcript, and media fetcher."""


@cli.command()
@_input_options
@_common_options
def fetch(ids, file_path, jsonl_path, id_field, strict, **kwargs):
    """Fetch metadata, transcripts, and optionally media."""
    options = _build_options(strict=strict, **kwargs)
    setup_logging(verbose=options.verbose)
    log = get_logger()

    video_ids = _collect_ids(ids, file_path, jsonl_path, id_field)
    if not video_ids:
        log.error("No video IDs provided. Use --id, --file, or --jsonl.")
        sys.exit(EXIT_ERROR)

    from yt_fetch.core.pipeline import process_batch

    result = process_batch(video_ids, options)
    sys.exit(_exit_code(result.total, result.failed, strict))


@cli.command()
@_input_options
@_common_options
def transcript(ids, file_path, jsonl_path, id_field, strict, **kwargs):
    """Fetch transcripts only."""
    options = _build_options(strict=strict, **kwargs)
    setup_logging(verbose=options.verbose)
    log = get_logger()

    video_ids = _collect_ids(ids, file_path, jsonl_path, id_field)
    if not video_ids:
        log.error("No video IDs provided. Use --id, --file, or --jsonl.")
        sys.exit(EXIT_ERROR)

    from yt_fetch.core.writer import write_transcript_json
    from yt_fetch.services.transcript import TranscriptError, get_transcript

    failed = 0
    for vid in video_ids:
        try:
            t = get_transcript(vid, options)
            write_transcript_json(t, Path(options.out))
            log.info("Wrote transcript for %s", vid)
        except TranscriptError as exc:
            log.error("Transcript error for %s: %s", vid, exc)
            failed += 1

    sys.exit(_exit_code(len(video_ids), failed, strict))


@cli.command()
@_input_options
@_common_options
def metadata(ids, file_path, jsonl_path, id_field, strict, **kwargs):
    """Fetch metadata only."""
    options = _build_options(strict=strict, **kwargs)
    setup_logging(verbose=options.verbose)
    log = get_logger()

    video_ids = _collect_ids(ids, file_path, jsonl_path, id_field)
    if not video_ids:
        log.error("No video IDs provided. Use --id, --file, or --jsonl.")
        sys.exit(EXIT_ERROR)

    from yt_fetch.core.writer import write_metadata
    from yt_fetch.services.metadata import MetadataError, get_metadata

    failed = 0
    for vid in video_ids:
        try:
            m = get_metadata(vid, options)
            write_metadata(m, Path(options.out))
            log.info("Wrote metadata for %s", vid)
        except MetadataError as exc:
            log.error("Metadata error for %s: %s", vid, exc)
            failed += 1

    sys.exit(_exit_code(len(video_ids), failed, strict))


@cli.command()
@_input_options
@_common_options
def media(ids, file_path, jsonl_path, id_field, strict, **kwargs):
    """Download media only."""
    options = _build_options(strict=strict, **kwargs)
    setup_logging(verbose=options.verbose)
    log = get_logger()

    video_ids = _collect_ids(ids, file_path, jsonl_path, id_field)
    if not video_ids:
        log.error("No video IDs provided. Use --id, --file, or --jsonl.")
        sys.exit(EXIT_ERROR)

    if options.download == "none":
        options = options.model_copy(update={"download": "video"})

    from yt_fetch.services.media import MediaError, download_media

    failed = 0
    for vid in video_ids:
        try:
            result = download_media(vid, options, Path(options.out))
            if result.skipped:
                log.warning("Skipped media for %s: %s", vid, result.errors)
            else:
                log.info("Downloaded media for %s", vid)
        except MediaError as exc:
            log.error("Media error for %s: %s", vid, exc)
            failed += 1

    sys.exit(_exit_code(len(video_ids), failed, strict))


if __name__ == "__main__":
    cli()
