"""
Numerical / analytical solver plugin interfaces.

Toy prototypes and future SCFT/MC methods share SimulationInput/Output.
"""

from .base import SimulationInput, SimulationOutput, Solver
from .analytical import AnalyticalSolver
from .phase_field import PhaseFieldSolver
from .scft import SCFTSolver
from .registry import get_solver, list_solvers

__all__ = [
    "SimulationInput",
    "SimulationOutput",
    "Solver",
    "AnalyticalSolver",
    "PhaseFieldSolver",
    "SCFTSolver",
    "get_solver",
    "list_solvers",
]
