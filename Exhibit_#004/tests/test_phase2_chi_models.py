"""Phase 2 tests: flexible ChiModel interface."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.polymer import Block, Polymer
from polymer_engine.thermodynamics.chi_models import (
    ConstantChiModel,
    LinearTemperatureChiModel,
    SolubilityParameterChiModel,
    build_chi_model,
    estimate_chi_from_solubility,
)


class TestChiModels(unittest.TestCase):
    def test_constant_model(self) -> None:
        model = ConstantChiModel(polymer_A="PS", polymer_B="PEO", chi=0.05)
        result = model.evaluate(temperature_K=423)
        self.assertAlmostEqual(result.chi, 0.05)
        self.assertEqual(result.model_name, "constant")
        self.assertEqual(result.polymer_A, "PS")
        self.assertEqual(result.polymer_B, "PEO")

    def test_linear_temperature_model(self) -> None:
        # χ = A + B/T
        model = LinearTemperatureChiModel(
            polymer_A="PS",
            polymer_B="PEO",
            A=0.01,
            B=20.0,
        )
        result = model.evaluate(temperature_K=400.0)
        self.assertAlmostEqual(result.chi, 0.01 + 20.0 / 400.0)
        self.assertEqual(result.model_name, "linear_temperature")
        self.assertIn("χ(T) = A + B/T", " ".join(result.explanation))

    def test_solubility_parameter_model_matches_helper(self) -> None:
        chi_helper, _ = estimate_chi_from_solubility(18.6, 20.2, 68.5, temperature_K=298.15)
        model = SolubilityParameterChiModel(
            polymer_A="PS",
            polymer_B="PEO",
            delta_a=18.6,
            delta_b=20.2,
            molar_volume_cm3_mol=68.5,
        )
        result = model.evaluate(temperature_K=298.15)
        self.assertAlmostEqual(result.chi, chi_helper)

    def test_build_chi_model_factory(self) -> None:
        const = build_chi_model(
            {"type": "constant", "chi": 0.04, "polymer_A": "PS", "polymer_B": "PMMA"}
        )
        self.assertAlmostEqual(const.evaluate().chi, 0.04)

        linear = build_chi_model(
            {
                "type": "linear_temperature",
                "A": -0.02,
                "B": 30.0,
                "polymer_A": "PS",
                "polymer_B": "PEO",
            }
        )
        self.assertAlmostEqual(linear.evaluate(350.0).chi, -0.02 + 30.0 / 350.0)

    def test_negative_chi_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ConstantChiModel(chi=-0.1)


class TestEvaluatorChiModelIntegration(unittest.TestCase):
    def test_legacy_constant_chi_unchanged(self) -> None:
        polymer = Polymer(
            name="PS-b-PMMA",
            architecture="diblock",
            blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
            chi=0.04,
            degree_of_polymerization=100,
        )
        pred = SimplifiedPhysicsEvaluator().evaluate(polymer)
        self.assertAlmostEqual(pred.chi, 0.04)
        self.assertAlmostEqual(pred.chiN, 4.0)
        self.assertEqual(pred.chi_model_name, "constant")
        self.assertEqual(pred.morphology, "disordered / mixed phase")

    def test_json_chi_model_and_temperature(self) -> None:
        polymer = Polymer.from_dict(
            {
                "name": "PS-b-PEO-T",
                "architecture": "diblock",
                "blocks": [
                    {"name": "styrene", "fraction": 0.5},
                    {"name": "EO", "fraction": 0.5},
                ],
                "parameters": {
                    "degree_of_polymerization": 200,
                    "temperature": 423,
                    "chi_model": {
                        "type": "linear_temperature",
                        "A": 0.0,
                        "B": 21.15,
                        "polymer_A": "PS",
                        "polymer_B": "PEO",
                    },
                },
            }
        )
        pred = SimplifiedPhysicsEvaluator().evaluate(polymer)
        expected_chi = 21.15 / 423.0
        self.assertAlmostEqual(pred.chi, expected_chi)
        self.assertAlmostEqual(pred.chiN, expected_chi * 200)
        self.assertEqual(pred.chi_model_name, "linear_temperature")
        self.assertAlmostEqual(pred.temperature_K or 0.0, 423.0)

    def test_evaluator_injected_chi_model(self) -> None:
        model = ConstantChiModel(polymer_A="PS", polymer_B="PEO", chi=0.08)
        evaluator = SimplifiedPhysicsEvaluator(chi_model=model)
        polymer = Polymer(
            name="injected",
            architecture="diblock",
            blocks=[Block("styrene", 0.3), Block("EO", 0.7)],
            degree_of_polymerization=150,
            # polymer.chi intentionally omitted; evaluator model should win
        )
        pred = evaluator.evaluate(polymer)
        self.assertAlmostEqual(pred.chi, 0.08)
        self.assertAlmostEqual(pred.chiN, 12.0)


if __name__ == "__main__":
    unittest.main()
