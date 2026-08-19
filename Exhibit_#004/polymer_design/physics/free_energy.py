"""Compatibility shim — logic lives in polymer_engine.energetics."""

from polymer_engine.energetics.free_energy import (
    FreeEnergyProxy,
    FreeEnergyResult,
    MorphologyFreeEnergyModel,
)
from polymer_engine.energetics.contributions import (
    ContributionResult,
    FreeEnergyContext,
    FreeEnergyContribution,
    InterfaceContribution,
    MixingContribution,
    StretchingContribution,
)

__all__ = [
    "FreeEnergyProxy",
    "FreeEnergyResult",
    "MorphologyFreeEnergyModel",
    "FreeEnergyContext",
    "ContributionResult",
    "FreeEnergyContribution",
    "MixingContribution",
    "InterfaceContribution",
    "StretchingContribution",
]
