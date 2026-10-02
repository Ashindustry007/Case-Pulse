"""[Dev 2] Read-only adapter over Dev 1's tables (filled in by Task 8)."""
from __future__ import annotations

from pathlib import Path

from ..config import settings


def data_dir() -> Path:
    """Root that records.meta.file_path is relative to (patched in tests)."""
    return settings.data_dir
