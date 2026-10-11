"""Transparent design-exploration reports with score breakdowns."""

from __future__ import annotations

from polymer_design.design.ranking import RankedCandidate
from polymer_design.design.target import DesignTarget


def format_design_report(
    target: DesignTarget,
    ranked: list[RankedCandidate],
    *,
    n_evaluated: int,
    top_k: int | None = None,
) -> str:
    k = top_k if top_k is not None else target.top_k
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append("Inverse design exploration report")
    lines.append("Method: local monomer grid + SimplifiedPhysicsEvaluator ranking")
    lines.append("Note: exploration framework — not claimed global optimization.")
    lines.append("=" * 64)
    lines.extend(target.summary_lines())
    lines.append(f"Candidates evaluated: {n_evaluated}")
    lines.append(f"Showing top {min(k, len(ranked))} of {len(ranked)}")
    lines.append("")

    for i, item in enumerate(ranked[:k], start=1):
        p = item.prediction
        poly = p.polymer
        b = item.breakdown
        lines.append("-" * 64)
        lines.append(f"Rank {i}: {poly.name}")
        lines.append("")
        lines.append("Candidate:")
        lines.append(f"  {poly.name}")
        lines.append(f"  blocks: {poly.composition_summary()}")
        lines.append("")
        lines.append("Method:")
        lines.append(f"  {item.method}")
        lines.append("")
        lines.append("Parameters:")
        lines.append(f"  architecture = {poly.architecture}")
        lines.append(f"  χ = {p.chi:.4g}")
        lines.append(f"  N = {p.N:.4g}")
        lines.append(f"  χN = {p.chiN:.4g}")
        if p.temperature_K is not None:
            lines.append(f"  T = {p.temperature_K:.4g} K")
        lines.append("")
        lines.append("Predictions:")
        lines.append(f"  morphology = {p.morphology}")
        lines.append(f"  segregation regime = {p.segregation_regime}")
        if p.domain_spacing_nm is None:
            lines.append("  domain spacing = n/a")
        else:
            lines.append(f"  domain spacing = {p.domain_spacing_nm:.3g} nm")
        lines.append(f"  free-energy proxy = {p.free_energy_score:.4g}")
        lines.append(f"  confidence = {p.confidence} ({p.confidence_score:.2f})")
        lines.append("")
        lines.append("Score:")
        lines.append(f"  total = {b.total:.4g}  (higher is better)")
        lines.append("  breakdown:")
        lines.append(f"    morphology      = {b.morphology:.4g}")
        lines.append(f"    spacing         = {b.spacing:.4g}")
        lines.append(f"    thermodynamics  = {b.thermodynamics:.4g}")
        lines.append(f"    confidence      = {b.confidence:.4g}")
        lines.append(f"  {b.details.get('weights', '')}")
        for key in ("morphology", "spacing", "thermodynamics", "confidence"):
            lines.append(f"    · {b.details.get(key, '')}")
        lines.append("")
        lines.append("Assumptions:")
        for a in item.assumptions:
            lines.append(f"  - {a}")
        lines.append("")

    lines.append("=" * 64)
    return "\n".join(lines)
