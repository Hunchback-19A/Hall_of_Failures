# Copyright (C) 2026 Disquietude
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""pscf_rpc solver: periodic diblock SCFT via the vendored Minnesota program."""

from __future__ import annotations

from polymer_engine.solvers.base import SimulationInput, SimulationOutput, Solver
from polymer_engine.solvers.pscf_rpc.runner import (
    CELLS,
    CHIN_CONVENTION,
    best_converged,
    run_cells,
)


class PscfRpcSolver(Solver):
    """
    Rank lamellar, hexagonal, gyroid, and BCC cells with pscf_rpc.

    The 1D educational solver remains registered as ``scft``.
    """

    name = "pscf_rpc"

    def solve(self, sim_input: SimulationInput) -> SimulationOutput:
        sim_input.validate()
        chi_n = float(sim_input.chiN)
        assumptions = [
            CHIN_CONVENTION,
            "Initial fields are the vendored PSCF example fields (lam, hex, gyr, bcc).",
            "The reported morphology is the converged cell with the lowest fHelmholtz.",
            "PSCF source is third_party/pscfpp, GPL-3.0-or-later, "
            "copyright 2015-2026 The Regents of the University of Minnesota.",
        ]
        if sim_input.architecture.lower() != "diblock":
            return SimulationOutput(
                solver_name=self.name,
                morphology="unsupported",
                energy=float("nan"),
                chiN=chi_n,
                success=False,
                assumptions=assumptions,
                notes=["pscf_rpc adapter runs AB diblocks only."],
            )
        f_a = float(sim_input.volume_fractions[0])
        settings = sim_input.settings or {}
        requested = settings.get("pscf_cells", list(CELLS))
        cells = [str(name) for name in requested]
        unknown = [name for name in cells if name not in CELLS]
        if unknown or not cells:
            known = ", ".join(CELLS)
            return SimulationOutput(
                solver_name=self.name,
                morphology="unsupported",
                energy=float("nan"),
                chiN=chi_n,
                success=False,
                assumptions=assumptions,
                notes=[f"pscf_cells must be chosen from: {known}."],
            )
        timeout_s = float(settings.get("pscf_timeout_s", 3600.0))
        keep_concentration = bool(settings.get("pscf_keep_concentration", False))
        if keep_concentration:
            assumptions.append(
                "The copied PSCF command writes the monomer concentration after ITERATE. "
                "That file is the field PSCF computed. It is not an atomistic structure."
            )
        error, runs = run_cells(
            f_a,
            chi_n,
            cells,
            timeout_s=timeout_s,
            keep_concentration=keep_concentration,
        )
        structure = {"cells": [_cell_record(run) for run in runs]}
        if error:
            return SimulationOutput(
                solver_name=self.name,
                morphology="unavailable",
                energy=float("nan"),
                chiN=chi_n,
                success=False,
                assumptions=assumptions,
                notes=[error],
                method_details={"upstream": "pscf_rpc", "chi_written": chi_n, "f_A": f_a},
            )
        winner = best_converged(runs)
        notes = [f"{run.cell}: {run.detail}" for run in runs]
        if winner is None or winner.free_energy is None:
            return SimulationOutput(
                solver_name=self.name,
                morphology="unconverged",
                energy=float("nan"),
                chiN=chi_n,
                success=False,
                structure=structure,
                convergence={"converged": False},
                assumptions=assumptions,
                notes=notes,
                method_details={"upstream": "pscf_rpc", "chi_written": chi_n, "f_A": f_a},
            )
        return SimulationOutput(
            solver_name=self.name,
            morphology=winner.morphology,
            energy=float(winner.free_energy),
            chiN=chi_n,
            success=True,
            structure=structure,
            convergence={"converged": True, "cell": winner.cell},
            assumptions=assumptions,
            notes=notes,
            method_details={
                "upstream": "pscf_rpc",
                "chi_written": chi_n,
                "f_A": f_a,
                "free_energy_name": "fHelmholtz",
                "source": "University of Minnesota PSCF (pscf_rpc), not the 1D prototype",
            },
        )


def _cell_record(run) -> dict:
    record = {
        "cell": run.cell,
        "morphology": run.morphology,
        "dimension": run.dimension,
        "fHelmholtz": run.free_energy,
        "converged": run.converged,
        "detail": run.detail,
    }
    if run.concentration is not None:
        record["concentration"] = run.concentration
    return record
