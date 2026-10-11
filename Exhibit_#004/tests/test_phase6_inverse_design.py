"""Phase 6 tests: inverse design exploration framework."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polymer_design.design import DesignExplorer, DesignTarget
from polymer_design.design.candidates import CandidateGridGenerator
from polymer_design.design.ranking import rank_candidates, score_prediction
from polymer_design.design.report import format_design_report
from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.polymer import Block, Polymer


MONOMERS = ROOT / "polymer_design" / "data" / "monomers.json"


class TestDesignTarget(unittest.TestCase):
    def test_rejects_bad_f_window(self) -> None:
        with self.assertRaises(ValueError):
            DesignTarget(f_min=0.6, f_max=0.7).validate()


class TestCandidateGrid(unittest.TestCase):
    def test_generates_from_monomers_not_fixed_db(self) -> None:
        gen = CandidateGridGenerator(
            MONOMERS,
            f_values=[0.25, 0.50],
            N_values=[100.0, 200.0],
        )
        target = DesignTarget(
            morphology="lamellae",
            block_a="styrene",
            block_b="MMA",
            f_min=0.25,
            f_max=0.50,
            N_min=100,
            N_max=200,
            chiN_min=0.0,
        )
        cands = gen.generate(target)
        self.assertGreaterEqual(len(cands), 1)
        self.assertTrue(all(c.polymer.architecture == "diblock" for c in cands))
        self.assertTrue(all("grid" in c.method.lower() for c in cands))

    def test_chi_bounds_filter(self) -> None:
        gen = CandidateGridGenerator(MONOMERS, f_values=[0.5], N_values=[100.0])
        # Extremely tight chi window should yield zero or few pairs.
        target = DesignTarget(chi_min=100.0, chi_max=101.0, f_min=0.5, f_max=0.5)
        self.assertEqual(gen.generate(target), [])


class TestRankingAndReport(unittest.TestCase):
    def test_morphology_match_ranks_higher(self) -> None:
        target = DesignTarget(morphology="lamellae", domain_spacing_nm=None)
        match = SimplifiedPhysicsEvaluator().evaluate(
            Polymer(
                name="match",
                architecture="diblock",
                blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
                chi=0.08,
                degree_of_polymerization=200,
            )
        )
        miss = SimplifiedPhysicsEvaluator().evaluate(
            Polymer(
                name="miss",
                architecture="diblock",
                blocks=[Block("styrene", 0.15), Block("MMA", 0.85)],
                chi=0.08,
                degree_of_polymerization=200,
            )
        )
        ranked = rank_candidates(
            [
                (miss, "test", ["a"]),
                (match, "test", ["a"]),
            ],
            target,
        )
        self.assertEqual(ranked[0].prediction.polymer.name, "match")
        self.assertGreater(ranked[0].breakdown.morphology, ranked[1].breakdown.morphology)

        report = format_design_report(target, ranked, n_evaluated=2, top_k=2)
        self.assertIn("Score:", report)
        self.assertIn("breakdown:", report)
        self.assertIn("morphology", report.lower())
        self.assertIn("Assumptions:", report)

    def test_score_breakdown_fields(self) -> None:
        pred = SimplifiedPhysicsEvaluator().evaluate(
            Polymer(
                name="x",
                architecture="diblock",
                blocks=[Block("styrene", 0.5), Block("MMA", 0.5)],
                chi=0.05,
                degree_of_polymerization=300,
            )
        )
        b = score_prediction(pred, DesignTarget(morphology="lamellae"))
        self.assertAlmostEqual(b.morphology, 1.0)
        self.assertIn("morphology", b.details)
        self.assertIn("weights", b.details)


class TestDesignExplorer(unittest.TestCase):
    def test_end_to_end_small_grid(self) -> None:
        gen = CandidateGridGenerator(
            MONOMERS,
            f_values=[0.35, 0.50],
            N_values=[200.0],
        )
        explorer = DesignExplorer(
            monomers_path=MONOMERS,
            evaluator=SimplifiedPhysicsEvaluator(monomers_path=MONOMERS),
            generator=gen,
        )
        target = DesignTarget(
            morphology="lamellae",
            block_a="styrene",
            block_b="MMA",
            f_min=0.35,
            f_max=0.50,
            N_min=200,
            N_max=200,
            top_k=3,
        )
        ranked, n_eval, report = explorer.explore(target)
        self.assertGreater(n_eval, 0)
        self.assertTrue(ranked)
        self.assertIn("Inverse design exploration report", report)
        self.assertIn("breakdown:", report)
        self.assertIn(ranked[0].prediction.polymer.name, report)


if __name__ == "__main__":
    unittest.main()
