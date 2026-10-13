"""
1D unit-cell length optimization for SCFT.

Design intent:
  - Optimize a single periodic length L (lamellar-like cell) by minimizing SCFT F(L).
  - Keep the API generic (callable free-energy evaluator) so future field users can
    swap in 2D/3D cell metrics or multi-parameter cells without rewriting this loop.
  - Do NOT encode ABC / complex morphologies here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class UnitCellScanResult:
    """Result of scanning candidate cell lengths."""

    candidate_lengths: list[float]
    free_energies: list[float]
    optimal_length: float
    optimal_free_energy: float
    method: str = "discrete 1D box-length scan (min F)"
    notes: list[str] = field(default_factory=list)


def scan_box_lengths(
    evaluate_free_energy: Callable[[float], float],
    candidate_lengths: list[float],
) -> UnitCellScanResult:
    """
    Evaluate F at each candidate L and return the minimizer.

    `evaluate_free_energy(L)` should run (or approximate) SCFT at fixed physics
    with only the cell length changed. Complex architecture search stays outside.
    """
    if len(candidate_lengths) < 2:
        raise ValueError("candidate_lengths needs at least two values")
    lengths = [float(L) for L in candidate_lengths]
    if any(L <= 0 for L in lengths):
        raise ValueError("box lengths must be > 0")

    energies: list[float] = []
    for L in lengths:
        energies.append(float(evaluate_free_energy(L)))

    best_i = min(range(len(energies)), key=lambda i: energies[i])
    return UnitCellScanResult(
        candidate_lengths=lengths,
        free_energies=energies,
        optimal_length=lengths[best_i],
        optimal_free_energy=energies[best_i],
        notes=[
            "1D periodic cell only (lamellar-like wavelength selection).",
            "Future users may replace evaluate_free_energy with 2D/3D unit-cell solvers.",
            "This scan does not identify cylinders/gyroid/network morphologies.",
        ],
    )


def default_length_grid(
    L_min: float,
    L_max: float,
    n_points: int = 7,
) -> list[float]:
    if n_points < 2 or L_min <= 0 or L_max <= L_min:
        raise ValueError("Need L_min > 0, L_max > L_min, n_points >= 2")
    if n_points == 2:
        return [L_min, L_max]
    step = (L_max - L_min) / (n_points - 1)
    return [L_min + i * step for i in range(n_points)]
