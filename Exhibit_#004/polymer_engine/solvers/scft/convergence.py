"""SCFT iteration residuals and convergence checks."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .density import DensityState
from .fields import FieldState


@dataclass
class ConvergenceState:
    iteration: int
    residual: float
    incompressibility_error: float
    free_energy: float
    history: list[float] = field(default_factory=list)

    @property
    def converged(self) -> bool:
        return False  # filled by monitor with tolerance


@dataclass
class ConvergenceMonitor:
    tolerance: float
    max_iterations: int
    history: list[float] = field(default_factory=list)

    def residual(self, fields: FieldState, density: DensityState, chiN: float) -> float:
        """
        Self-consistency residual:

            R = <(w_A - w_B - χN (φ_B - φ_A))^2>^{1/2}
              + <(φ_A + φ_B - 1)^2>^{1/2}
        """
        sc = fields.w_A - fields.w_B - chiN * (density.phi_B - density.phi_A)
        inc = density.phi_A + density.phi_B - 1.0
        r1 = float(np.sqrt(np.mean(sc**2)))
        r2 = float(np.sqrt(np.mean(inc**2)))
        return r1 + r2

    def update(
        self,
        iteration: int,
        fields: FieldState,
        density: DensityState,
        chiN: float,
        free_energy: float,
    ) -> ConvergenceState:
        res = self.residual(fields, density, chiN)
        self.history.append(res)
        state = ConvergenceState(
            iteration=iteration,
            residual=res,
            incompressibility_error=density.incompressibility_error,
            free_energy=free_energy,
            history=list(self.history),
        )
        return state

    def is_converged(self, state: ConvergenceState) -> bool:
        return state.residual < self.tolerance
