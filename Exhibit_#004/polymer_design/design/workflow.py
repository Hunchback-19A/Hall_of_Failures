# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Orchestrate target → candidates → evaluate → rank (no optimizer rewrite)."""

from __future__ import annotations

from pathlib import Path

from polymer_design.design.candidates import CandidateGridGenerator
from polymer_design.design.ranking import RankedCandidate, rank_candidates
from polymer_design.design.report import format_design_report
from polymer_design.design.target import DesignTarget
from polymer_design.evaluator import SimplifiedPhysicsEvaluator


class DesignExplorer:
    """
    Inverse design exploration workflow.

    Uses SimplifiedPhysicsEvaluator as a black-box scorer without modifying it.
    Does not use or alter the existing random/PSO/MCTS modules.
    """

    def __init__(
        self,
        monomers_path: str | Path,
        evaluator: SimplifiedPhysicsEvaluator | None = None,
        generator: CandidateGridGenerator | None = None,
    ) -> None:
        self.monomers_path = Path(monomers_path)
        self.evaluator = evaluator or SimplifiedPhysicsEvaluator(
            monomers_path=self.monomers_path
        )
        self.generator = generator or CandidateGridGenerator(self.monomers_path)

    def explore(
        self,
        target: DesignTarget,
        *,
        use_pscf: bool = False,
        pscf_top: int = 3,
        pscf_timeout_s: float = 3600.0,
    ) -> tuple[list[RankedCandidate], int, str]:
        target.validate()
        candidates = self.generator.generate(target)
        meta: list[tuple] = []
        for cand in candidates:
            pred = self.evaluator.evaluate(cand.polymer)
            meta.append((pred, cand.method, cand.assumptions))
        ranked = rank_candidates(meta, target)
        report = format_design_report(target, ranked, n_evaluated=len(candidates))
        if use_pscf and ranked:
            from polymer_engine.solvers.pscf_rpc.design import design_pscf_section

            limit = max(1, pscf_top)
            rows = [
                (
                    item.prediction.polymer.name,
                    item.prediction.polymer.architecture,
                    list(item.prediction.polymer.volume_fractions),
                    float(item.prediction.chiN),
                )
                for item in ranked[:limit]
            ]
            report += design_pscf_section(rows, timeout_s=pscf_timeout_s)
        return ranked, len(candidates), report
