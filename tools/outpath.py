"""Small output-path helpers shared by the tools."""
from __future__ import annotations

import os


def ensure_parent(path: str) -> None:
    """Create the directory that will hold `path` (safe for bare filenames)."""
    if not path:
        return
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)
