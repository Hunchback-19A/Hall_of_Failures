"""
Professional scientific reports for polymer researchers.

Sections:
  A) Scientific interpretation
  B) Numerical details
  C) Assumptions and limitations
"""

from __future__ import annotations

from typing import Any

from polymer_engine.output.report_generator import format_report
from polymer_engine.reporting.interpretation import (
    ScientificInterpretation,
    interpret_prediction,
    interpret_simulation,
)
from polymer_engine.thermodynamics.flory_huggins import SYMMETRIC_DIBLOCK_ODT_CHIN


def _section(title: str) -> list[str]:
    return ["", "─" * 64, title, "─" * 64, ""]


def format_interpretation_block(interp: ScientificInterpretation) -> list[str]:
    lines: list[str] = []
    lines.extend(_section("Scientific interpretation"))
    lines.append(f"System:\n{interp.system}")
    lines.append("")
    lines.append(f"Numerical state:\n{interp.numerical_state}")
    lines.append("")
    lines.extend(interp.claim_lines())
    return lines


def format_prediction_scientific_report(
    prediction: Any,
    *,
    show_calculations: bool = True,
) -> str:
    """Chemist-facing wrapper around existing Prediction reports."""
    interp = interpret_prediction(prediction)
    lines = format_interpretation_block(interp)
    lines.extend(_section("Numerical details"))
    # Preserve the full legacy technical report unchanged beneath the interpretation.
    lines.append(format_report(prediction, show_calculations=show_calculations))
    lines.extend(_section("Assumptions and limitations"))
    lines.append(
        f"ODT reference used for interpretation: mean-field symmetric-diblock "
        f"χN_ODT ≈ {SYMMETRIC_DIBLOCK_ODT_CHIN}."
    )
    lines.append(
        "Morphology labels from the analytical map are educational phase-window "
        "assignments, not SCFT-ranked equilibrium structures."
    )
    if getattr(prediction, "domain_size_assumptions", None):
        for item in prediction.domain_size_assumptions:
            lines.append(f"- {item}")
    for note in getattr(prediction, "notes", None) or []:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def format_simulation_scientific_report(
    output: Any,
    *,
    sim_input: Any | None = None,
) -> str:
    """Chemist-facing report for SimulationOutput."""
    interp = interpret_simulation(output, sim_input=sim_input)
    lines = format_interpretation_block(interp)

    lines.extend(_section("Numerical details"))
    lines.append(f"Solver: {output.solver_name}")
    lines.append(f"Success: {output.success}")
    lines.append(f"Energy: {float(output.energy):.6g}")
    lines.append(f"χN: {float(output.chiN):.4g}")
    if sim_input is not None:
        lines.append("")
        lines.append("Parameters:")
        lines.append(f"  name = {sim_input.name}")
        lines.append(f"  architecture = {sim_input.architecture}")
        lines.append(f"  volume fractions = {list(sim_input.volume_fractions)}")
        lines.append(f"  χ = {sim_input.chi:.4g}")
        lines.append(f"  N = {sim_input.degree_of_polymerization:.4g}")
        lines.append(f"  χN = {sim_input.chiN:.4g}")
        lines.append(f"  n_grid = {sim_input.n_grid}")
        lines.append(f"  timestep = {sim_input.timestep}")
        lines.append(f"  n_iterations = {sim_input.n_iterations}")
        lines.append(f"  random_seed = {sim_input.random_seed}")

    lines.append("")
    lines.append("Numerical results:")
    lines.append(f"  morphology label = {output.morphology}")
    if isinstance(output.structure, dict):
        for key in (
            "phi_min",
            "phi_max",
            "phi_amplitude",
            "phi_A_amplitude",
            "phi_A_min",
            "phi_A_max",
            "mean_phi",
            "domain_spacing_nm",
            "radius_of_gyration_nm",
            "domain_size_model",
            "f_minor",
            "f_A",
            "f_B",
            "Q",
        ):
            if key in output.structure:
                lines.append(f"  {key} = {output.structure[key]}")
        if "order_parameter_phi" in output.structure:
            phi = output.structure["order_parameter_phi"]
            if isinstance(phi, list):
                lines.append(f"  order_parameter_phi = list[{len(phi)}] (truncated in report)")

    lines.append("")
    lines.append("Convergence:")
    for k, v in (output.convergence or {}).items():
        if k == "energy_samples" and isinstance(v, list) and len(v) > 6:
            lines.append(f"  {k}: list[{len(v)}] (truncated)")
        else:
            lines.append(f"  {k}: {v}")

    lines.append("")
    lines.append("Method:")
    for k, v in (output.method_details or {}).items():
        lines.append(f"  {k}: {v}")

    # Preserve raw dump for validation/debugging (original summary content).
    lines.append("")
    lines.append("Raw solver summary:")
    lines.append(output.format() if hasattr(output, "format") else str(output))

    lines.extend(_section("Assumptions and limitations"))
    for a in output.assumptions or []:
        lines.append(f"- {a}")
    for n in output.notes or []:
        lines.append(f"- {n}")
    if interp.is_toy_field_model:
        lines.append(
            "- Toy phase-field outputs must not be read as lamellae/cylinders/gyroid predictions."
        )
    lines.append(
        f"- Interpretation ODT anchor: χN_ODT ≈ {SYMMETRIC_DIBLOCK_ODT_CHIN} "
        "(mean-field symmetric diblock reference used in this package)."
    )
    lines.append("")
    return "\n".join(lines)
