"""Rank evaluated candidates against a design target."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp

from polymer_design.design.target import DesignTarget
from polymer_design.evaluator import Prediction
from polymer_design.validation.runner import morphologies_match


@dataclass
class ScoreBreakdown:
    morphology: float
    spacing: float
    thermodynamics: float
    confidence: float
    total: float
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class RankedCandidate:
    prediction: Prediction
    method: str
    assumptions: list[str]
    breakdown: ScoreBreakdown


def _morphology_component(pred: Prediction, target: DesignTarget) -> tuple[float, str]:
    if target.morphology is None:
        return 1.0, "No morphology target; full morphology credit."
    if morphologies_match(pred.morphology, target.morphology):
        return 1.0, f"Morphology match: predicted '{pred.morphology}' ≈ target '{target.morphology}'."
    return 0.0, f"Morphology mismatch: predicted '{pred.morphology}' vs target '{target.morphology}'."


def _spacing_component(pred: Prediction, target: DesignTarget) -> tuple[float, str]:
    if target.domain_spacing_nm is None:
        return 1.0, "No spacing target; full spacing credit."
    if pred.domain_spacing_nm is None:
        return 0.0, "Target spacing set, but prediction has no domain spacing (disordered)."
    err = abs(pred.domain_spacing_nm - target.domain_spacing_nm)
    # Smooth score in (0, 1]: exact match → 1
    score = 1.0 / (1.0 + err)
    return score, (
        f"|D_pred − D_target| = |{pred.domain_spacing_nm:.3g} − {target.domain_spacing_nm:.3g}| "
        f"= {err:.3g} nm → spacing_score = 1/(1+err) = {score:.4g}"
    )


def _thermo_component(pred: Prediction) -> tuple[float, str]:
    # Map free-energy proxy (lower better) to (0, 1) via logistic on -score.
    # Centered near 0 so typical ordered negative scores score high.
    x = -pred.free_energy_score
    score = 1.0 / (1.0 + exp(-x / 10.0))
    return score, (
        f"free_energy_proxy = {pred.free_energy_score:.4g}; "
        f"thermo_score = 1/(1+exp(FE/10)) = {score:.4g}"
    )


def _confidence_component(pred: Prediction) -> tuple[float, str]:
    return (
        pred.confidence_score,
        f"confidence_score = {pred.confidence_score:.3g} ({pred.confidence})",
    )


def score_prediction(pred: Prediction, target: DesignTarget) -> ScoreBreakdown:
    m, m_detail = _morphology_component(pred, target)
    s, s_detail = _spacing_component(pred, target)
    t, t_detail = _thermo_component(pred)
    c, c_detail = _confidence_component(pred)
    total = (
        target.weight_morphology * m
        + target.weight_spacing * s
        + target.weight_thermodynamics * t
        + target.weight_confidence * c
    )
    return ScoreBreakdown(
        morphology=m,
        spacing=s,
        thermodynamics=t,
        confidence=c,
        total=total,
        details={
            "morphology": m_detail,
            "spacing": s_detail,
            "thermodynamics": t_detail,
            "confidence": c_detail,
            "weights": (
                f"w_morph={target.weight_morphology}, w_space={target.weight_spacing}, "
                f"w_thermo={target.weight_thermodynamics}, w_conf={target.weight_confidence}"
            ),
        },
    )


def rank_candidates(
    predictions_with_meta: list[tuple[Prediction, str, list[str]]],
    target: DesignTarget,
) -> list[RankedCandidate]:
    ranked: list[RankedCandidate] = []
    for pred, method, assumptions in predictions_with_meta:
        ranked.append(
            RankedCandidate(
                prediction=pred,
                method=method,
                assumptions=assumptions,
                breakdown=score_prediction(pred, target),
            )
        )
    ranked.sort(key=lambda r: r.breakdown.total, reverse=True)
    return ranked
