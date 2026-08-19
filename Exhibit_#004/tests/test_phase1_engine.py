"""
Phase 1 regression tests.

Lock χN, morphology, and evaluator free-energy proxy scores to the
pre-refactor SimplifiedPhysicsEvaluator behavior.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.physics import chi_model as shim_chi
from polymer_design.physics import free_energy as shim_fe
from polymer_design.physics import morphology as shim_morph
from polymer_design.polymer import Block, Polymer, load_polymers
from polymer_engine.energetics.free_energy import FreeEnergyProxy
from polymer_engine.morphology.morphology_prediction import MorphologyPredictor
from polymer_engine.thermodynamics.flory_huggins import (
    SYMMETRIC_DIBLOCK_ODT_CHIN,
    compute_chiN,
)


DATA = ROOT / "polymer_design" / "data" / "polymers.json"
MONOMERS = ROOT / "polymer_design" / "data" / "monomers.json"


# Golden values captured from the pre-refactor simplified engine.
GOLDEN = {
    "weakly-segregated-demo": {
        "chiN": 4.0,
        "morphology": "disordered / mixed phase",
        "regime": "disordered / mixed",
        "confidence": "Low",
        "confidence_score": 0.45,
        "free_energy_score": (SYMMETRIC_DIBLOCK_ODT_CHIN - 4.0) ** 2,
    },
    "PS-b-PMMA": {
        "chiN": 7.4,
        "morphology": "disordered / mixed phase",
        "regime": "disordered / mixed",
        "confidence": "Low",
        "confidence_score": 0.45,
        "free_energy_score": (SYMMETRIC_DIBLOCK_ODT_CHIN - 7.4) ** 2,
    },
    "PS-b-PI": {
        "chiN": 13.5,
        "morphology": "gyroid",
        "regime": "weak segregation",
        "confidence": "Medium",
        "confidence_score": 0.60,
        "free_energy_score": -2.025,
    },
    "SBS": {
        "chiN": 24.0,
        "morphology": "cylinders",
        "regime": "weak segregation",
        "confidence": "Medium",
        "confidence_score": 0.50,
        "free_energy_score": -12.185,
    },
    "PS-b-PEO-asymmetric": {
        "chiN": 14.4,
        "morphology": "cylinders",
        "regime": "weak segregation",
        "confidence": "Medium",
        "confidence_score": 0.60,
        "free_energy_score": -2.385,
    },
}


class TestChiNRegression(unittest.TestCase):
    def test_known_products(self) -> None:
        cases = [
            (0.04, 100, 4.0, "disordered / mixed"),
            (0.037, 200, 7.4, "disordered / mixed"),
            (0.09, 150, 13.5, "weak segregation"),
            (0.08, 300, 24.0, "weak segregation"),
            (0.12, 120, 14.4, "weak segregation"),
        ]
        for chi, N, chiN, regime in cases:
            with self.subTest(chi=chi, N=N):
                result = compute_chiN(chi, N)
                self.assertAlmostEqual(result.chiN, chiN)
                self.assertEqual(result.segregation_regime, regime)


class TestMorphologyRegression(unittest.TestCase):
    def test_phase_windows(self) -> None:
        predictor = MorphologyPredictor()
        # Ordered regime with χN above ODT.
        cases = [
            ([0.10, 0.90], "spheres"),
            ([0.20, 0.80], "cylinders"),
            ([0.35, 0.65], "gyroid"),
            ([0.50, 0.50], "lamellae"),
        ]
        for f_values, expected in cases:
            with self.subTest(f=f_values):
                result = predictor.predict(f_values, chiN=20.0, segregation_regime="weak segregation")
                self.assertEqual(result.morphology, expected)

    def test_below_odt_is_disordered(self) -> None:
        predictor = MorphologyPredictor()
        result = predictor.predict([0.5, 0.5], chiN=4.0, segregation_regime="disordered / mixed")
        self.assertEqual(result.morphology, "disordered / mixed phase")


class TestEvaluatorRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evaluator = SimplifiedPhysicsEvaluator(monomers_path=MONOMERS)
        cls.library = {p.name: p for p in load_polymers(DATA)}

    def test_library_goldens(self) -> None:
        for name, expected in GOLDEN.items():
            with self.subTest(polymer=name):
                pred = self.evaluator.evaluate(self.library[name])
                self.assertAlmostEqual(pred.chiN, expected["chiN"])
                self.assertEqual(pred.morphology, expected["morphology"])
                self.assertEqual(pred.segregation_regime, expected["regime"])
                self.assertEqual(pred.confidence, expected["confidence"])
                self.assertAlmostEqual(pred.confidence_score, expected["confidence_score"])
                self.assertAlmostEqual(pred.free_energy_score, expected["free_energy_score"], places=6)

    def test_prompt_example_json(self) -> None:
        polymer = Polymer(
            name="PS-b-PMMA",
            architecture="diblock",
            blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
            chi=0.04,
            degree_of_polymerization=100,
        )
        pred = self.evaluator.evaluate(polymer)
        self.assertAlmostEqual(pred.chiN, 4.0)
        self.assertEqual(pred.morphology, "disordered / mixed phase")
        self.assertAlmostEqual(pred.free_energy_score, (SYMMETRIC_DIBLOCK_ODT_CHIN - 4.0) ** 2)


class TestCompatibilityShims(unittest.TestCase):
    def test_shim_compute_chiN(self) -> None:
        a = compute_chiN(0.05, 200)
        b = shim_chi.compute_chiN(0.05, 200)
        self.assertEqual(a.chiN, b.chiN)
        self.assertEqual(a.segregation_regime, b.segregation_regime)

    def test_shim_morphology_and_energy(self) -> None:
        engine_pred = MorphologyPredictor().predict(
            [0.25, 0.75], chiN=25.0, segregation_regime="weak segregation"
        )
        shim_pred = shim_morph.MorphologyPredictor().predict(
            [0.25, 0.75], chiN=25.0, segregation_regime="weak segregation"
        )
        self.assertEqual(engine_pred.morphology, shim_pred.morphology)

        engine_fe = FreeEnergyProxy().evaluate(25.0, engine_pred.f_minor, engine_pred)
        shim_score = shim_fe.FreeEnergyProxy().evaluate(25.0, shim_pred.f_minor, shim_pred)
        self.assertAlmostEqual(engine_fe.score, shim_score.score)


if __name__ == "__main__":
    unittest.main()
