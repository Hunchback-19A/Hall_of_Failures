"""
Main SCFT self-consistency loop for AB diblocks (1D periodic prototype).

Workflow:
  fields → propagator → density → field update → free energy → convergence
  optional: scan box length L to reduce F (1D unit-cell refinement only)

Educational core stays 1D AB. ABC / 2D–3D architectures are extension points
for future field users — not implemented here.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polymer_engine.solvers.base import SimulationInput, SimulationOutput, Solver

from .convergence import ConvergenceMonitor
from .density import densities_from_propagators
from .fields import FieldState, initialize_fields
from .free_energy import scft_free_energy
from .models import DiblockSCFTSpec
from .propagator import propagate_diblock_1d
from .unit_cell import default_length_grid, scan_box_lengths


def _update_fields(
    fields: FieldState,
    density,
    *,
    chiN: float,
    mix: float,
    pressure_mix: float,
) -> FieldState:
    """
    Picard / simple mixing update with pressure-like field for incompressibility.

        w_A ← (1-λ) w_A + λ (χN φ_B + ξ)
        w_B ← (1-λ) w_B + λ (χN φ_A + ξ)
        ξ   ← ξ + λ_p (φ_A + φ_B - 1)
    """
    xi = fields.pressure
    target_A = chiN * density.phi_B + xi
    target_B = chiN * density.phi_A + xi
    w_A = (1.0 - mix) * fields.w_A + mix * target_A
    w_B = (1.0 - mix) * fields.w_B + mix * target_B
    xi_new = xi + pressure_mix * (density.phi_A + density.phi_B - 1.0)
    # Gauge: subtract spatial mean of (w_A+w_B)/2 to reduce drift
    mean = 0.5 * (np.mean(w_A) + np.mean(w_B))
    w_A = w_A - mean
    w_B = w_B - mean
    xi_new = xi_new - np.mean(xi_new)
    return FieldState(w_A=w_A, w_B=w_B, pressure=xi_new)


class SCFTSolver(Solver):
    """
    Minimal 1D mean-field SCFT for AB Gaussian diblocks.

    Not a commercial SCFT package. Designed as an extensible research prototype.
    """

    name = "scft"

    def solve(self, sim_input: SimulationInput) -> SimulationOutput:
        sim_input.validate()
        f_A = float(sim_input.volume_fractions[0])
        spec = DiblockSCFTSpec(
            f_A=f_A, chiN=float(sim_input.chiN), architecture=sim_input.architecture
        )
        spec.validate()

        n_grid = int(sim_input.n_grid)
        if n_grid < 16:
            raise ValueError("SCFT n_grid must be >= 16")

        settings = sim_input.settings or {}
        box0 = float(sim_input.box_length)
        n_contour = int(settings.get("n_contour", 100))
        mix = float(
            settings.get(
                "mix_parameter",
                sim_input.timestep if sim_input.timestep < 1 else 0.05,
            )
        )
        if "mix_parameter" not in settings:
            mix = float(settings.get("lambda", 0.05))
        pressure_mix = float(settings.get("pressure_mix", mix))
        tol = float(settings.get("tolerance", 1.0e-4))
        max_iter = int(sim_input.n_iterations)
        seed_amp = float(settings.get("field_seed_amplitude", 0.08))
        # NumPy is the default install path; "auto" uses optional C++ when built.
        backend = str(settings.get("propagator_backend", "auto"))
        optimize_box = bool(settings.get("optimize_box", False))

        run_kwargs: dict[str, Any] = dict(
            sim_input=sim_input,
            spec=spec,
            n_grid=n_grid,
            n_contour=n_contour,
            mix=mix,
            pressure_mix=pressure_mix,
            tol=tol,
            max_iter=max_iter,
            seed_amp=seed_amp,
            backend=backend,
        )

        if optimize_box:
            lengths = settings.get("box_lengths")
            if lengths is None:
                lengths = default_length_grid(
                    float(settings.get("box_L_min", max(2.0, 0.6 * box0))),
                    float(settings.get("box_L_max", max(box0 * 1.8, 8.0))),
                    int(settings.get("box_n_points", 7)),
                )
            else:
                lengths = [float(x) for x in lengths]

            def _energy_at(L: float) -> float:
                out = self._run_fixed_box(box=float(L), **run_kwargs)
                return float(out.energy)

            scan = scan_box_lengths(_energy_at, lengths)
            result = self._run_fixed_box(box=float(scan.optimal_length), **run_kwargs)
            result.structure = dict(result.structure)
            result.structure["box_scan"] = {
                "lengths": list(scan.candidate_lengths),
                "energies": list(scan.free_energies),
                "best_length": scan.optimal_length,
                "best_energy": scan.optimal_free_energy,
                "method": scan.method,
                "notes": list(scan.notes),
            }
            result.method_details = dict(result.method_details)
            result.method_details["optimize_box"] = True
            result.method_details["box_length_Rg_units"] = scan.optimal_length
            return result

        return self._run_fixed_box(box=box0, **run_kwargs)

    def _run_fixed_box(
        self,
        *,
        sim_input: SimulationInput,
        spec: DiblockSCFTSpec,
        box: float,
        n_grid: int,
        n_contour: int,
        mix: float,
        pressure_mix: float,
        tol: float,
        max_iter: int,
        seed_amp: float,
        backend: str,
    ) -> SimulationOutput:
        fields = initialize_fields(
            n_grid,
            box_length=box,
            chiN=spec.chiN,
            f_A=spec.f_A,
            amplitude=seed_amp,
            seed=int(sim_input.random_seed),
        )
        monitor = ConvergenceMonitor(tolerance=tol, max_iterations=max_iter)

        fe_terms = None
        density = None
        prop = None
        conv_state = None
        residual_history: list[float] = []

        for it in range(1, max_iter + 1):
            prop = propagate_diblock_1d(
                fields.w_A,
                fields.w_B,
                f_A=spec.f_A,
                box_length=box,
                n_contour=n_contour,
                backend=backend,
            )
            density = densities_from_propagators(prop, f_A=spec.f_A, box_length=box)
            fe_terms = scft_free_energy(
                fields, density, Q=prop.Q, chiN=spec.chiN, box_length=box
            )
            conv_state = monitor.update(it, fields, density, spec.chiN, fe_terms.total)
            residual_history.append(conv_state.residual)

            if monitor.is_converged(conv_state):
                break

            fields = _update_fields(
                fields,
                density,
                chiN=spec.chiN,
                mix=mix,
                pressure_mix=pressure_mix,
            )

        assert (
            density is not None
            and fe_terms is not None
            and prop is not None
            and conv_state is not None
        )

        amp = float(np.max(density.phi_A) - np.min(density.phi_A))
        if amp < 0.02:
            morph = "scft-homogeneous (weak density modulation)"
        else:
            morph = "scft-modulated (1D density wave)"

        x = (np.arange(n_grid) * (box / n_grid)).tolist()
        return SimulationOutput(
            solver_name=self.name,
            morphology=morph,
            energy=fe_terms.total,
            chiN=spec.chiN,
            structure={
                "x": x,
                "phi_A": density.phi_A.tolist(),
                "phi_B": density.phi_B.tolist(),
                "w_A": fields.w_A.tolist(),
                "w_B": fields.w_B.tolist(),
                "phi_A_min": float(np.min(density.phi_A)),
                "phi_A_max": float(np.max(density.phi_A)),
                "phi_A_amplitude": amp,
                "f_A": spec.f_A,
                "f_B": spec.f_B,
                "Q": prop.Q,
                "incompressibility_error": density.incompressibility_error,
            },
            convergence={
                "iterations": conv_state.iteration,
                "residual": conv_state.residual,
                "tolerance": tol,
                "converged": monitor.is_converged(conv_state),
                "residual_history": residual_history,
                "incompressibility_error": density.incompressibility_error,
                "free_energy_terms": {
                    "total": fe_terms.total,
                    "minus_ln_Q": fe_terms.minus_ln_Q,
                    "interaction": fe_terms.interaction,
                    "field": fe_terms.field,
                    "formula": fe_terms.formula,
                },
            },
            method_details={
                "method": "1D real-space/spectral mean-field SCFT (AB Gaussian diblock)",
                "chain_model": "Gaussian chain modified diffusion equation",
                "interaction": "mean-field Flory–Huggins χN",
                "boundary_conditions": "periodic 1D",
                "propagator": "Strang splitting + Fourier Laplacian",
                "propagator_backend": prop.backend,
                "grid_size": n_grid,
                "box_length_Rg_units": box,
                "optimize_box": False,
                "n_contour": n_contour,
                "mix_parameter": mix,
                "pressure_mix": pressure_mix,
                "tolerance": tol,
                "max_iterations": max_iter,
                "random_seed": sim_input.random_seed,
                "extension_points": (
                    "Future field users: ABC/multiblock models, 2D/3D unit cells, "
                    "full morphology libraries. Educational core stays 1D AB."
                ),
            },
            assumptions=[
                "Gaussian chain statistics (continuous Edwards Hamiltonian).",
                "Mean-field SCFT (fluctuation corrections neglected).",
                "Incompressible AB melt; single χN parameter.",
                "One-dimensional periodic cell (lamellar-like density waves only).",
                "Lengths in units of R_g = a sqrt(N/6); contour s ∈ [0,1].",
            ],
            notes=[
                "Educational/research SCFT prototype — not a quantitative experimental predictor.",
                "Density modulation indicates microphase segregation tendency; classical "
                "3D morphologies (gyroid, cylinders, BCC) are outside this 1D model.",
                "Optional C++ MDE kernel accelerates the propagator; NumPy remains the default path.",
                "Optional optimize_box scans 1D cell length L to reduce free energy "
                "(not a 2D/3D cell suite).",
            ],
            success=bool(np.isfinite(fe_terms.total)),
        )
