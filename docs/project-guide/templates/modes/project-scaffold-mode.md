Scaffold the project foundation: license, copyright headers, package manifest, README with badges, CHANGELOG, and .gitignore. This is a one-time scaffolding step after planning is complete, using decisions made in the concept, features, tech-spec, and stories documents.

{% include "modes/_header-sequence.md" %}

## Prerequisites

Before starting, the developer must provide (or the LLM must ask for):

1. **Project name** -- the repository and package name
2. **Copyright holder** -- individual or organization name
3. **License preference** -- e.g. Apache-2.0, MIT, MPL-2.0, GPL-3.0

## Steps

### 1. License

1. If a `LICENSE` file exists in the project root, read it and identify the license.
2. If no `LICENSE` file exists, create one based on the developer's preference.
3. Record the license identifier (SPDX format, e.g. `Apache-2.0`) -- this will be used in `pyproject.toml` (or equivalent) and in file headers.

### 2. Copyright and License Header

Establish the standard copyright and license header for all source files in the project. The header format depends on the license and the file's comment syntax.

**Example for Apache-2.0 in a Python file:**

```python
# Copyright (c) <year> <copyright holder>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

**Example for MIT in a Python file:**

```python
# Copyright (c) <year> <copyright holder>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction. See the LICENSE file for details.
```

Adapt the comment syntax for the file type (`#` for Python/Shell, `//` for JS/TS/Go, `<!-- -->` for HTML/XML, etc.).

### 3. Package Manifest

Create the project's package manifest (e.g. `pyproject.toml`, `package.json`, `Cargo.toml`):

- The `license` field must match the `LICENSE` file (use the SPDX identifier).
- Include the copyright holder in the authors/maintainers field.
- Set the initial version to `0.1.0`.
- Add a placeholder description (will be refined in `document_brand` mode).

### 4. README.md

Create an initial `README.md` with:

- Project name as heading
- One-line description placeholder
- License badge (always include)
- Installation section placeholder
- Usage section placeholder

**Badge reference:**

| Badge | When to include | Example source |
|-------|----------------|----------------|
| **License** | Always | `shields.io/badge/License-Apache%202.0-blue.svg` |
| **CI status** | After CI is configured | GitHub Actions badge URL |
| **Package version** | After publishing to registry | `shields.io/pypi/v/...` |
| **Language version** | After specifying in manifest | `shields.io/pypi/pyversions/...` |
| **Coverage** | After coverage service is configured | Codecov/Coveralls badge URL |

Add badges proactively as each becomes applicable.

### 5. CHANGELOG.md

Create `CHANGELOG.md` in the repository root:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
```

**Guidelines:**
- Update `CHANGELOG.md` in the same commit as the version bump
- Use standard categories: Added, Changed, Deprecated, Removed, Fixed, Security
- Omit empty categories
- Most recent versions at the top

### 6. .gitignore

Create or update `.gitignore` with language-appropriate patterns. Include at minimum:

- Build artifacts
- Virtual environment directories
- IDE/editor files
- OS-specific files (`.DS_Store`, `Thumbs.db`)
- Test/coverage output

### 7. Present for Approval

Present the scaffolded project to the developer for review:

- [ ] LICENSE file present and correct
- [ ] Copyright header format established
- [ ] Package manifest created with correct metadata
- [ ] README.md with license badge
- [ ] CHANGELOG.md initialized
- [ ] .gitignore configured

Once approved, proceed to coding:

```bash
project-guide mode {{ next_mode }}
```
