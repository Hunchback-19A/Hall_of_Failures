"""
Minimal SCFT framework for AB diblock copolymers (Gaussian chains, mean-field χ).

Educational scope: 1D AB only.
Future field users can extend with ABC / 2D–3D / full unit-cell suites without
rewriting this diblock core.
"""

from .models import DiblockSCFTSpec
from .propagator import mde_cpp_available, resolve_propagator_backend
from .solver import SCFTSolver
from .unit_cell import UnitCellScanResult, default_length_grid, scan_box_lengths

__all__ = [
    "SCFTSolver",
    "DiblockSCFTSpec",
    "UnitCellScanResult",
    "default_length_grid",
    "scan_box_lengths",
    "mde_cpp_available",
    "resolve_propagator_backend",
]
