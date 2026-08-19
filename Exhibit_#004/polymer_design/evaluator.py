"""
Pluggable polymer evaluator.

SimplifiedPhysicsEvaluator remains the default engine and now delegates
physics calculations to polymer_engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from polymer_engine.chains.chain_statistics import effective_two_component_fractions
from polymer_engine.energetics.free_energy import FreeEnergyProxy, FreeEnergyResult
from polymer_engine.morphology.morphology_prediction import (
    MorphologyPredictor,
    MorphologyResult,
)
from polymer_engine.structure.domain_size import DomainSizeEstimator, DomainSizeResult
from polymer_engine.thermodynamics.chi_models import (
    ChiModel,
    ConstantChiModel,
    SolubilityParameterChiModel,
    build_chi_model,
)
from polymer_engine.thermodynamics.flory_huggins import compute_chiN

from .polymer import Polymer, load_monomers


@dataclass
class Prediction:
    polymer: Polymer
    chi: float
    N: float
    chiN: float
    segregation_regime: str
    morphology: str
    confidence: str
    confidence_score: float
    free_energy_score: float
    reasons: list[str] = field(default_factory=list)
    calculation_steps: list[str] = field(default_factory=list)
    free_energy_terms: dict[str, float] = field(default_factory=dict)
    engine: str = "simplified_physics_v1"
    notes: list[str] = field(default_factory=list)
    chi_model_name: str | None = None
    temperature_K: float | None = None
    domain_spacing_nm: float | None = None
    characteristic_length_nm: float | None = None
    radius_of_gyration_nm: float | None = None
    domain_size_model: str | None = None
    domain_size_assumptions: list[str] = field(default_factory=list)


class Evaluator(Protocol):
    def evaluate(self, polymer: Polymer) -> Prediction: ...


class SimplifiedPhysicsEvaluator:
    """Default explainable evaluator (preserved public interface)."""

    def __init__(
        self,
        monomers_path: str | Path | None = None,
        chi_model: ChiModel | None = None,
        segment_length_nm: float = 0.50,
    ) -> None:
        self.morphology_predictor = MorphologyPredictor()
        self.free_energy_proxy = FreeEnergyProxy()
        self.domain_size_estimator = DomainSizeEstimator(
            segment_length_nm=segment_length_nm
        )
        self.monomers: dict[str, dict[str, Any]] = {}
        self.default_chi_model = chi_model
        if monomers_path is not None:
            self.monomers = load_monomers(monomers_path)

    def _block_pair_labels(self, polymer: Polymer) -> tuple[str | None, str | None]:
        if len(polymer.blocks) < 2:
            return None, None
        return polymer.blocks[0].name, polymer.blocks[1].name

    def resolve_chi(self, polymer: Polymer) -> tuple[float, list[str], str, float | None]:
        """
        Resolve χ via ChiModel.

        Priority:
          1) evaluator-level default_chi_model
          2) polymer.chi_model_spec
          3) polymer.chi as ConstantChiModel (legacy JSON)
          4) solubility-parameter estimate from monomer data
        """
        polymer_A, polymer_B = self._block_pair_labels(polymer)
        T = polymer.temperature_K

        if self.default_chi_model is not None:
            result = self.default_chi_model.evaluate(T)
            return result.chi, result.explanation, result.model_name, result.temperature_K

        if polymer.chi_model_spec is not None:
            spec = dict(polymer.chi_model_spec)
            spec.setdefault("polymer_A", polymer_A)
            spec.setdefault("polymer_B", polymer_B)
            model = build_chi_model(spec)
            result = model.evaluate(T)
            return result.chi, result.explanation, result.model_name, result.temperature_K

        if polymer.chi is not None:
            # Preserve legacy report wording for existing examples.
            steps = [f"Using user-provided χ = {polymer.chi:.4g}"]
            model = ConstantChiModel(
                chi=polymer.chi,
                polymer_A=polymer_A,
                polymer_B=polymer_B,
            )
            # Evaluate for validation; keep legacy explanation text.
            model.evaluate(T)
            return polymer.chi, steps, "constant", T

        if len(polymer.blocks) >= 2 and self.monomers:
            a = self.monomers.get(polymer.blocks[0].name.lower())
            b = self.monomers.get(polymer.blocks[1].name.lower())
            if a and b:
                v_ref = 0.5 * (
                    float(a["molar_volume_cm3_mol"]) + float(b["molar_volume_cm3_mol"])
                )
                model = SolubilityParameterChiModel(
                    delta_a=float(a["solubility_parameter_MPa05"]),
                    delta_b=float(b["solubility_parameter_MPa05"]),
                    molar_volume_cm3_mol=v_ref,
                    polymer_A=polymer_A,
                    polymer_B=polymer_B,
                    default_temperature_K=T if T is not None else 298.15,
                )
                result = model.evaluate(T)
                return result.chi, result.explanation, result.model_name, result.temperature_K

        raise ValueError(
            f"Polymer '{polymer.name}' has no χ / chi_model, and χ could not be estimated "
            "from monomer solubility parameters."
        )

    def evaluate(self, polymer: Polymer) -> Prediction:
        polymer.validate()
        chi, chi_steps, chi_model_name, temperature_K = self.resolve_chi(polymer)
        N = polymer.degree_of_polymerization
        chin = compute_chiN(chi, N)

        f_map, arch_note = effective_two_component_fractions(
            fractions=polymer.volume_fractions,
            names=polymer.block_names,
            architecture=polymer.architecture,
        )

        morph: MorphologyResult = self.morphology_predictor.predict(
            f_values=f_map,
            chiN=chin.chiN,
            segregation_regime=chin.segregation_regime,
            architecture=polymer.architecture,
        )
        fe: FreeEnergyResult = self.free_energy_proxy.evaluate(
            chiN=chin.chiN,
            f_minor=morph.f_minor,
            morphology=morph,
        )
        domain: DomainSizeResult = self.domain_size_estimator.estimate(
            N=N,
            chi=chi,
            chiN=chin.chiN,
            morphology=morph.morphology,
            f_minor=morph.f_minor,
        )

        reasons = [arch_note] + morph.reasons
        calc_steps = (
            chi_steps + chin.explanation + fe.explanation + domain.explanation
        )
        notes = [
            "This is a simplified educational prediction.",
            "Replace SimplifiedPhysicsEvaluator with SCFT/MD/MC/database engines later.",
        ]

        return Prediction(
            polymer=polymer,
            chi=chi,
            N=N,
            chiN=chin.chiN,
            segregation_regime=chin.segregation_regime,
            morphology=morph.morphology,
            confidence=morph.confidence,
            confidence_score=morph.confidence_score,
            free_energy_score=fe.score,
            reasons=reasons,
            calculation_steps=calc_steps,
            free_energy_terms=fe.terms,
            notes=notes,
            chi_model_name=chi_model_name,
            temperature_K=temperature_K,
            domain_spacing_nm=domain.domain_spacing_nm,
            characteristic_length_nm=domain.characteristic_length_nm,
            radius_of_gyration_nm=domain.radius_of_gyration_nm,
            domain_size_model=domain.model,
            domain_size_assumptions=list(domain.assumptions),
        )
