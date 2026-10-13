"""Thermodynamic helpers: Flory–Huggins χN and χ models."""

from .chi_models import (
    ChiEvaluation,
    ChiModel,
    ConstantChiModel,
    LinearTemperatureChiModel,
    SolubilityParameterChiModel,
    build_chi_model,
    estimate_chi_from_solubility,
)
from .flory_huggins import (
    INTERMEDIATE_SEGREGATION_UPPER,
    SYMMETRIC_DIBLOCK_ODT_CHIN,
    WEAK_SEGREGATION_UPPER,
    ChiNResult,
    compute_chiN,
)

__all__ = [
    "SYMMETRIC_DIBLOCK_ODT_CHIN",
    "WEAK_SEGREGATION_UPPER",
    "INTERMEDIATE_SEGREGATION_UPPER",
    "ChiNResult",
    "compute_chiN",
    "estimate_chi_from_solubility",
    "ChiEvaluation",
    "ChiModel",
    "ConstantChiModel",
    "LinearTemperatureChiModel",
    "SolubilityParameterChiModel",
    "build_chi_model",
]
