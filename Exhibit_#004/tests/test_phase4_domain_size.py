"""Phase 4 tests: domain spacing and characteristic length estimates."""

from __future__ import annotations

import sys
import unittest
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.polymer import Block, Polymer, load_polymers
from polymer_engine.output.report_generator import format_report
from polymer_engine.structure.domain_size import (
    DEFAULT_SEGMENT_LENGTH_NM,
    DomainSizeEstimator,
    radius_of_gyration_nm,
)
from polymer_engine.thermodynamics.flory_huggins import (
    INTERMEDIATE_SEGREGATION_UPPER,
    SYMMETRIC_DIBLOCK_ODT_CHIN,
)


DATA = ROOT / "polymer_design" / "data" / "polymers.json"
MONOMERS = ROOT / "polymer_design" / "data" / "monomers.json"


class TestRadiusOfGyration(unittest.TestCase):
    def test_ideal_chain_formula(self) -> None:
        N = 150.0
        a = 0.5
        self.assertAlmostEqual(radius_of_gyration_nm(N, a), a * sqrt(N / 6.0))


class TestDomainSizeEstimator(unittest.TestCase):
    def setUp(self) -> None:
        self.est = DomainSizeEstimator(segment_length_nm=0.5)

    def test_disordered_has_no_spacing(self) -> None:
        result = self.est.estimate(
            N=100,
            chi=0.04,
            chiN=4.0,
            morphology="disordered / mixed phase",
        )
        self.assertIsNone(result.domain_spacing_nm)
        self.assertIn("disordered", result.model.lower())
        self.assertAlmostEqual(
            result.radius_of_gyration_nm,
            DEFAULT_SEGMENT_LENGTH_NM * sqrt(100 / 6.0),
        )

    def test_weak_segregation_scaling(self) -> None:
        N = 200.0
        chi = 0.08
        chiN = 16.0
        self.assertGreaterEqual(chiN, SYMMETRIC_DIBLOCK_ODT_CHIN)
        self.assertLess(chiN, INTERMEDIATE_SEGREGATION_UPPER)
        result = self.est.estimate(
            N=N,
            chi=chi,
            chiN=chiN,
            morphology="lamellae",
        )
        self.assertIsNotNone(result.domain_spacing_nm)
        self.assertIn("weak segregation", result.model.lower())
        rg = radius_of_gyration_nm(N, 0.5)
        expected = (2.0 * 3.141592653589793 / 1.95) * rg
        self.assertAlmostEqual(result.domain_spacing_nm or 0.0, expected, places=6)

    def test_strong_segregation_scaling(self) -> None:
        N = 400.0
        chi = 0.2
        chiN = 80.0
        result = self.est.estimate(
            N=N,
            chi=chi,
            chiN=chiN,
            morphology="lamellae",
        )
        self.assertIn("strong segregation", result.model.lower())
        expected = 1.10 * 0.5 * (chi ** (1.0 / 6.0)) * (N ** (2.0 / 3.0))
        self.assertAlmostEqual(result.domain_spacing_nm or 0.0, expected, places=6)

    def test_cylinder_factor_increases_spacing(self) -> None:
        base = self.est.estimate(N=200, chi=0.1, chiN=20, morphology="lamellae")
        cyl = self.est.estimate(N=200, chi=0.1, chiN=20, morphology="cylinders")
        self.assertGreater(cyl.domain_spacing_nm or 0.0, base.domain_spacing_nm or 0.0)


class TestEvaluatorDomainSize(unittest.TestCase):
    def test_disordered_library_case(self) -> None:
        polymer = Polymer(
            name="demo",
            architecture="diblock",
            blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
            chi=0.04,
            degree_of_polymerization=100,
        )
        pred = SimplifiedPhysicsEvaluator().evaluate(polymer)
        self.assertIsNone(pred.domain_spacing_nm)
        self.assertIsNotNone(pred.radius_of_gyration_nm)
        report = format_report(pred, show_calculations=False)
        self.assertIn("Predicted domain spacing:", report)
        self.assertIn("n/a", report)
        self.assertIn("Model:", report)

    def test_ordered_library_case_has_spacing(self) -> None:
        library = {p.name: p for p in load_polymers(DATA)}
        pred = SimplifiedPhysicsEvaluator(monomers_path=MONOMERS).evaluate(library["SBS"])
        self.assertIsNotNone(pred.domain_spacing_nm)
        self.assertGreater(pred.domain_spacing_nm or 0.0, 0.0)
        self.assertIsNotNone(pred.domain_size_model)
        # Phase 1 score regression still holds.
        self.assertAlmostEqual(pred.free_energy_score, -12.185, places=6)


if __name__ == "__main__":
    unittest.main()
