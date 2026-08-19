"""SCFT chemical-potential fields w_A(r), w_B(r) and pressure-like field."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FieldState:
    w_A: np.ndarray
    w_B: np.ndarray
    pressure: np.ndarray

    def copy(self) -> "FieldState":
        return FieldState(
            w_A=self.w_A.copy(),
            w_B=self.w_B.copy(),
            pressure=self.pressure.copy(),
        )


def initialize_fields(
    n_grid: int,
    *,
    box_length: float,
    chiN: float,
    f_A: float,
    amplitude: float = 0.05,
    seed: int = 0,
) -> FieldState:
    """
    Initialize fields with a small 1D cosine perturbation (lamellar-like seed).

    This biases the solver toward a one-mode density wave when segregation is
    strong enough; it does not force a physical morphology assignment.
    """
    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, box_length, n_grid, endpoint=False)
    # Fundamental mode compatible with periodic box
    wave = amplitude * np.cos(2.0 * np.pi * x / box_length)
    noise = 0.01 * amplitude * rng.standard_normal(n_grid)
    # Antisymmetric seed: A-rich / B-rich contrast
    delta = wave + noise
    # Mean-field homogeneous reference: w_A ~ χN f_B, w_B ~ χN f_A
    w_A = chiN * (1.0 - f_A) + delta
    w_B = chiN * f_A - delta
    pressure = 0.5 * (w_A + w_B)
    return FieldState(w_A=w_A, w_B=w_B, pressure=pressure)
