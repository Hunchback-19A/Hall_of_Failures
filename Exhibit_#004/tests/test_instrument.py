"""Request validation, reports, and ranking. PSCF is launched only in one regression."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from polymer_design.instrument.engine import execute_request
from polymer_design.instrument.report import format_report
from polymer_design.instrument.schema import parse_request
from polymer_design.instrument.xlsx_export import write_xlsx
from polymer_engine.solvers.base import SimulationOutput
from polymer_engine.solvers.pscf_rpc.paramfile import rewrite_diblock_param
from polymer_engine.solvers.pscf_rpc.runner import find_pscf_rpc

_ROOT = Path(__file__).resolve().parents[1]
_LAM = _ROOT / "third_party" / "pscfpp" / "examples" / "rpc" / "scf" / "diblock" / "lam" / "param"
_EXAMPLE = _ROOT / "polymer_design" / "data" / "examples" / "periodic_lamellar.json"


def _candidate(**overrides):
    item = {
        "architecture": "diblock",
        "volume_fractions": [0.5, 0.5],
        "chi": 0.05,
        "degree_of_polymerization": 200,
    }
    item.update(overrides)
    return item


def _request(**overrides):
    payload = {
        "client": "human",
        "solver": "analytical",
        "candidates": [_candidate(id="one")],
    }
    payload.update(overrides)
    return payload


class _FakeSolver:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def solve(self, sim):
        self.calls.append(sim.name)
        return self.outputs[sim.name]


def _pscf_output(name, cells):
    winner = next(item for item in cells if item["converged"])
    return SimulationOutput(
        solver_name="pscf_rpc",
        morphology=winner["morphology"],
        energy=winner["fHelmholtz"],
        chiN=10.0,
        success=True,
        structure={"cells": cells},
        convergence={"converged": True},
        method_details={"upstream": "pscf_rpc"},
        notes=["cell note"],
    )


class ValidationTests(unittest.TestCase):
    def test_human_and_ai_share_validation(self) -> None:
        human = parse_request(_request(client="human"))
        ai = parse_request(_request(client="AI"))
        self.assertEqual(human.client, "human")
        self.assertEqual(ai.client, "ai")
        self.assertEqual(human.candidates[0].chiN, ai.candidates[0].chiN)

    def test_disagreement_is_rejected(self) -> None:
        with self.assertRaises(ValueError) as caught:
            parse_request(_request(candidates=[_candidate(chi=0.05, chiN=20, N=200)]))
        self.assertIn("disagree", str(caught.exception))

    def test_fractions_are_not_rescaled(self) -> None:
        with self.assertRaises(ValueError) as caught:
            parse_request(_request(candidates=[_candidate(volume_fractions=[0.2, 0.2])]))
        self.assertIn("not rescaled", str(caught.exception))

    def test_batch_limit_rejects_without_truncation(self) -> None:
        payload = _request(candidates=[_candidate(id=f"c{i}") for i in range(1001)])
        with self.assertRaises(ValueError) as caught:
            parse_request(payload)
        self.assertIn("1001", str(caught.exception))
        self.assertIn("not truncated", str(caught.exception))

    def test_request_cannot_raise_the_limit(self) -> None:
        payload = _request()
        payload["max_candidates"] = 100000
        with self.assertRaises(ValueError) as caught:
            parse_request(payload)
        self.assertIn("max_candidates", str(caught.exception))

    def test_operator_limit_applies_to_ai_requests(self) -> None:
        payload = _request(
            client="ai",
            candidates=[_candidate(id="a"), _candidate(id="b"), _candidate(id="c")],
        )
        with patch.dict(os.environ, {"POLYMER_DESIGN_MAX_CANDIDATES": "2"}):
            with self.assertRaises(ValueError) as caught:
                parse_request(payload)
        self.assertIn("limit is 2", str(caught.exception))


