"""Minimal SCFT validation tests (AB diblock, 1D) + optional C++ / box scan."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_engine.reporting import format_simulation_scientific_report, interpret_simulation
from polymer_engine.solvers import SCFTSolver, SimulationInput, get_solver, list_solvers
from polymer_engine.solvers.scft.propagator import (
    mde_cpp_available,
    propagate_diblock_1d,
    resolve_propagator_backend,
)
from polymer_engine.solvers.scft.unit_cell import default_length_grid, scan_box_lengths


MDE_CPP_NUMPY_AGREEMENT_TOL = 1.0e-10


def _scft_input(*, chi: float, N: float, f: float = 0.5, **kwargs) -> SimulationInput:
    settings = {
        "n_contour": kwargs.pop("n_contour", 80),
        "mix_parameter": kwargs.pop("mix_parameter", 0.08),
        "tolerance": kwargs.pop("tolerance", 5.0e-4),
        "field_seed_amplitude": kwargs.pop("field_seed_amplitude", 0.1),
        # Keep physics tests on NumPy so results do not depend on optional C++.
        "propagator_backend": kwargs.pop("propagator_backend", "numpy"),
    }
    settings.update(kwargs.pop("settings", {}))
    return SimulationInput(
        name="ab-diblock-scft",
        architecture="diblock",
        volume_fractions=[f, 1.0 - f],
        chi=chi,
        degree_of_polymerization=N,
        n_grid=kwargs.pop("n_grid", 32),
        box_length=kwargs.pop("box_length", 4.0),
        n_iterations=kwargs.pop("n_iterations", 80),
        timestep=0.05,
        random_seed=kwargs.pop("random_seed", 0),
        settings=settings,
    )


class TestSCFTRegistry(unittest.TestCase):
    def test_scft_is_implemented(self) -> None:
        self.assertIn("implemented", list_solvers()["scft"].lower())
        self.assertIsInstance(get_solver("scft"), SCFTSolver)


class TestSCFTPhysicsTrends(unittest.TestCase):
    def test_low_chin_near_homogeneous(self) -> None:
        out = SCFTSolver().solve(_scft_input(chi=0.05, N=100.0, n_iterations=60))
        amp = out.structure["phi_A_amplitude"]
        self.assertTrue(out.success)
        self.assertLess(amp, 0.15)
        self.assertIn("homogeneous", out.morphology.lower())

    def test_high_chin_develops_modulation(self) -> None:
        out = SCFTSolver().solve(
            _scft_input(chi=0.125, N=200.0, n_iterations=100, n_contour=100)
        )
        amp = out.structure["phi_A_amplitude"]
        self.assertTrue(out.success)
        self.assertGreater(amp, 0.05)
        self.assertIn("modulated", out.morphology.lower())
        self.assertIn("free_energy_terms", out.convergence)
        self.assertIn("Q", out.structure)

    def test_high_amplitude_exceeds_low(self) -> None:
        low = SCFTSolver().solve(_scft_input(chi=0.04, N=100.0, n_iterations=50))
        high = SCFTSolver().solve(_scft_input(chi=0.15, N=200.0, n_iterations=100))
        self.assertGreater(
            high.structure["phi_A_amplitude"],
            low.structure["phi_A_amplitude"],
        )


class TestSCFTReporting(unittest.TestCase):
    def test_scientific_report_traceable(self) -> None:
        sim = _scft_input(chi=0.1, N=200.0, n_iterations=60)
        out = SCFTSolver().solve(sim)
        report = format_simulation_scientific_report(out, sim_input=sim)
        self.assertIn("Scientific interpretation", report)
        self.assertIn("Reason:", report)
        self.assertIn("SCFT", report)
        self.assertNotIn("Lamellae predicted", report)
        self.assertNotIn("Gyroid predicted", report)
        interp = interpret_simulation(out, sim_input=sim)
        self.assertFalse(interp.is_toy_field_model)
        self.assertIn("χN", interp.claims[0].reason)


class TestPropagatorBackendResolution(unittest.TestCase):
    def test_numpy_always_resolves(self) -> None:
        self.assertEqual(resolve_propagator_backend("numpy"), "numpy")

    def test_auto_falls_back_when_cpp_missing(self) -> None:
        with mock.patch(
            "polymer_engine.solvers.scft.propagator.mde_cpp_available",
            return_value=False,
        ):
            self.assertEqual(resolve_propagator_backend("auto"), "numpy")

    def test_explicit_cpp_errors_when_unavailable(self) -> None:
        with mock.patch(
            "polymer_engine.solvers.scft.propagator.mde_cpp_available",
            return_value=False,
        ):
            with self.assertRaises(ImportError):
                resolve_propagator_backend("cpp")


class TestUnitCellScan(unittest.TestCase):
    def test_scan_picks_minimum(self) -> None:
        lengths = default_length_grid(3.0, 7.0, 5)

        def fake_F(L: float) -> float:
            return (L - 5.0) ** 2

        scan = scan_box_lengths(fake_F, lengths)
        self.assertAlmostEqual(scan.optimal_length, 5.0)
        self.assertEqual(scan.optimal_free_energy, min(scan.free_energies))

    def test_optimize_box_records_scan(self) -> None:
        out = SCFTSolver().solve(
            _scft_input(
                chi=0.125,
                N=200.0,
                n_iterations=40,
                n_contour=60,
                n_grid=32,
                box_length=5.0,
                settings={
                    "optimize_box": True,
                    "box_lengths": [3.5, 4.5, 5.5, 6.5],
                    "propagator_backend": "numpy",
                },
            )
        )
        self.assertTrue(out.success)
        self.assertTrue(out.method_details["optimize_box"])
        scan = out.structure["box_scan"]
        self.assertEqual(len(scan["lengths"]), 4)
        self.assertEqual(len(scan["energies"]), 4)
        self.assertEqual(out.method_details["box_length_Rg_units"], scan["best_length"])
        self.assertAlmostEqual(min(scan["energies"]), scan["best_energy"])


@unittest.skipUnless(mde_cpp_available(), "SCFT C++ MDE extension not built")
class TestSCFTMdeCppKernel(unittest.TestCase):
    def test_agreement_with_numpy(self) -> None:
        rng = np.random.default_rng(3)
        nx = 32
        w_A = 2.0 + 0.3 * np.cos(2.0 * np.pi * np.arange(nx) / nx) + 0.01 * rng.standard_normal(nx)
        w_B = 1.5 - 0.3 * np.cos(2.0 * np.pi * np.arange(nx) / nx)
        kwargs = dict(f_A=0.5, box_length=4.0, n_contour=40)
        np_res = propagate_diblock_1d(w_A, w_B, backend="numpy", **kwargs)
        cpp_res = propagate_diblock_1d(w_A, w_B, backend="cpp", **kwargs)
        self.assertEqual(cpp_res.backend, "cpp")
        self.assertLessEqual(float(np.max(np.abs(np_res.q - cpp_res.q))), MDE_CPP_NUMPY_AGREEMENT_TOL)
        self.assertLessEqual(
            float(np.max(np.abs(np_res.q_dagger - cpp_res.q_dagger))),
            MDE_CPP_NUMPY_AGREEMENT_TOL,
        )
        self.assertAlmostEqual(np_res.Q, cpp_res.Q, places=10)

    def test_solver_cpp_backend(self) -> None:
        out = SCFTSolver().solve(
            _scft_input(
                chi=0.1,
                N=200.0,
                n_iterations=40,
                n_grid=32,
                propagator_backend="cpp",
            )
        )
        self.assertEqual(out.method_details["propagator_backend"], "cpp")
        self.assertTrue(out.success)


if __name__ == "__main__":
    unittest.main()
