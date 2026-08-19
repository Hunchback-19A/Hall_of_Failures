"""
Morphology free-energy comparison framework.

Philosophy (equilibrium theory / SCFT):
  The stable morphology minimizes free energy. A full SCFT free-energy
  functional is not solved here. Instead we assemble named contributions
  (mixing, interface, stretching) that can later be replaced by SCFT/MD/MC.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polymer_engine.morphology.morphology_prediction import MorphologyResult

from .contributions import (
    FreeEnergyContext,
    FreeEnergyContribution,
    InterfaceContribution,
    MixingContribution,
    StretchingContribution,
)


@dataclass
class FreeEnergyResult:
    """
    Lower score is treated as 'better' for optimizer hooks.

    `contributions` holds the physics terms (mixing / interface / stretching).
    `terms` retains a flat dict used by the evaluator and legacy callers.
    """

    score: float
    terms: dict[str, float]
    explanation: list[str]
    contributions: dict[str, float] = field(default_factory=dict)


class MorphologyFreeEnergyModel:
    """
    Sum free-energy contributions for morphology comparison.

    Extra model-level penalties (confidence / phase-boundary ambiguity) are
    kept separate from the three physics contributions so the architecture
    stays clear while preserving prior numerical ranking behavior.
    """

    def __init__(
        self,
        contributions: list[FreeEnergyContribution] | None = None,
        include_confidence_penalty: bool = True,
    ) -> None:
        self.contributions = contributions or [
            MixingContribution(),
            InterfaceContribution(),
            StretchingContribution(),
        ]
        self.include_confidence_penalty = include_confidence_penalty

    def evaluate(
        self,
        chiN: float,
        f_minor: float,
        morphology: MorphologyResult,
    ) -> FreeEnergyResult:
        context = FreeEnergyContext(
            chiN=chiN,
            f_minor=f_minor,
            morphology=morphology,
        )
        explanation: list[str] = [
            "Self-assembly is treated as free-energy minimization at a conceptual level.",
            "F ≈ F_mixing + F_interface + F_stretching (+ optional stability penalties).",
            "This is a simplified educational model; replace contributions with SCFT/MD/MC later.",
        ]

        contribution_values: dict[str, float] = {}
        total = 0.0
        for term in self.contributions:
            result = term.evaluate(context)
            contribution_values[result.name] = result.value
            total += result.value
            explanation.extend(result.explanation)

        terms = dict(contribution_values)

        # Model-level ranking corrections (not SCFT physics).
        if context.is_ordered and self.include_confidence_penalty:
            confidence_penalty = 2.0 * (1.0 - morphology.confidence_score)
            boundary_penalty = (
                1.5 if "boundary" in " ".join(morphology.reasons).lower() else 0.0
            )
            terms["confidence_penalty"] = confidence_penalty
            terms["boundary_penalty"] = boundary_penalty
            total += confidence_penalty + boundary_penalty
            explanation.extend(
                [
                    "Stability penalties (ranking aids, not pure thermodynamics):",
                    f"  confidence_penalty = 2*(1 − confidence) = {confidence_penalty:.4g}",
                    f"  boundary_penalty = {boundary_penalty:.4g}",
                ]
            )

        explanation.append(
            f"Total free-energy proxy (lower is better for search) = {total:.4g}"
        )

        # Legacy aliases so older flat-term consumers still recognize keys.
        if not context.is_ordered:
            terms["disordered_mixing_proxy"] = contribution_values.get("mixing", 0.0)
        else:
            terms["segregation_gain"] = contribution_values.get("interface", 0.0)
            terms["stretch_penalty"] = contribution_values.get("stretching", 0.0)

        return FreeEnergyResult(
            score=total,
            terms=terms,
            explanation=explanation,
            contributions=contribution_values,
        )


class FreeEnergyProxy:
    """
    Backward-compatible facade used by SimplifiedPhysicsEvaluator.

    Delegates to MorphologyFreeEnergyModel so existing scores are preserved
    while exposing the contribution framework underneath.
    """

    def __init__(self, model: MorphologyFreeEnergyModel | None = None) -> None:
        self.model = model or MorphologyFreeEnergyModel()

    def evaluate(
        self,
        chiN: float,
        f_minor: float,
        morphology: MorphologyResult,
    ) -> FreeEnergyResult:
        return self.model.evaluate(chiN=chiN, f_minor=f_minor, morphology=morphology)
