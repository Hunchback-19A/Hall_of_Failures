"""
Free-energy contribution interfaces.

Equilibrium morphology selection is framed as minimization of a free-energy
functional. Full SCFT is not implemented; these contributions provide a clean
place to plug improved physics later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from polymer_engine.morphology.morphology_prediction import MorphologyResult
from polymer_engine.thermodynamics.flory_huggins import SYMMETRIC_DIBLOCK_ODT_CHIN


@dataclass
class FreeEnergyContext:
    """Inputs shared by all free-energy contributions."""

    chiN: float
    f_minor: float
    morphology: MorphologyResult

    @property
    def is_ordered(self) -> bool:
        return self.chiN >= SYMMETRIC_DIBLOCK_ODT_CHIN


@dataclass
class ContributionResult:
    name: str
    value: float
    explanation: list[str] = field(default_factory=list)


class FreeEnergyContribution(ABC):
    """One term in a morphology free-energy comparison."""

    name: str

    @abstractmethod
    def evaluate(self, context: FreeEnergyContext) -> ContributionResult:
        raise NotImplementedError


class MixingContribution(FreeEnergyContribution):
    """
    Mixing / disordered-state contribution.

    Simplified model (educational):
      below ODT: (χN_ODT − χN)^2  (favors remaining mixed when far below ODT)
      above ODT: 0
    """

    name = "mixing"

    def evaluate(self, context: FreeEnergyContext) -> ContributionResult:
        if not context.is_ordered:
            value = (SYMMETRIC_DIBLOCK_ODT_CHIN - context.chiN) ** 2
            return ContributionResult(
                name=self.name,
                value=value,
                explanation=[
                    "Mixing contribution (disordered melt proxy):",
                    f"  F_mix ≈ (χN_ODT − χN)^2 = {value:.4g}",
                ],
            )
        return ContributionResult(
            name=self.name,
            value=0.0,
            explanation=[
                "Mixing contribution: 0 (ordered regime; mixing term not applied).",
            ],
        )


class InterfaceContribution(FreeEnergyContribution):
    """
    Interfacial / segregation contribution.

    Simplified model (educational):
      below ODT: 0
      above ODT: −(χN − χN_ODT)
        (more segregation strength lowers the proxy energy)
    """

    name = "interface"

    def evaluate(self, context: FreeEnergyContext) -> ContributionResult:
        if not context.is_ordered:
            return ContributionResult(
                name=self.name,
                value=0.0,
                explanation=[
                    "Interface contribution: 0 (no ordered interfaces below ODT).",
                ],
            )
        value = -(context.chiN - SYMMETRIC_DIBLOCK_ODT_CHIN)
        return ContributionResult(
            name=self.name,
            value=value,
            explanation=[
                "Interface / segregation contribution:",
                f"  F_int ≈ −(χN − χN_ODT) = {value:.4g}",
            ],
        )


class StretchingContribution(FreeEnergyContribution):
    """
    Chain-stretching contribution.

    Simplified model (educational):
      below ODT: 0
      above ODT: 8 (0.5 − f_minor)^2
        (asymmetric compositions pay a larger stretching penalty)
    """

    name = "stretching"

    def evaluate(self, context: FreeEnergyContext) -> ContributionResult:
        if not context.is_ordered:
            return ContributionResult(
                name=self.name,
                value=0.0,
                explanation=[
                    "Stretching contribution: 0 (homogeneous melt; no domain filling).",
                ],
            )
        value = 8.0 * (0.5 - context.f_minor) ** 2
        return ContributionResult(
            name=self.name,
            value=value,
            explanation=[
                "Chain-stretching contribution:",
                f"  F_str ≈ 8*(0.5 − f_minor)^2 = {value:.4g}",
            ],
        )
