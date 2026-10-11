"""Adapter tests for the vendored pscf_rpc examples. They do not launch PSCF."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from polymer_engine.solvers.base import SimulationInput
from polymer_engine.solvers.pscf_rpc.paramfile import (
    iteration_converged,
    parse_f_helmholtz,
    rewrite_diblock_param,
)
from polymer_engine.solvers.pscf_rpc.runner import decode_process_output, pscf_command
from polymer_engine.solvers.pscf_rpc.solver import PscfRpcSolver

_ROOT = Path(__file__).resolve().parents[1]
_LAM = _ROOT / "third_party" / "pscfpp" / "examples" / "rpc" / "scf" / "diblock" / "lam" / "param"


class PscfParamTests(unittest.TestCase):
    def test_rewrite_uses_volume_fraction_and_chi_n(self) -> None:
        text = _LAM.read_text(encoding="utf-8")
        rewritten = rewrite_diblock_param(text, 0.5, 25.0)
        self.assertNotIn("0.56", rewritten)
        self.assertNotIn("12.0", rewritten)
        self.assertIn("0.5", rewritten)
        self.assertIn("25", rewritten)

    def test_parse_f_helmholtz_and_convergence(self) -> None:
        log = "noise\nfHelmholtz    1.25000000000E+01\n Converged\n"
        self.assertEqual(parse_f_helmholtz(log), 12.5)
        self.assertTrue(iteration_converged(log))
        failed = log + "Iterator failed to converge.\n"
        self.assertFalse(iteration_converged(failed))

    def test_missing_executable_is_reported(self) -> None:
        solver = PscfRpcSolver()
        sim = SimulationInput(chi=0.125, degree_of_polymerization=200.0, volume_fractions=[0.5, 0.5])
        with patch("polymer_engine.solvers.pscf_rpc.runner.find_pscf_rpc", return_value=None):
            output = solver.solve(sim)
        self.assertFalse(output.success)
        self.assertEqual(output.morphology, "unavailable")
        self.assertTrue(any("pscf_rpc was not found" in note for note in output.notes))
        self.assertTrue(any("University of Minnesota" in item for item in output.assumptions))

    def test_bundled_windows_exe_is_chosen_when_present(self) -> None:
        exe = _ROOT / "third_party" / "pscfpp" / "bin" / "pscf_rpc.exe"
        if not exe.is_file():
            self.skipTest("Windows pscf_rpc.exe is not in the tree")
        with patch.dict(os.environ, {"PSCF_RPC": ""}, clear=False):
            from polymer_engine.solvers.pscf_rpc.runner import find_pscf_rpc

            found = find_pscf_rpc()
        self.assertEqual(Path(found or ""), exe)

    def test_wsl_command_uses_linux_binary_and_windows_directory(self) -> None:
        case = Path(r"C:\temp\pscf_case")
        argv, process_cwd = pscf_command("wsl:/root/pscfpp/bin/pscf_rpc", 1, case)
        self.assertIsNone(process_cwd)
        self.assertIn("--cd", argv)
        self.assertEqual(argv[argv.index("--cd") + 1], str(case))
        self.assertIn("/root/pscfpp/bin/pscf_rpc", argv)
        self.assertEqual(argv[-7:], ["-d", "1", "-p", "param", "-c", "command", "-e"])

    def test_decode_wsl_utf16_log(self) -> None:
        raw = "fHelmholtz     1.5\n".encode("utf-16")
        self.assertIn("fHelmholtz", decode_process_output(raw))


if __name__ == "__main__":
    unittest.main()
