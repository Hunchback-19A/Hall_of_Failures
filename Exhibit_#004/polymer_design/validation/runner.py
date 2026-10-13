"""Run morphology predictions against local benchmark fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from polymer_design.evaluator import Prediction, SimplifiedPhysicsEvaluator
from polymer_design.polymer import Polymer

from .benchmark import BenchmarkCase, load_benchmark_dir


def morphologies_match(predicted: str, expected: str) -> bool:
    """Loose label match (e.g. 'lamellae' vs 'lamellar')."""
    pred = predicted.strip().lower()
    exp = expected.strip().lower()
    if pred == exp:
        return True
    aliases = {
        "lamellae": {"lamellae", "lamellar", "lamella"},
        "cylinders": {"cylinders", "cylindrical", "hex", "hexagonal cylinders"},
        "spheres": {"spheres", "spherical", "bcc"},
        "gyroid": {"gyroid", "double gyroid", "double-gyroid"},
        "disordered / mixed phase": {
            "disordered",
            "disordered / mixed",
            "disordered / mixed phase",
            "mixed",
            "homogeneous",
        },
    }
    for group in aliases.values():
        if exp in group and pred in group:
            return True
        if exp in group and any(token in pred for token in group if len(token) > 3):
            return True
    return exp in pred or pred in exp


@dataclass
class CaseResult:
    name: str
    passed: bool
    expected_morphology: str
    predicted_morphology: str
    chiN: float
    approximate_composition: str
    experimental_notes: str
    references: list
    details: str = ""
    prediction: Prediction | None = None


@dataclass
class BenchmarkReport:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def summary_lines(self) -> list[str]:
        lines = [
            "=" * 64,
            "Benchmark validation report",
            f"Cases: {len(self.results)}  passed: {self.n_passed}  failed: {self.n_failed}",
            "=" * 64,
        ]
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.extend(
                [
                    f"[{status}] {r.name}",
                    f"  composition: {r.approximate_composition}",
                    f"  expected:    {r.expected_morphology}",
                    f"  predicted:   {r.predicted_morphology}  (χN = {r.chiN:.4g})",
                ]
            )
            if r.experimental_notes:
                lines.append(f"  notes:       {r.experimental_notes}")
            if r.references:
                lines.append(
                    f"  references:  {len(r.references)} user-supplied entr(y/ies)"
                )
            else:
                lines.append(
                    "  references:  (none — add real citations manually if needed)"
                )
            if r.details:
                lines.append(f"  details:     {r.details}")
            lines.append("")
        return lines

    def format(self) -> str:
        return "\n".join(self.summary_lines()).rstrip() + "\n"


class BenchmarkRunner:
    """
    Compare SimplifiedPhysicsEvaluator (or any evaluate_fn) to local benchmarks.

    Does not download data or generate citations.
    """

    def __init__(
        self,
        evaluate_fn: Callable[[Polymer], Prediction] | None = None,
        evaluator: SimplifiedPhysicsEvaluator | None = None,
    ) -> None:
        if evaluate_fn is not None:
            self.evaluate_fn = evaluate_fn
        else:
            ev = evaluator or SimplifiedPhysicsEvaluator()
            self.evaluate_fn = ev.evaluate

    def run_case(self, case: BenchmarkCase) -> CaseResult:
        pred = self.evaluate_fn(case.polymer)
        ok = morphologies_match(pred.morphology, case.expected_morphology)
        details = ""
        if not ok:
            details = (
                "Morphology mismatch between benchmark expectation and current engine."
            )
        return CaseResult(
            name=case.name,
            passed=ok,
            expected_morphology=case.expected_morphology,
            predicted_morphology=pred.morphology,
            chiN=pred.chiN,
            approximate_composition=case.approximate_composition,
            experimental_notes=case.experimental_notes,
            references=list(case.references),
            details=details,
            prediction=pred,
        )

    def run_dir(self, directory: str | Path) -> BenchmarkReport:
        cases = load_benchmark_dir(directory)
        return BenchmarkReport(results=[self.run_case(c) for c in cases])
