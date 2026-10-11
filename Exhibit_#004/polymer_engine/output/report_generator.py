"""Human-readable scientific reports (duck-typed prediction objects)."""

from __future__ import annotations

from typing import Any, Protocol


class ReportablePrediction(Protocol):
    polymer: Any
    chi: float
    N: float
    chiN: float
    morphology: str
    segregation_regime: str
    reasons: list[str]
    confidence: str
    confidence_score: float
    free_energy_score: float
    engine: str
    calculation_steps: list[str]
    notes: list[str]
    domain_spacing_nm: float | None
    characteristic_length_nm: float | None
    radius_of_gyration_nm: float | None
    domain_size_model: str | None
    domain_size_assumptions: list[str]


def format_report(prediction: ReportablePrediction, show_calculations: bool = True) -> str:
    p = prediction.polymer
    lines = [
        "-" * 64,
        f"Polymer: {p.name}",
        "",
        "Architecture:",
        p.architecture.capitalize(),
        "",
        "Blocks:",
        p.composition_summary(),
        "",
        "Parameters:",
        f"χ = {prediction.chi:.4g}",
        f"N = {prediction.N:.4g}",
        f"χN = {prediction.chiN:.4g}",
        "",
        "Prediction:",
        prediction.morphology[0].upper() + prediction.morphology[1:],
        f"Segregation regime: {prediction.segregation_regime}",
        "",
        "Reason:",
    ]
    for reason in prediction.reasons:
        lines.append(f"  - {reason}")

    lines.extend(
        [
            "",
            "Confidence:",
            f"{prediction.confidence} ({prediction.confidence_score:.2f})",
            "",
            f"Free-energy proxy score (lower ~ more favored for search): {prediction.free_energy_score:.4g}",
            f"Engine: {prediction.engine}",
        ]
    )

    # Domain-size block (Phase 4)
    domain_spacing = getattr(prediction, "domain_spacing_nm", None)
    rg = getattr(prediction, "radius_of_gyration_nm", None)
    domain_model = getattr(prediction, "domain_size_model", None)
    assumptions = getattr(prediction, "domain_size_assumptions", None) or []

    lines.extend(["", "Predicted domain spacing:"])
    if domain_spacing is None:
        lines.append("n/a (disordered / mixed; no microdomain lattice)")
    else:
        lines.append(f"{domain_spacing:.3g} nm")
    if rg is not None:
        lines.append(f"Characteristic coil size R_g: {rg:.3g} nm")
    if domain_model:
        lines.extend(["", "Model:", domain_model])
    if assumptions and show_calculations:
        lines.append("Assumptions:")
        for item in assumptions:
            lines.append(f"  - {item}")

    if show_calculations and prediction.calculation_steps:
        lines.extend(["", "Calculation steps:"])
        for step in prediction.calculation_steps:
            lines.append(f"  • {step}")

    if prediction.notes:
        lines.extend(["", "Note:"])
        for note in prediction.notes:
            lines.append(note)

    lines.append("-" * 64)
    return "\n".join(lines)


def print_report(prediction: ReportablePrediction, show_calculations: bool = True) -> None:
    print(format_report(prediction, show_calculations=show_calculations))
