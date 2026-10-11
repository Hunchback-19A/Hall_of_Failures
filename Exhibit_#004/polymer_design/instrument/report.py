# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Human-readable calculation record."""

from __future__ import annotations

from typing import Any


def format_report(result: dict[str, Any]) -> str:
    lines = [
        "Polymer design calculation",
        "",
        f"Request: {result['request_id']}",
        f"Client: {result['client']}",
        f"Solver: {result['solver']}",
        f"Software version: {result['software_version']}",
        f"Started: {result['started_at']}",
        f"Finished: {result['finished_at']}",
        f"Status: {result['status']}",
    ]
    if result.get("pscf_commit"):
        lines.append(f"PSCF commit: {result['pscf_commit']}")
        lines.append(f"PSCF upstream: {result['pscf_upstream']}")
    lines.extend(["", "Assumptions"])
    lines.extend(f"- {item}" for item in result["assumptions"])
    for candidate in result["candidates"]:
        lines.extend(["", f"Candidate {candidate['id']}"])
        incoming = candidate["input"]
        lines.append(f"  Architecture: {incoming['architecture']}")
        lines.append(
            "  Volume fractions: "
            + ", ".join(f"{value:.6g}" for value in incoming["volume_fractions"])
        )
        lines.append(f"  chi: {incoming['chi']:.6g}")
        lines.append(f"  N: {incoming['degree_of_polymerization']:.6g}")
        lines.append(f"  chiN: {incoming['chiN']:.6g}")
        if incoming["cells"]:
            lines.append("  Cells: " + ", ".join(incoming["cells"]))
        lines.append(f"  Candidate status: {candidate['status']}")
        if candidate["preferred_morphology"]:
            lines.append(f"  Preferred morphology: {candidate['preferred_morphology']}")
        energy = candidate["free_energy"]
        if energy is not None:
            lines.append(
                f"  Free energy ({candidate['free_energy_name']}): {energy:.8g}"
            )
        if candidate["batch_rank"] is not None:
            lines.append(f"  Batch rank: {candidate['batch_rank']}")
            lines.append(
                f"  Relative to batch best: {candidate['relative_to_batch_best']:.8g}"
            )
        if candidate["morphologies"]:
            lines.append("  Morphologies:")
            for item in candidate["morphologies"]:
                flag = "converged" if item["converged"] else "not ranked"
                energy_text = "n/a" if item["free_energy"] is None else f"{item['free_energy']:.8g}"
                relative = item["relative_free_energy"]
                relative_text = "n/a" if relative is None else f"{relative:.8g}"
                lines.append(
                    f"    - {item['morphology']}: {flag}, "
                    f"free energy {energy_text}, relative {relative_text}"
                )
        reading = candidate["interpretation"]
        lines.extend(
            [
                "  Calculated result:",
                f"    {reading['calculated']}",
                "  Model prediction:",
                f"    {reading['prediction']}",
                "  Experimental interpretation:",
                f"    {reading['experimental']}",
                "  Limitations:",
                f"    {reading['limitations']}",
            ]
        )
        for warning in candidate["warnings"]:
            lines.append(f"  Warning: {warning}")
    lines.extend(["", "Ranking (converged candidates only)"])
    if not result["ranking"]:
        lines.append("  None. No converged free energy was available to rank.")
    for row in result["ranking"]:
        lines.append(
            f"  {row['rank']}. {row['id']}: {row['morphology']}, "
            f"{row['free_energy_name']} {row['free_energy']:.8g}, "
            f"relative {row['relative_free_energy']:.8g}"
        )
    lines.extend(
        [
            "",
            "The ranking compares numbers from this request only.",
            "It does not claim that a morphology will form in experiment.",
            "",
            "Normal termination",
        ]
    )
    return "\n".join(lines) + "\n"
