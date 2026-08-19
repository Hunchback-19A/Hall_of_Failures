"""
Flexible χ models for block copolymer thermodynamics.

Supported now:
  - ConstantChiModel
  - LinearTemperatureChiModel  (χ = A + B/T)
  - SolubilityParameterChiModel

Literature databases / scraping are intentionally out of scope.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChiEvaluation:
    """Result of evaluating a χ model at a given temperature."""

    chi: float
    temperature_K: float | None
    model_name: str
    polymer_A: str | None = None
    polymer_B: str | None = None
    explanation: list[str] = field(default_factory=list)


class ChiModel(ABC):
    """
    Interface for χ providers.

    Example conceptual usage:
        model = ConstantChiModel(polymer_A="PS", polymer_B="PEO", chi=0.05)
        chi = model.evaluate(temperature_K=423).chi
    """

    polymer_A: str | None
    polymer_B: str | None

    @abstractmethod
    def evaluate(self, temperature_K: float | None = None) -> ChiEvaluation:
        """Return χ (and explanation) at the requested temperature."""


@dataclass
class ConstantChiModel(ChiModel):
    """χ independent of temperature."""

    chi: float
    polymer_A: str | None = None
    polymer_B: str | None = None

    def __post_init__(self) -> None:
        if self.chi < 0:
            raise ValueError("chi must be >= 0")

    def evaluate(self, temperature_K: float | None = None) -> ChiEvaluation:
        pair = ""
        if self.polymer_A and self.polymer_B:
            pair = f" for {self.polymer_A}/{self.polymer_B}"
        steps = [
            f"ConstantChiModel{pair}: χ = {self.chi:.4g} (temperature-independent)",
        ]
        if temperature_K is not None:
            steps.append(
                f"Requested T = {temperature_K:.2f} K was ignored by ConstantChiModel."
            )
        return ChiEvaluation(
            chi=self.chi,
            temperature_K=temperature_K,
            model_name="constant",
            polymer_A=self.polymer_A,
            polymer_B=self.polymer_B,
            explanation=steps,
        )


@dataclass
class LinearTemperatureChiModel(ChiModel):
    """
    Simple temperature-dependent model used in many polymer studies:

        χ(T) = A + B / T

    with T in kelvin. A and B are user-supplied parameters (not looked up).
    """

    A: float
    B: float
    polymer_A: str | None = None
    polymer_B: str | None = None
    default_temperature_K: float = 298.15

    def evaluate(self, temperature_K: float | None = None) -> ChiEvaluation:
        T = self.default_temperature_K if temperature_K is None else float(temperature_K)
        if T <= 0:
            raise ValueError("temperature_K must be > 0")
        chi = self.A + self.B / T
        if chi < 0:
            raise ValueError(
                f"χ(T) = A + B/T evaluated to {chi:.4g} < 0 at T={T:.2f} K; "
                "check A and B."
            )
        pair = ""
        if self.polymer_A and self.polymer_B:
            pair = f" for {self.polymer_A}/{self.polymer_B}"
        steps = [
            f"LinearTemperatureChiModel{pair}: χ(T) = A + B/T",
            f"  A = {self.A:.4g}, B = {self.B:.4g}, T = {T:.2f} K",
            f"  χ = {self.A:.4g} + {self.B:.4g}/{T:.2f} = {chi:.4g}",
        ]
        return ChiEvaluation(
            chi=chi,
            temperature_K=T,
            model_name="linear_temperature",
            polymer_A=self.polymer_A,
            polymer_B=self.polymer_B,
            explanation=steps,
        )


@dataclass
class SolubilityParameterChiModel(ChiModel):
    """
    Rough Flory–Huggins estimate from Hildebrand solubility parameters:

        χ ≈ (V / RT) (δ_A − δ_B)^2
    """

    delta_a: float
    delta_b: float
    molar_volume_cm3_mol: float
    polymer_A: str | None = None
    polymer_B: str | None = None
    default_temperature_K: float = 298.15

    def evaluate(self, temperature_K: float | None = None) -> ChiEvaluation:
        T = self.default_temperature_K if temperature_K is None else float(temperature_K)
        chi, steps = estimate_chi_from_solubility(
            self.delta_a,
            self.delta_b,
            self.molar_volume_cm3_mol,
            temperature_K=T,
        )
        if self.polymer_A and self.polymer_B:
            steps = [
                f"SolubilityParameterChiModel for {self.polymer_A}/{self.polymer_B}"
            ] + steps
        return ChiEvaluation(
            chi=chi,
            temperature_K=T,
            model_name="solubility_parameter",
            polymer_A=self.polymer_A,
            polymer_B=self.polymer_B,
            explanation=steps,
        )


def estimate_chi_from_solubility(
    delta_a: float,
    delta_b: float,
    molar_volume_cm3_mol: float,
    temperature_K: float = 298.15,
) -> tuple[float, list[str]]:
    """
    Rough Flory–Huggins estimate:

        χ ≈ (V / RT) (δ_A − δ_B)^2

    where δ are Hildebrand solubility parameters (MPa^0.5) and V is a
    reference molar volume (cm^3/mol). This is a coarse chemical estimate,
    not a fitted experimental χ(T).
    """
    # R in J/(mol·K) = cm^3·MPa/(mol·K)
    R = 8.314
    diff = delta_a - delta_b
    chi = (molar_volume_cm3_mol / (R * temperature_K)) * (diff**2)
    steps = [
        "Estimated χ from solubility parameters:",
        f"  δ_A = {delta_a:.3g} MPa^0.5, δ_B = {delta_b:.3g} MPa^0.5",
        f"  V = {molar_volume_cm3_mol:.3g} cm^3/mol, T = {temperature_K:.2f} K",
        f"  χ ≈ (V/RT)(δ_A−δ_B)^2 = {chi:.4g}",
        "Warning: solubility-parameter χ is approximate; prefer measured χ when available.",
    ]
    return chi, steps


def build_chi_model(spec: dict[str, Any]) -> ChiModel:
    """
    Construct a ChiModel from a small JSON-friendly dict.

    Examples:
      {"type": "constant", "chi": 0.04, "polymer_A": "PS", "polymer_B": "PMMA"}
      {"type": "linear_temperature", "A": -0.01, "B": 20.0, "polymer_A": "PS", "polymer_B": "PEO"}
      {"type": "solubility_parameter", "delta_a": 18.6, "delta_b": 20.2, "molar_volume_cm3_mol": 68.5}
    """
    if not isinstance(spec, dict) or "type" not in spec:
        raise ValueError("chi_model spec must be a dict with a 'type' field")

    model_type = str(spec["type"]).lower().strip()
    polymer_A = spec.get("polymer_A")
    polymer_B = spec.get("polymer_B")

    if model_type in {"constant", "const"}:
        if "chi" not in spec:
            raise ValueError("constant chi_model requires 'chi'")
        return ConstantChiModel(
            chi=float(spec["chi"]),
            polymer_A=polymer_A,
            polymer_B=polymer_B,
        )

    if model_type in {"linear_temperature", "linear", "a_plus_b_over_t"}:
        if "A" not in spec or "B" not in spec:
            raise ValueError("linear_temperature chi_model requires 'A' and 'B'")
        kwargs: dict[str, Any] = {
            "A": float(spec["A"]),
            "B": float(spec["B"]),
            "polymer_A": polymer_A,
            "polymer_B": polymer_B,
        }
        if "default_temperature_K" in spec:
            kwargs["default_temperature_K"] = float(spec["default_temperature_K"])
        return LinearTemperatureChiModel(**kwargs)

    if model_type in {"solubility_parameter", "solubility", "hildebrand"}:
        required = ("delta_a", "delta_b", "molar_volume_cm3_mol")
        missing = [k for k in required if k not in spec]
        if missing:
            raise ValueError(f"solubility_parameter chi_model missing: {', '.join(missing)}")
        kwargs = {
            "delta_a": float(spec["delta_a"]),
            "delta_b": float(spec["delta_b"]),
            "molar_volume_cm3_mol": float(spec["molar_volume_cm3_mol"]),
            "polymer_A": polymer_A,
            "polymer_B": polymer_B,
        }
        if "default_temperature_K" in spec:
            kwargs["default_temperature_K"] = float(spec["default_temperature_K"])
        return SolubilityParameterChiModel(**kwargs)

    raise ValueError(
        f"Unknown chi_model type '{spec['type']}'. "
        "Supported: constant, linear_temperature, solubility_parameter."
    )
