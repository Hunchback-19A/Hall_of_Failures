# Copyright (C) 2026 Disquietude
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Optional PSCF free-energy section for the design report."""

from __future__ import annotations

from polymer_engine.solvers.pscf_rpc.runner import CHIN_CONVENTION, best_converged, run_cells


def design_pscf_section(
    rows: list[tuple[str, str, list[float], float]],
    *,
    timeout_s: float = 3600.0,
) -> str:
    """
    Rescore diblock rows with pscf_rpc.

    Each row is (name, architecture, volume fractions, chiN).
    Analytical ranking is left unchanged when PSCF cannot run.
    """
    lines = [
        "",
        "=" * 64,
        "PSCF periodic free-energy check (pscf_rpc)",
        CHIN_CONVENTION,
        "Cells: lamellae, hexagonal cylinders, gyroid, BCC spheres.",
        "Lowest converged fHelmholtz is preferred.",
        "=" * 64,
    ]
    scored: list[tuple[float, str, str]] = []
    for name, architecture, fractions, chi_n in rows:
        if architecture.lower() != "diblock" or len(fractions) < 2:
            lines.append(f"{name}: skipped (pscf_rpc adapter is AB diblock only).")
            continue
        error, runs = run_cells(float(fractions[0]), float(chi_n), ["lam", "hex", "gyr", "bcc"], timeout_s=timeout_s)
        if error:
            lines.append(error)
            lines.append("Analytical ranking is unchanged.")
            return "\n".join(lines)
        winner = best_converged(runs)
        if winner is None or winner.free_energy is None:
            lines.append(f"{name}: no converged cell. χN = {chi_n:.4g}")
            continue
        scored.append((float(winner.free_energy), name, winner.morphology))
        lines.append(
            f"{name}: {winner.morphology}, fHelmholtz = {winner.free_energy:.8g}, χN = {chi_n:.4g}"
        )
    if scored:
        lines.append("")
        lines.append("Order by ascending fHelmholtz (PSCF only; analytical ranks stay above):")
        for index, (energy, name, morphology) in enumerate(sorted(scored), start=1):
            lines.append(f"  {index}. {name}: {morphology}, fHelmholtz = {energy:.8g}")
    lines.append("=" * 64)
    return "\n".join(lines)
