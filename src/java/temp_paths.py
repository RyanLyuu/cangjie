from __future__ import annotations

import os
import tempfile
from pathlib import Path


IS_WINDOWS = os.name == "nt"


def short_temporary_directory(
    *,
    prefix: str = "tmp-",
    workspace: str | Path | None = None,
    windows_parent: str | Path | None = None,
) -> tempfile.TemporaryDirectory:
    """Create a TemporaryDirectory while keeping Windows paths short.

    On Windows, callers can provide a workspace-local parent so child tools
    do not receive a long system temporary path. Other platforms retain the
    standard tempfile location. The returned object intentionally has the
    same lifetime and cleanup contract as tempfile.TemporaryDirectory.
    """
    directory = None
    if IS_WINDOWS:
        parent = windows_parent or workspace
        if parent is not None:
            parent_path = Path(parent)
            parent_path.mkdir(parents=True, exist_ok=True)
            directory = str(parent_path)

    return tempfile.TemporaryDirectory(prefix=prefix, dir=directory)
