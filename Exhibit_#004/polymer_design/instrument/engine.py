# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Run validated design requests through the existing solvers."""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from typing import Any, Callable

from polymer_engine.solvers import SimulationInput, get_solver
from polymer_engine.solvers.pscf_rpc.runner import CHIN_CONVENTION

from polymer_design.instrument.provenance import pscf_commit, software_version
from polymer_design.instrument.schema import EXAMPLE_CELLS, SCHEMA, DesignRequest

RESULT_SCHEMA = "polymer_design.result.v1"
Progress = Callable[[str], None]


def execute_request(
    request: DesignRequest,
    *,
    prior: dict[str, dict[str, Any]] | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Evaluate every candidate. Failures stay in the result; they are not retried."""
    started = _now()
    report = progress or _stderr
    known = dict(prior or {})
    records: list[dict[str, Any]] = []
    total = len(request.candidates)
    for spec in request.candidates:
        previous = known.get(spec.id)
        if previous is None:
            continue
        if previous.get("input") != _input_record(request, spec):
            raise ValueError(
                f"{spec.id} is already recorded with different parameters. "
                "Resume left that record unchanged and did not recalculate it."
            )
    for index, spec in enumerate(request.candidates, start=1):
        if spec.id in known:
            records.append(known[spec.id])
            report(f"[{index}/{total}] {spec.id} skipped (already recorded)")
            continue
        report(f"[{index}/{total}] {spec.id} {request.solver}")
        records.append(_run_one(request, spec))
    finished = _now()
    _attach_batch_ranking(records)
    failures = [item for item in records if item["status"] != "converged"]
    status = "completed_with_failures" if failures else "completed"
    return {
        "schema": RESULT_SCHEMA,
        "request_schema": SCHEMA,
        "client": request.client,
        "request_id": request.request_id,
        "metadata": request.metadata,
        "solver": request.solver,
        "software_version": software_version(),
        "pscf_commit": pscf_commit() if request.solver == "pscf_rpc" else None,
        "pscf_upstream": "https://github.com/dmorse/pscfpp" if request.solver == "pscf_rpc" else None,
        "started_at": started,
        "finished_at": finished,
        "status": status,
        "assumptions": _assumptions(request),
        "candidates": records,
        "ranking": _ranking(records),
    }


def _run_one(request: DesignRequest, spec) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    if request.solver == "pscf_rpc":
        settings["pscf_cells"] = list(request.cells)
        settings["pscf_timeout_s"] = request.timeout_s
        settings["pscf_keep_concentration"] = request.keep_concentration
    sim = SimulationInput(
        name=spec.name,
        architecture=spec.architecture,
        volume_fractions=list(spec.volume_fractions),
        chi=spec.chi,
        degree_of_polymerization=spec.degree_of_polymerization,
        settings=settings,
    )
    base = _candidate_header(request, spec)
    try:
        output = get_solver(request.solver).solve(sim)
    except Exception as exc:
        base.update(
            {
                "status": "failed",
                "success": False,
                "preferred_morphology": None,
                "free_energy": None,
                "free_energy_name": None,
                "morphologies": [],
                "warnings": [f"{type(exc).__name__}: {exc}"],
                "diagnostics": {},
                "interpretation": _interpret(None, request.solver, failed=True),
                "concentration_fields": [],
                "visualization": _unavailable_visualization(),
            }
        )
        return base
    fields = _take_concentration(output)
    morphologies = _morphologies(request, output)
    converged = [item for item in morphologies if item["converged"] and item["free_energy"] is not None]
    if request.solver == "pscf_rpc":
        winner = min(converged, key=lambda item: item["free_energy"]) if converged else None
        status = "converged" if winner else ("unavailable" if not morphologies else "unconverged")
        energy = None if winner is None else winner["free_energy"]
        preferred = None if winner is None else winner["morphology"]
        energy_name = "fHelmholtz" if winner else None
    else:
        status = "converged" if output.success else "failed"
        energy = output.energy
        preferred = output.morphology if output.success else None
        energy_name = "solver_energy" if output.success else None
    warnings = [str(item) for item in output.notes]
    if request.solver == "pscf_rpc" and any(not item["converged"] for item in morphologies):
        skipped = [str(item["cell"]) for item in morphologies if not item["converged"]]
        warnings.append("Unconverged cells were not ranked: " + ", ".join(skipped))
    base.update(
        {
            "status": status,
            "success": status == "converged",
            "preferred_morphology": preferred,
            "free_energy": energy,
            "free_energy_name": energy_name,
            "morphologies": morphologies,
            "warnings": warnings,
            "diagnostics": {
                "method": output.method_details,
                "convergence": output.convergence,
                "structure": output.structure,
                "solver_assumptions": list(output.assumptions),
            },
            "interpretation": _interpret(preferred, request.solver, failed=status != "converged"),
            "concentration_fields": fields,
            "visualization": _visualization_block(fields),
        }
    )
    return base


def _take_concentration(output) -> list[dict[str, Any]]:
    """Lift PSCF concentration grids out of the diagnostics copy."""
    fields = []
    for cell in output.structure.get("cells", []):
        grid = cell.pop("concentration", None)
        if grid is not None:
            fields.append({"cell": cell.get("cell"), "morphology": cell.get("morphology"), "field": grid})
    return fields


def _unavailable_visualization() -> dict[str, Any]:
    return {
        "available": False,
        "representation": None,
        "density_source": "unavailable",
        "formats": [],
        "fields": [],
        "reason": (
            "This calculation did not keep a PSCF concentration grid. "
            "Free energies were recorded. A picture was not invented from the label."
        ),
        "export_command": "python -m polymer_design visualize RESULT.json --format avogadro",
    }


def _visualization_block(fields: list[dict[str, Any]]) -> dict[str, Any]:
    if not fields:
        return _unavailable_visualization()
    return {
        "available": True,
        "representation": "monomer_concentration",
        "density_source": "pscf_calculated",
        "formats": ["cjson"],
        "fields": [],
        "reason": (
            "Monomer concentrations from PSCF WRITE_C_RGRID. "
            "Passing them to visualize writes an Avogadro CJSON volume, not an atomistic file."
        ),
        "export_command": "python -m polymer_design visualize RESULT.json --format avogadro",
    }


def _input_record(request: DesignRequest, spec) -> dict[str, Any]:
    return {
        "architecture": spec.architecture,
        "volume_fractions": list(spec.volume_fractions),
        "chi": spec.chi,
        "degree_of_polymerization": spec.degree_of_polymerization,
        "chiN": spec.chiN,
        "cells": list(request.cells),
    }


def _candidate_header(request: DesignRequest, spec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "name": spec.name,
        "client": request.client,
        "input": _input_record(request, spec),
        "solver": request.solver,
        "software_version": software_version(),
        "pscf_commit": pscf_commit() if request.solver == "pscf_rpc" else None,
    }


def _morphologies(request: DesignRequest, output) -> list[dict[str, Any]]:
    if request.solver != "pscf_rpc":
        return [
            {
                "representation": "solver_morphology_v1",
                "cell": None,
                "morphology": output.morphology,
                "dimension": None,
                "lattice": None,
                "space_group": None,
                "converged": bool(output.success),
                "free_energy": output.energy,
                "free_energy_name": "solver_energy",
                "relative_free_energy": 0.0 if output.success else None,
                "detail": output.convergence,
            }
        ]
    rows = []
    for cell in output.structure.get("cells", []):
        key = str(cell.get("cell"))
        identity = EXAMPLE_CELLS.get(key, {})
        reported = _finite(cell.get("fHelmholtz"))
        converged = bool(cell.get("converged")) and reported is not None
        rows.append(
            {
                "representation": "pscf_example_cell_v1",
                "cell": key,
                "morphology": cell.get("morphology", identity.get("morphology", key)),
                "dimension": cell.get("dimension", identity.get("dimension")),
                "lattice": identity.get("lattice"),
                "space_group": identity.get("space_group"),
                "converged": converged,
                "reported_free_energy": reported,
                "free_energy": reported if converged else None,
                "free_energy_name": "fHelmholtz",
                "relative_free_energy": None,
                "detail": cell.get("detail", ""),
            }
        )
    usable = [item["free_energy"] for item in rows if item["converged"] and item["free_energy"] is not None]
    if usable:
        lowest = min(usable)
        for item in rows:
            if item["converged"] and item["free_energy"] is not None:
                item["relative_free_energy"] = item["free_energy"] - lowest
    return rows


def _attach_batch_ranking(records: list[dict[str, Any]]) -> None:
    usable = [
        item["free_energy"]
        for item in records
        if item["status"] == "converged" and item["free_energy"] is not None
    ]
    lowest = min(usable) if usable else None
    for item in records:
        if lowest is None or item["status"] != "converged" or item["free_energy"] is None:
            item["relative_to_batch_best"] = None
            item["batch_rank"] = None
        else:
            item["relative_to_batch_best"] = item["free_energy"] - lowest


def _ranking(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = [
        item
        for item in records
        if item["status"] == "converged" and item["free_energy"] is not None
    ]
    ranked.sort(key=lambda item: (item["free_energy"], item["id"]))
    table = []
    for place, item in enumerate(ranked, start=1):
        item["batch_rank"] = place
        table.append(
            {
                "rank": place,
                "id": item["id"],
                "morphology": item["preferred_morphology"],
                "free_energy": item["free_energy"],
                "free_energy_name": item["free_energy_name"],
                "relative_free_energy": item["relative_to_batch_best"],
            }
        )
    return table


def _assumptions(request: DesignRequest) -> list[str]:
    lines = [
        "Human and AI requests use the same validation and the same solver.",
        "client is provenance only. It does not change the calculation.",
        "No parameter was rewritten to force a result.",
    ]
    if request.solver == "pscf_rpc":
        lines.append(CHIN_CONVENTION)
        if request.keep_concentration:
            lines.append(
                "Monomer concentrations were written with WRITE_C_RGRID after ITERATE. "
                "That does not change the free energy. A missing grid is not filled in."
            )
        lines.append(
            "Only the requested example cells are compared. "
            "A lower fHelmholtz is preferred only among cells that converged."
        )
        lines.append(
            "Space-group names in the result are the vendored example identities, "
            "not a symmetry calculated for this composition."
        )
    elif request.solver == "analytical":
        lines.append(
            "The analytical solver is an educational morphology map and a free-energy proxy. "
            "It is not a periodic SCFT ranking."
        )
    elif request.solver == "scft":
        lines.append(
            "The 1D SCFT solver is the local prototype, not the periodic PSCF calculation."
        )
    return lines


def _interpret(morphology: str | None, solver: str, *, failed: bool) -> dict[str, str]:
    limitations = (
        "This is a calculation inside the selected model. "
        "It does not include dispersity, processing, solvent history, defects, "
        "or a measured temperature. Experimental validation is required."
    )
    if failed or not morphology:
        return {
            "calculated": "No converged free energy is available for this candidate.",
            "prediction": (
                "No preferred morphology is assigned. "
                "An unconverged or failed calculation is not treated as a thermodynamic result."
            ),
            "experimental": (
                "No experimental implication is drawn. "
                "A missing calculation is not evidence for or against a morphology."
            ),
            "limitations": limitations,
        }
    if solver == "pscf_rpc":
        return {
            "calculated": (
                f"Among the tested morphologies that converged, {morphology} "
                "has the lowest fHelmholtz."
            ),
            "prediction": (
                f"Within this PSCF model and among the tested morphologies, "
                f"the calculation predicts {morphology}. "
                "That is a model prediction, not a statement that the morphology will form."
            ),
            "experimental": (
                f"{morphology.capitalize()} is a candidate for experimental investigation "
                "if the composition, segregation strength, and processing are comparable "
                "to this calculation. The model does not account for kinetic trapping, "
                "molecular-weight distribution, solvent history, temperature history, or defects. "
                "The prediction requires experimental validation."
            ),
            "limitations": limitations,
        }
    return {
        "calculated": (
            f"The {solver} solver returned {morphology} with its own energy proxy."
        ),
        "prediction": (
            f"Within that model, the reported morphology is {morphology}. "
            "This is not a periodic SCFT ranking of lamellae, cylinders, gyroid, and spheres."
        ),
        "experimental": (
            "The result is a qualitative educational indication only. "
            "It requires experimental validation and should not be read as a processing recommendation."
        ),
        "limitations": limitations,
    }


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _stderr(message: str) -> None:
    print(message, file=sys.stderr)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
