"""Tests for scientific interpretation / reporting layer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.polymer import Block, Polymer
from polymer_engine.reporting import (
    format_prediction_scientific_report,
    format_simulation_scientific_report,
    interpret_prediction,
    interpret_simulation,
)
from polymer_engine.solvers import PhaseFieldSolver, SimulationInput
from polymer_engine.thermodynamics.flory_huggins import SYMMETRIC_DIBLOCK_ODT_CHIN


class TestTraceableInterpretation(unittest.TestCase):
    def test_above_odt_has_reason_with_chin(self) -> None:
        pred = SimplifiedPhysicsEvaluator().evaluate(
            Polymer(
                name="PS-b-PI",
                architecture="diblock",
                blocks=[Block("styrene", 0.35), Block("isoprene", 0.65)],
                chi=0.09,
                degree_of_polymerization=150,
            )
        )
        interp = interpret_prediction(pred)
        text = "\n".join(
            [c.interpretation + "\n" + c.reason for c in interp.claims]
        )
        self.assertIn("Segregation is favored", text)
        self.assertIn(f"χN = {pred.chiN:.4g}", text)
        self.assertIn(f"{SYMMETRIC_DIBLOCK_ODT_CHIN}", text)

    def test_below_odt_mixed(self) -> None:
        pred = SimplifiedPhysicsEvaluator().evaluate(
            Polymer(
                name="weak",
                architecture="diblock",
                blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
                chi=0.04,
                degree_of_polymerization=100,
            )
        )
        claim0 = interpret_prediction(pred).claims[0]
        self.assertIn("disordered/mixed", claim0.interpretation.lower())
        self.assertIn("below", claim0.reason.lower())


class TestScientificReports(unittest.TestCase):
    def test_prediction_report_sections_and_raw_params(self) -> None:
        pred = SimplifiedPhysicsEvaluator().evaluate(
            Polymer(
                name="PS-b-PMMA",
                architecture="diblock",
                blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
                chi=0.05,
                degree_of_polymerization=300,
            )
        )
        report = format_prediction_scientific_report(pred, show_calculations=False)
        self.assertIn("Scientific interpretation", report)
        self.assertIn("Numerical details", report)
        self.assertIn("Assumptions and limitations", report)
        self.assertIn("Interpretation:", report)
        self.assertIn("Reason:", report)
        self.assertIn("χ = 0.05", report)
        self.assertIn("N = 300", report)
        self.assertIn(f"χN = {pred.chiN:.4g}", report)
        # Numerical values unchanged vs evaluator
        self.assertAlmostEqual(pred.chiN, 15.0)
        self.assertEqual(pred.morphology, "lamellae")

    def test_toy_phase_field_never_claims_classical_morphology(self) -> None:
        sim_input = SimulationInput(
            name="toy-run",
            architecture="diblock",
            volume_fractions=[0.5, 0.5],
            chi=0.08,
            degree_of_polymerization=200,
            n_grid=32,
            n_iterations=200,
            timestep=5.0e-4,
            random_seed=0,
            settings={"backend": "numpy"},
        )
        out = PhaseFieldSolver().solve(sim_input)
        report = format_simulation_scientific_report(out, sim_input=sim_input)
        self.assertIn("toy field", report.lower())
        self.assertIn("Periodic composition modulation", report)
        banned = ["Lamellae predicted", "Cylinders predicted", "Gyroid predicted"]
        for phrase in banned:
            self.assertNotIn(phrase, report)
        # Should not present classical morphology as the interpretation conclusion
        interp = interpret_simulation(out, sim_input=sim_input)
        self.assertTrue(interp.is_toy_field_model)
        self.assertNotIn("lamellae", interp.structure_indication.interpretation.lower())
        self.assertNotIn("cylinders", interp.structure_indication.interpretation.lower())
        self.assertNotIn("gyroid", interp.structure_indication.interpretation.lower())


if __name__ == "__main__":
    unittest.main()
