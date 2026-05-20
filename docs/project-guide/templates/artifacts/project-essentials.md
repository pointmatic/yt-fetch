<!--
This file captures must-know facts future LLMs need to avoid blunders when
working on this project. Anything a smart newcomer could miss on day one and
waste time on goes here.

This content gets injected verbatim under a `## Project Essentials` section
in every rendered `go.md`, so entries below should use `###` for subsections
(not `##`, which would collide with the wrapper heading). Do NOT include a
top-level `#` title — the wrapper provides it.

What belongs here:

- **Workflow rules — tool wrappers and environment conventions.** A common
  source of "random walks" by LLMs: multiple invocation forms all *work*,
  but only one is canonical. Capture which form to use so future LLMs don't
  pick whatever happens to succeed first. Examples:
    - Python invocation (`pyve run python ...` vs `python -m ...` vs
      `.venv/bin/python ...`)
    - Dev-tool installation (dedicated testenv vs `pip install -e ".[dev]"`
      into the main venv — different isolation guarantees)
    - Test invocation (`pyve test`, `poetry run pytest`, `make test` vs
      bare `pytest`)

- **Architecture quirks.** Source-of-truth vs generated/installed file
  locations (edit the source, not the copy); build outputs that get
  regenerated; files that look hand-edited but aren't.

- **Domain conventions.** Money stored in cents, all timestamps UTC, IDs
  are strings not ints, and similar non-obvious rules.

- **Hidden coupling.** Files that mirror each other; auto-generated code;
  regenerated outputs that look hand-edited.

- **Dogfooding / meta notes.** If the project uses itself, capture the
  rules that keep the dogfood loop safe.

An empty file is acceptable — omit this file entirely, or leave the comment
block above with no content below it. When empty, the rendered `go.md` for
every mode will simply omit the "Project Essentials" section.

The `plan_tech_spec`, `refactor_plan`, and `plan_phase` modes prompt for new
entries at natural points in the project lifecycle.
-->
