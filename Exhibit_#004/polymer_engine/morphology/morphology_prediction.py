"""Rule-based morphology prediction with explicit reasoning."""

from __future__ import annotations

from dataclasses import dataclass

from polymer_engine.thermodynamics.flory_huggins import SYMMETRIC_DIBLOCK_ODT_CHIN

from .phase_map import near_boundary, ordered_morphology_from_f


@dataclass
class MorphologyResult:
    morphology: str
    segregation_strength: float
    segregation_regime: str
    confidence: str
    confidence_score: float
    reasons: list[str]
    f_minor: float
    f_major: float


def _confidence_from_context(
    f_minor: float,
    chiN: float,
    architecture: str,
    is_near_boundary: bool,
) -> tuple[str, float, list[str]]:
    notes: list[str] = []
    score = 0.75

    if architecture.lower() != "diblock":
        score -= 0.25
        notes.append(
            "Architecture is not a simple AB diblock; the classical f–χN map is only a proxy."
        )

    if chiN < SYMMETRIC_DIBLOCK_ODT_CHIN:
        score = min(score, 0.45)
        notes.append("Below mean-field ODT; ordered-phase assignment is not applicable.")
    elif chiN < 15:
        score -= 0.15
        notes.append("Near the ODT; fluctuation effects (ignored here) can shift boundaries.")

    if is_near_boundary:
        score -= 0.20
        notes.append("Composition is close to a morphology boundary; prediction is ambiguous.")

    score = max(0.15, min(0.9, score))
    if score >= 0.7:
        label = "Medium-High"
    elif score >= 0.5:
        label = "Medium"
    elif score >= 0.35:
        label = "Low"
    else:
        label = "Very Low"
    return label, score, notes


class MorphologyPredictor:
    """Rule-based morphology estimator with explicit reasoning."""

    def predict(
        self,
        f_values: list[float],
        chiN: float,
        segregation_regime: str,
        architecture: str = "diblock",
    ) -> MorphologyResult:
        if not f_values:
            raise ValueError("f_values must not be empty")

        f_minor = min(f_values)
        f_major = max(f_values)
        reasons: list[str] = [
            "Microphase separation (not macrophase separation) is expected for a "
            "covalently linked block copolymer when χN is large enough.",
            f"Using minority fraction f_minor = {f_minor:.3f} (major = {f_major:.3f}).",
            f"Segregation strength χN = {chiN:.3f} ({segregation_regime}).",
        ]

        if chiN < SYMMETRIC_DIBLOCK_ODT_CHIN:
            morph = "disordered / mixed phase"
            reasons.append(
                f"χN below strong-ordering threshold (χN_ODT ≈ {SYMMETRIC_DIBLOCK_ODT_CHIN} "
                "for a symmetric diblock in mean-field theory)."
            )
            if chiN >= SYMMETRIC_DIBLOCK_ODT_CHIN * 0.7:
                reasons.append(
                    "χN is approaching the ODT; local composition fluctuations may appear "
                    "even if long-range order is not predicted."
                )
            is_near = False
        else:
            morph, morph_reasons = ordered_morphology_from_f(f_minor)
            reasons.extend(morph_reasons)
            reasons.append(
                "Morphology choice follows a simplified educational map of the "
                "classical diblock phases (S → C → G → L with increasing f_minor)."
            )
            is_near = near_boundary(f_minor)

        conf_label, conf_score, conf_notes = _confidence_from_context(
            f_minor, chiN, architecture, is_near
        )
        reasons.extend(conf_notes)

        return MorphologyResult(
            morphology=morph,
            segregation_strength=chiN,
            segregation_regime=segregation_regime,
            confidence=conf_label,
            confidence_score=conf_score,
            reasons=reasons,
            f_minor=f_minor,
            f_major=f_major,
        )