class ResultTests(unittest.TestCase):
    def test_unconverged_cells_are_not_ranked(self) -> None:
        cells = [
            {"cell": "lam", "morphology": "lamellae", "dimension": 1, "fHelmholtz": 5.0, "converged": False, "detail": "no"},
            {"cell": "gyr", "morphology": "gyroid", "dimension": 3, "fHelmholtz": 1.5, "converged": True, "detail": "yes"},
            {"cell": "hex", "morphology": "hexagonal cylinders", "dimension": 2, "fHelmholtz": 1.2, "converged": True, "detail": "yes"},
        ]
        fake = _FakeSolver({"one": _pscf_output("one", cells)})
        request = parse_request(_request(solver="pscf_rpc", cells=["lam", "hex", "gyr"]))
        with patch("polymer_design.instrument.engine.get_solver", return_value=fake):
            result = execute_request(request, progress=lambda _message: None)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["preferred_morphology"], "hexagonal cylinders")
        lam = next(item for item in candidate["morphologies"] if item["cell"] == "lam")
        self.assertFalse(lam["converged"])
        self.assertIsNone(lam["free_energy"])
        self.assertEqual(lam["reported_free_energy"], 5.0)
        self.assertEqual(lam["space_group"], "P_-1")
        self.assertAlmostEqual(candidate["free_energy"], 1.2)

    def test_failed_candidate_is_kept(self) -> None:
        class Boom:
            def solve(self, sim):
                if sim.name == "bad":
                    raise RuntimeError("solver stopped")
                return SimulationOutput(
                    solver_name="analytical",
                    morphology="lamellae",
                    energy=1.0,
                    chiN=10.0,
                    success=True,
                )

        request = parse_request(
            _request(candidates=[_candidate(id="bad", name="bad"), _candidate(id="ok", name="ok")])
        )
        with patch("polymer_design.instrument.engine.get_solver", return_value=Boom()):
            result = execute_request(request, progress=lambda _message: None)
        self.assertEqual(result["status"], "completed_with_failures")
        self.assertEqual(result["candidates"][0]["status"], "failed")
        self.assertEqual(result["ranking"][0]["id"], "ok")
        self.assertEqual(len(result["ranking"]), 1)

    def test_resume_does_not_rerun_a_recorded_candidate(self) -> None:
        fake = _FakeSolver(
            {
                "one": SimulationOutput("analytical", "lamellae", 1.0, 10.0, success=True),
                "two": SimulationOutput("analytical", "disordered", 2.0, 10.0, success=True),
            }
        )
        request = parse_request(
            _request(candidates=[_candidate(id="one", name="one"), _candidate(id="two", name="two")])
        )
        with patch("polymer_design.instrument.engine.get_solver", return_value=fake):
            first = execute_request(request, progress=lambda _message: None)
            fake.calls.clear()
            second = execute_request(
                request,
                prior={"one": first["candidates"][0]},
                progress=lambda _message: None,
            )
        self.assertEqual(fake.calls, ["two"])
        self.assertEqual(second["candidates"][0]["id"], "one")
        self.assertEqual([row["id"] for row in second["ranking"]], ["one", "two"])

    def test_report_and_spreadsheet(self) -> None:
        fake = _FakeSolver(
            {"one": SimulationOutput("analytical", "lamellae", 1.25, 10.0, success=True, notes=["proxy"])}
        )
        request = parse_request(_request(client="ai", request_id="demo"))
        with patch("polymer_design.instrument.engine.get_solver", return_value=fake):
            result = execute_request(request, progress=lambda _message: None)
        text = format_report(result)
        self.assertIn("Client: ai", text)
        self.assertIn("Normal termination", text)
        self.assertIn("requires experimental validation", text)
        self.assertIn("does not claim that a morphology will form", text)
        self.assertNotIn("the morphology will form", text)
        encoded = json.dumps(result)
        self.assertIn("polymer_design.result.v1", encoded)
        self.assertIn("demo", encoded)
        folder = Path(os.environ.get("TEMP", "."))
        book = folder / "polymer-design-instrument-test.xlsx"
        write_xlsx(book, result)
        with zipfile.ZipFile(book) as archive:
            sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("candidate_id", sheet)
        self.assertIn("one", sheet)
        book.unlink(missing_ok=True)

    def test_request_chi_n_is_what_the_pscf_param_receives(self) -> None:
        request = parse_request(
            _request(
                solver="pscf_rpc",
                cells=["lam"],
                candidates=[_candidate(volume_fractions=[0.5, 0.5], chi=0.125, N=200)],
            )
        )
        rewritten = rewrite_diblock_param(_LAM.read_text(encoding="utf-8"), 0.5, request.candidates[0].chiN)
        self.assertIn("25", rewritten)
        self.assertNotIn("12.0", rewritten)


class KnownLamellarRegression(unittest.TestCase):
    def test_vendored_lamellar_example(self) -> None:
        if find_pscf_rpc() is None:
            self.skipTest("pscf_rpc is not available")
        request = parse_request(json.loads(_EXAMPLE.read_text(encoding="utf-8")))
        result = execute_request(request, progress=lambda _message: None)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["status"], "converged")
        self.assertEqual(candidate["preferred_morphology"], "lamellae")
        self.assertAlmostEqual(candidate["free_energy"], 1.92567500294, places=8)
        self.assertTrue(result["pscf_commit"])


class TerminalPathTests(unittest.TestCase):
    def test_run_prints_absolute_output_paths(self) -> None:
        from polymer_design.main import main

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            request = root / "candidate.inp"
            request.write_text(
                json.dumps(
                    {
                        "client": "human",
                        "solver": "analytical",
                        "candidates": [
                            {
                                "id": "one",
                                "architecture": "diblock",
                                "volume_fractions": [0.5, 0.5],
                                "chi": 0.05,
                                "N": 200,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            xlsx = root / "table.xlsx"
            stderr = io.StringIO()
            with patch("sys.stderr", stderr), patch("sys.stdout", io.StringIO()):
                code = main(["run", str(request), "--xlsx", str(xlsx)])
            self.assertEqual(code, 0)
            report = request.with_suffix(".out").resolve()
            result = request.with_suffix(".result.json").resolve()
            text = stderr.getvalue()
            self.assertIn(f"report: {report}", text)
            self.assertIn(f"result: {result}", text)
            self.assertIn(f"spreadsheet: {xlsx.resolve()}", text)
            self.assertTrue(report.is_file())
            self.assertTrue(result.is_file())
            self.assertNotEqual(result, request.resolve())
