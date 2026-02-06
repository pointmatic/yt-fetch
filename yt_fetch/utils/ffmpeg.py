# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""ffmpeg detection and helpers."""

from __future__ import annotations

import shutil


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is found on PATH."""
    return shutil.which("ffmpeg") is not None
