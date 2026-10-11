"""Phase 3 tests: free-energy contribution framework."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.polymer import Block, Polymer, load_polymers
from polymer_engine.energetics.contributions import (
    FreeEnergyContext,
    InterfaceContribution,
    MixingContribution,
    StretchingContribution,
)
from polymer_engine.energetics.free_energy import FreeEnergyProxy, MorphologyFreeEnergyModel
from polymer_engine.morphology.morphology_prediction import MorphologyPredictor
from polymer_engine.thermodynamics.flory_huggins import SYMMETRIC_DIBLOCK_ODT_CHIN


DATA = ROOT / "polymer_design" / "data" / "polymers.json"
MONOMERS = ROOT / "polymer_design" / "data" / "monomers.json"


def _morph(f_values: list[float], chiN: float):
    regime = "disordered / mixed" if chiN < SYMMETRIC_DIBLOCK_ODT_CHIN else "weak segregation"
    return MorphologyPredictor().predict(f_values, chiN=chiN, segregation_regime=regime)


class TestContributions(unittest.TestCase):
    def test_disordered_only_mixing(self) -> None:
        morph = _morph([0.5, 0.5], chiN=4.0)
        ctx = FreeEnergyContext(chiN=4.0, f_minor=0.5, morphology=morph)

        mix = MixingContribution().evaluate(ctx)
        iface = InterfaceContribution().evaluate(ctx)
        stretch = StretchingContribution().evaluate(ctx)

        self.assertAlmostEqual(mix.value, (SYMMETRIC_DIBLOCK_ODT_CHIN - 4.0) ** 2)
        self.assertAlmostEqual(iface.value, 0.0)
        self.assertAlmostEqual(stretch.value, 0.0)

    def test_ordered_interface_and_stretching(self) -> None:
        morph = _morph([0.35, 0.65], chiN=13.5)
        ctx = FreeEnergyContext(chiN=13.5, f_minor=0.35, morphology=morph)

        mix = MixingContribution().evaluate(ctx)
        iface = InterfaceContribution().evaluate(ctx)
        stretch = StretchingContribution().evaluate(ctx)

        self.assertAlmostEqual(mix.value, 0.0)
        self.assertAlmostEqual(iface.value, -(13.5 - SYMMETRIC_DIBLOCK_ODT_CHIN))
        self.assertAlmostEqual(stretch.value, 8.0 * (0.5 - 0.35) ** 2)


class TestMorphologyFreeEnergyModel(unittest.TestCase):
    def test_exposes_named_contributions(self) -> None:
        morph = _morph([0.5, 0.5], chiN=4.0)
        result = MorphologyFreeEnergyModel().evaluate(4.0, 0.5, morph)
        self.assertIn("mixing", result.contributions)
        self.assertIn("interface", result.contributions)
        self.assertIn("stretching", result.contributions)
        self.assertAlmostEqual(result.score, result.contributions["mixing"])

    def test_proxy_matches_model(self) -> None:
        morph = _morph([0.3, 0.7], chiN=24.0)
        model = MorphologyFreeEnergyModel()
        proxy = FreeEnergyProxy(model=model)
        a = model.evaluate(24.0, 0.3, morph)
        b = proxy.evaluate(24.0, 0.3, morph)
        self.assertAlmostEqual(a.score, b.score)
        self.assertEqual(a.contributions, b.contributions)


class TestScoreRegressionViaEvaluator(unittest.TestCase):
    """Ensure Phase 3 does not change evaluator scores for library polymers."""

    def test_library_scores_unchanged(self) -> None:
        expected = {
            "weakly-segregated-demo": (SYMMETRIC_DIBLOCK_ODT_CHIN - 4.0) ** 2,
            "PS-b-PMMA": (SYMMETRIC_DIBLOCK_ODT_CHIN - 7.4) ** 2,
            "PS-b-PI": -2.025,
            "SBS": -12.185,
            "PS-b-PEO-asymmetric": -2.385,
        }
        evaluator = SimplifiedPhysicsEvaluator(monomers_path=MONOMERS)
        library = {p.name: p for p in load_polymers(DATA)}
        for name, score in expected.items():
            with self.subTest(polymer=name):
                pred = evaluator.evaluate(library[name])
                self.assertAlmostEqual(pred.free_energy_score, score, places=6)
                # Contribution breakdown should be present on the proxy result path.
                self.assertIn("mixing", pred.free_energy_terms)
                self.assertIn("interface", pred.free_energy_terms)
                self.assertIn("stretching", pred.free_energy_terms)


if __name__ == "__main__":
    unittest.main()
