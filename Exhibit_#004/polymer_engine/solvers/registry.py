"""Solver registry (implemented + placeholders)."""

from __future__ import annotations

from .analytical import AnalyticalSolver
from .base import Solver
from .monte_carlo import MonteCarloSolver
from .phase_field import PhaseFieldSolver
from .scft import SCFTSolver

_REGISTRY: dict[str, type[Solver]] = {
    "analytical": AnalyticalSolver,
    "phase_field": PhaseFieldSolver,
    "scft": SCFTSolver,
    "monte_carlo": MonteCarloSolver,
}


def list_solvers() -> dict[str, str]:
    """Return solver name -> status string."""
    return {
        "analytical": "implemented (rule-based / scaling adapter)",
        "phase_field": "implemented (1D toy Cahn–Hilliard demo)",
        "scft": "implemented (minimal 1D AB diblock mean-field SCFT)",
        "monte_carlo": "placeholder only (NotImplementedError)",
    }


def get_solver(name: str) -> Solver:
    key = name.lower().strip()
    if key not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown solver '{name}'. Known: {known}")
    return _REGISTRY[key]()
