"""Phase 5 tests: local benchmark validation framework."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.main import main
from polymer_design.validation import BenchmarkRunner, load_benchmark, load_benchmark_dir
from polymer_design.validation.runner import morphologies_match


BENCHMARKS = ROOT / "benchmarks"


class TestBenchmarkLoading(unittest.TestCase):
    def test_loads_three_named_cases(self) -> None:
        cases = load_benchmark_dir(BENCHMARKS)
        names = {c.name for c in cases}
        self.assertEqual(names, {"PS-b-PEO", "PS-b-PMMA", "PI-b-PS"})
        for case in cases:
            self.assertEqual(case.references, [])
            self.assertTrue(case.experimental_notes)

    def test_single_file_fields(self) -> None:
        case = load_benchmark(BENCHMARKS / "PS-b-PMMA.json")
        self.assertEqual(case.expected_morphology, "lamellae")
        self.assertIn("symmetric", case.approximate_composition.lower())


class TestMorphologyMatch(unittest.TestCase):
    def test_aliases(self) -> None:
        self.assertTrue(morphologies_match("lamellae", "lamellar"))
        self.assertTrue(morphologies_match("cylinders", "cylinders"))
        self.assertFalse(morphologies_match("spheres", "lamellae"))


class TestBenchmarkRunner(unittest.TestCase):
    def test_default_benchmarks_pass(self) -> None:
        report = BenchmarkRunner().run_dir(BENCHMARKS)
        self.assertEqual(report.n_failed, 0)
        self.assertEqual(report.n_passed, 3)

    def test_mismatch_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "bad-case",
                        "architecture": "diblock",
                        "blocks": [
                            {"name": "styrene", "fraction": 0.5},
                            {"name": "MMA", "fraction": 0.5},
                        ],
                        "parameters": {
                            "chi": 0.05,
                            "degree_of_polymerization": 300,
                        },
                        "expected": {
                            "morphology": "spheres",
                            "approximate_composition": "intentionally wrong expectation",
                        },
                        "experimental_notes": "Negative-control fixture.",
                        "references": [],
                    }
                ),
                encoding="utf-8",
            )
            report = BenchmarkRunner().run_dir(tmp)
            self.assertEqual(report.n_failed, 1)
            self.assertFalse(report.results[0].passed)


class TestValidateCLI(unittest.TestCase):
    def test_validate_command_exit_code(self) -> None:
        code = main(["validate", "--benchmarks", str(BENCHMARKS)])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
