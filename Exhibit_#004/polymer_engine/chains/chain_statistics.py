"""
Basic chain / composition statistics.

Includes composition mapping helpers and ideal-chain size utilities.
"""

from __future__ import annotations

from polymer_engine.structure.domain_size import (
    DEFAULT_SEGMENT_LENGTH_NM,
    radius_of_gyration_nm,
)


def minority_fraction(f_values: list[float]) -> float:
    if not f_values:
        raise ValueError("f_values must not be empty")
    return min(f_values)


def effective_two_component_fractions(
    fractions: list[float],
    names: list[str],
    architecture: str,
) -> tuple[list[float], str]:
    """
    Map architecture to composition used by the classical diblock phase map.

    For ABA-like triblocks with identical end chemistries, collapse the two ends.
    """
    arch = architecture.lower()
    if (
        arch == "triblock"
        and len(fractions) == 3
        and len(names) == 3
        and names[0].lower() == names[2].lower()
    ):
        f_map = [fractions[0] + fractions[2], fractions[1]]
        note = (
            "Triblock mapped to effective two-component composition "
            f"(ends={f_map[0]:.3f}, mid={f_map[1]:.3f}) for the classical phase map."
        )
        return f_map, note
    return list(fractions), f"Architecture: {architecture}"
