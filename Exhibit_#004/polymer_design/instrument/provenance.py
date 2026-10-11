# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Versions recorded with every calculation."""

from __future__ import annotations

from pathlib import Path

from polymer_engine import __version__

_PROVENANCE = (
    Path(__file__).resolve().parents[2] / "third_party" / "pscfpp" / "PROVENANCE.txt"
)
PSCF_UPSTREAM = "https://github.com/dmorse/pscfpp"


def software_version() -> str:
    return __version__


def pscf_commit() -> str:
    """Commit hash recorded in the vendored PSCF provenance file."""
    if not _PROVENANCE.is_file():
        return "unavailable"
    for line in _PROVENANCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("Commit:"):
            return line.split(":", 1)[1].strip()
    return "unavailable"
