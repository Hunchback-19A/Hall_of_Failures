"""Phase 8 tests: optional C++ phase-field kernel vs NumPy fallback."""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_engine.solvers.phase_field import (
    CPP_NUMPY_AGREEMENT_TOL,
    PhaseFieldSolver,
    cpp_extension_available,
    evolve_cpp,
    evolve_numpy,
    resolve_backend,
)
from polymer_engine.solvers import SimulationInput


def _phi0(n: int = 64, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    phi = 0.0 + 0.01 * rng.standard_normal(n)
    return np.clip(phi, -1.5, 1.5)


class TestBackendResolution(unittest.TestCase):
    def test_numpy_always_resolves(self) -> None:
        self.assertEqual(resolve_backend("numpy"), "numpy")

    def test_auto_falls_back_when_cpp_missing(self) -> None:
        with mock.patch(
            "polymer_engine.solvers.phase_field.cpp_extension_available",
            return_value=False,
        ):
            self.assertEqual(resolve_backend("auto"), "numpy")

    def test_explicit_cpp_errors_when_unavailable(self) -> None:
        with mock.patch(
            "polymer_engine.solvers.phase_field.cpp_extension_available",
            return_value=False,
        ):
            with self.assertRaises(ImportError):
                resolve_backend("cpp")


class TestNumpyFallbackSolver(unittest.TestCase):
    def test_forced_numpy_backend(self) -> None:
        out = PhaseFieldSolver().solve(
            SimulationInput(
                chi=0.1,
                degree_of_polymerization=200,
                n_grid=32,
                n_iterations=200,
                timestep=5.0e-4,
                random_seed=3,
                settings={"backend": "numpy"},
            )
        )
        self.assertEqual(out.method_details["backend"], "numpy")
        self.assertTrue(out.success)
        self.assertIn("NumPy", out.method_details["time_integrator"])


@unittest.skipUnless(cpp_extension_available(), "C++ extension not built")
class TestCppKernelAvailable(unittest.TestCase):
    def test_agreement_with_numpy(self) -> None:
        phi0 = _phi0(64, seed=11)
        kwargs = dict(dx=1.0 / 64, dt=5.0e-4, n_steps=400, eps2=4.0e-3, mobility=1.0, alpha=0.15)
        phi_np, e_np, _ = evolve_numpy(phi0, **kwargs)
        phi_cpp, e_cpp, _ = evolve_cpp(phi0, **kwargs)
        max_abs = float(np.max(np.abs(phi_np - phi_cpp)))
        self.assertLessEqual(max_abs, CPP_NUMPY_AGREEMENT_TOL)
        self.assertTrue(np.allclose(e_np, e_cpp, atol=1.0e-9, rtol=1.0e-9))

    def test_solver_cpp_backend(self) -> None:
        out = PhaseFieldSolver().solve(
            SimulationInput(
                chi=0.1,
                degree_of_polymerization=300,
                n_grid=64,
                n_iterations=500,
                timestep=5.0e-4,
                random_seed=1,
                settings={"backend": "cpp"},
            )
        )
        self.assertEqual(out.method_details["backend"], "cpp")
        self.assertTrue(out.success)

    def test_benchmark_comparison(self) -> None:
        """Report timing; C++ need not always win at tiny educational sizes."""
        phi0 = _phi0(128, seed=0)
        kwargs = dict(dx=1.0 / 128, dt=5.0e-4, n_steps=3000, eps2=4.0e-3, mobility=1.0, alpha=0.15)

        t0 = time.perf_counter()
        evolve_numpy(phi0, **kwargs)
        t_np = time.perf_counter() - t0

        t0 = time.perf_counter()
        evolve_cpp(phi0, **kwargs)
        t_cpp = time.perf_counter() - t0

        # Keep as an assertion that both completed; print for the Phase 8 report.
        print(
            f"\n[Phase8 benchmark] n=128 steps=3000  "
            f"numpy={t_np:.4f}s  cpp={t_cpp:.4f}s  "
            f"speedup={t_np / t_cpp if t_cpp > 0 else float('inf'):.2f}x  "
            f"agreement_tol={CPP_NUMPY_AGREEMENT_TOL:g}"
        )
        self.assertGreater(t_np, 0.0)
        self.assertGreater(t_cpp, 0.0)


class TestCppUnavailablePath(unittest.TestCase):
    def test_auto_uses_numpy_when_extension_missing(self) -> None:
        with mock.patch(
            "polymer_engine.solvers.phase_field.cpp_extension_available",
            return_value=False,
        ):
            out = PhaseFieldSolver().solve(
                SimulationInput(
                    chi=0.05,
                    degree_of_polymerization=100,
                    n_grid=32,
                    n_iterations=80,
                    timestep=5.0e-4,
                    random_seed=2,
                    settings={"backend": "auto"},
                )
            )
            self.assertEqual(out.method_details["backend"], "numpy")


if __name__ == "__main__":
    unittest.main()
