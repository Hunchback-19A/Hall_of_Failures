"""SCFT polymer architecture specs (start with AB diblock)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiblockSCFTSpec:
    """
    AB diblock in the standard dimensionless SCFT representation.

    Lengths are measured in units of R_g = a * sqrt(N/6).
    Contour variable s runs from 0 to 1 along the chain.

    Scope note for future field users:
      This educational core validates AB diblocks only. ABC / multiblock /
      blend architectures should be added as separate specs and solvers so the
      1D diblock path stays small and auditable.
    """

    f_A: float
    chiN: float
    architecture: str = "diblock"

    def validate(self) -> None:
        if self.architecture.lower() != "diblock":
            raise ValueError(
                "This SCFT prototype currently supports architecture='diblock' only "
                "(ABC / blends are extension points for future field-facing modules)."
            )
        if not (0.0 < self.f_A < 1.0):
            raise ValueError("f_A must be in (0, 1)")
        if self.chiN < 0:
            raise ValueError("chiN must be >= 0")

    @property
    def f_B(self) -> float:
        return 1.0 - self.f_A
