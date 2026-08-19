"""SCFT free-energy evaluation for incompressible AB diblock melts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .density import DensityState
from .fields import FieldState


@dataclass
class FreeEnergyTerms:
    total: float
    minus_ln_Q: float
    interaction: float
    field: float
    formula: str


def scft_free_energy(
    fields: FieldState,
    density: DensityState,
    *,
    Q: float,
    chiN: float,
    box_length: float,
) -> FreeEnergyTerms:
    """
    Intensive free energy per chain (units of kT):

        F = −ln Q + (1/V) ∫ [ χN φ_A φ_B − w_A φ_A − w_B φ_B ] dr

    This is the standard mean-field diblock expression used in many educational
    codes (pressure terms absorbed into field definitions). Documented for
    transparency; not a universal SCFT free-energy convention for all ensembles.
    """
    dx = box_length / fields.w_A.size
    volume = box_length
    interaction = float(np.sum(chiN * density.phi_A * density.phi_B) * dx / volume)
    field = float(
        np.sum(-fields.w_A * density.phi_A - fields.w_B * density.phi_B) * dx / volume
    )
    minus_ln_Q = float(-np.log(Q))
    total = minus_ln_Q + interaction + field
    return FreeEnergyTerms(
        total=total,
        minus_ln_Q=minus_ln_Q,
        interaction=interaction,
        field=field,
        formula="F = -ln Q + (1/V)∫[χN φA φB - wA φA - wB φB] dr",
    )
