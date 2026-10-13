"""Segment densities from chain propagators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .propagator import PropagatorResult


@dataclass
class DensityState:
    phi_A: np.ndarray
    phi_B: np.ndarray
    incompressibility_error: float


def densities_from_propagators(
    prop: PropagatorResult,
    *,
    f_A: float,
    box_length: float,
) -> DensityState:
    """
    φ_K(r) = (1/Q) ∫_{s∈K} q(r,s) q†(r,s) ds

    Contour integrals use the trapezoid rule on the stored s-grid.
    """
    ns = prop.q.shape[0] - 1
    ds = 1.0 / ns
    nx = prop.q.shape[1]
    # index i corresponds to s = i/ns
    i_cut = int(round(f_A * ns))
    i_cut = min(max(i_cut, 1), ns - 1)

    qq = prop.q * prop.q_dagger
    # Trapezoidal weights along contour
    w = np.ones(ns + 1)
    w[0] = 0.5
    w[-1] = 0.5

    phi_A = np.zeros(nx)
    phi_B = np.zeros(nx)
    for i in range(0, i_cut + 1):
        phi_A += w[i] * qq[i]
    for i in range(i_cut, ns + 1):
        phi_B += w[i] * qq[i]
    # Avoid double-counting the cut index
    phi_A -= 0.5 * w[i_cut] * qq[i_cut]
    phi_B -= 0.5 * w[i_cut] * qq[i_cut]

    phi_A *= ds / prop.Q
    phi_B *= ds / prop.Q

    # Normalize softly to enforce mean composition (reduces grid bias)
    mean_A = float(np.mean(phi_A))
    mean_B = float(np.mean(phi_B))
    if mean_A > 0:
        phi_A *= f_A / mean_A
    if mean_B > 0:
        phi_B *= (1.0 - f_A) / mean_B

    err = float(np.max(np.abs(phi_A + phi_B - 1.0)))
    return DensityState(phi_A=phi_A, phi_B=phi_B, incompressibility_error=err)
