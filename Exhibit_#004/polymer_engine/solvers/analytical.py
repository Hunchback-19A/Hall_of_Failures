"""Analytical solver adapter around the existing simplified physics engine."""

from __future__ import annotations

from polymer_engine.energetics.free_energy import FreeEnergyProxy
from polymer_engine.morphology.morphology_prediction import MorphologyPredictor
from polymer_engine.structure.domain_size import DomainSizeEstimator
from polymer_engine.thermodynamics.flory_huggins import compute_chiN

from .base import SimulationInput, SimulationOutput, Solver


class AnalyticalSolver(Solver):
    """
    Wraps the current rule-based / scaling models behind the Solver interface.

    This is not a field-theoretic calculation.
    """

    name = "analytical"

    def __init__(self) -> None:
        self.morphology = MorphologyPredictor()
        self.energy = FreeEnergyProxy()
        self.domain = DomainSizeEstimator()

    def solve(self, sim_input: SimulationInput) -> SimulationOutput:
        sim_input.validate()
        chin = compute_chiN(sim_input.chi, sim_input.degree_of_polymerization)
        morph = self.morphology.predict(
            f_values=list(sim_input.volume_fractions),
            chiN=chin.chiN,
            segregation_regime=chin.segregation_regime,
            architecture=sim_input.architecture,
        )
        fe = self.energy.evaluate(chin.chiN, morph.f_minor, morph)
        dom = self.domain.estimate(
            N=sim_input.degree_of_polymerization,
            chi=sim_input.chi,
            chiN=chin.chiN,
            morphology=morph.morphology,
            f_minor=morph.f_minor,
        )
        return SimulationOutput(
            solver_name=self.name,
            morphology=morph.morphology,
            energy=fe.score,
            chiN=chin.chiN,
            structure={
                "f_minor": morph.f_minor,
                "domain_spacing_nm": dom.domain_spacing_nm,
                "radius_of_gyration_nm": dom.radius_of_gyration_nm,
                "domain_size_model": dom.model,
            },
            convergence={
                "status": "n/a (closed-form / rule-based evaluation)",
                "iterations": 0,
            },
            method_details={
                "method": "simplified analytical morphology map + free-energy proxy",
                "engine": "polymer_engine morphology/energetics/structure modules",
                "grid_size": "n/a",
                "timestep": "n/a",
                "random_seed": "n/a",
            },
            assumptions=[
                "Uses the educational Phase 1–4 analytical models.",
                "Not a numerical PDE / SCFT solution.",
            ],
            notes=[
                "AnalyticalSolver exists so numerical solvers can share the same I/O contract.",
            ],
            success=True,
        )
