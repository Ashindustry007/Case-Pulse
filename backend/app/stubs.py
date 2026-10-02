"""Phase 0 stub loader: serves fixtures/<name>.json validated against a contract model.
Owners replace each stub route with a real implementation; this file and fixtures/ are deleted by the freeze.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@lru_cache(maxsize=None)
def _raw(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def fixture(name: str, model: Any) -> Any:
    """Load fixture `name` and validate it as `model` (a Pydantic model or a typing expression like list[X])."""
    return TypeAdapter(model).validate_python(_raw(name))
