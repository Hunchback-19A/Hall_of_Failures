# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Batch-size limit. A request cannot raise it."""

from __future__ import annotations

import json
import os
from pathlib import Path

_LIMITS_PATH = Path(__file__).resolve().parents[1] / "run_limits.json"
_ENV = "POLYMER_DESIGN_MAX_CANDIDATES"
_VIS_ENV = "POLYMER_DESIGN_MAX_VISUALIZATION_BATCH"


def max_candidates() -> int:
    """Limit from POLYMER_DESIGN_MAX_CANDIDATES, otherwise run_limits.json."""
    raw = os.environ.get(_ENV, "").strip()
    if raw:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{_ENV} must be a positive integer") from exc
        if value < 1:
            raise ValueError(f"{_ENV} must be a positive integer")
        return value
    payload = json.loads(_LIMITS_PATH.read_text(encoding="utf-8"))
    value = int(payload["max_candidates"])
    if value < 1:
        raise ValueError("run_limits.json max_candidates must be a positive integer")
    return value


def max_visualization_batch() -> int:
    """How many morphology files one visualization batch may write.

    A request cannot raise this. The operator can, via run_limits.json or
    POLYMER_DESIGN_MAX_VISUALIZATION_BATCH.
    """
    raw = os.environ.get(_VIS_ENV, "").strip()
    if raw:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{_VIS_ENV} must be a positive integer") from exc
        if value < 1:
            raise ValueError(f"{_VIS_ENV} must be a positive integer")
        return value
    payload = json.loads(_LIMITS_PATH.read_text(encoding="utf-8"))
    value = int(payload["max_visualization_batch"])
    if value < 1:
        raise ValueError("run_limits.json max_visualization_batch must be a positive integer")
    return value
