"""Phase 7 tests: solver interfaces and toy phase-field prototype."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_engine.solvers import (
    AnalyticalSolver,
    PhaseFieldSolver,
    SimulationInput,
    get_solver,
    list_solvers,
)
from polymer_engine.solvers.monte_carlo import MonteCarloSolver
import numpy as np


def _base_input(**kwargs) -> SimulationInput:
    data = dict(
        name="test",
        architecture="diblock",
        volume_fractions=[0.5, 0.5],
        chi=0.08,
        degree_of_polymerization=200.0,
        n_grid=32,
        timestep=1.0e-3,
        n_iterations=400,
        random_seed=1,
        box_length=1.0,
    )
    data.update(kwargs)
    return SimulationInput(**data)


class TestRegistry(unittest.TestCase):
    def test_list_and_get(self) -> None:
        status = list_solvers()
        self.assertIn("analytical", status)
        self.assertIn("phase_field", status)
        self.assertIn("placeholder", status["monte_carlo"].lower())
        self.assertIn("implemented", status["scft"].lower())
        self.assertIsInstance(get_solver("analytical"), AnalyticalSolver)
        self.assertIsInstance(get_solver("phase_field"), PhaseFieldSolver)


class TestPlaceholders(unittest.TestCase):
    def test_mc_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            MonteCarloSolver().solve(_base_input())


class TestAnalyticalSolver(unittest.TestCase):
    def test_output_schema(self) -> None:
        out = AnalyticalSolver().solve(_base_input())
        self.assertEqual(out.solver_name, "analytical")
        self.assertIn("method", out.method_details)
        self.assertTrue(out.assumptions)
        self.assertAlmostEqual(out.chiN, 16.0)


class TestPhaseFieldSolver(unittest.TestCase):
    def test_reproducibility_with_seed(self) -> None:
        solver = PhaseFieldSolver()
        a = solver.solve(_base_input(random_seed=7, n_iterations=300, n_grid=32, timestep=5.0e-4))
        b = solver.solve(_base_input(random_seed=7, n_iterations=300, n_grid=32, timestep=5.0e-4))
        self.assertTrue(np.allclose(a.structure["order_parameter_phi"], b.structure["order_parameter_phi"]))
        self.assertEqual(a.method_details["random_seed"], 7)
        self.assertEqual(a.method_details["grid_size"], 32)
        self.assertEqual(a.method_details["timestep"], 5.0e-4)
        self.assertEqual(a.method_details["n_iterations"], 300)
        self.assertTrue(a.success)

    def test_toy_disclaimer_present(self) -> None:
        out = PhaseFieldSolver().solve(
            _base_input(chi=0.2, degree_of_polymerization=400, timestep=5.0e-4)
        )
        blob = " ".join(out.notes + out.assumptions).lower()
        self.assertIn("toy", blob)
        self.assertIn("not a quantitative", " ".join(out.notes).lower())
        self.assertIn("energy_samples", out.convergence)
        self.assertIn("equation", out.method_details)
        self.assertTrue(out.morphology.startswith("toy-"))

    def test_low_vs_high_segregation_amplitude(self) -> None:
        solver = PhaseFieldSolver()
        weak = solver.solve(
            _base_input(
                chi=0.01,
                degree_of_polymerization=50,
                n_iterations=800,
                timestep=5.0e-4,
                random_seed=0,
            )
        )
        strong = solver.solve(
            _base_input(
                chi=0.25,
                degree_of_polymerization=500,
                n_iterations=800,
                timestep=5.0e-4,
                random_seed=0,
            )
        )
        self.assertTrue(np.isfinite(weak.structure["phi_amplitude"]))
        self.assertTrue(np.isfinite(strong.structure["phi_amplitude"]))
        self.assertGreaterEqual(
            strong.structure["phi_amplitude"] + 1e-9,
            weak.structure["phi_amplitude"],
        )


if __name__ == "__main__":
    unittest.main()
