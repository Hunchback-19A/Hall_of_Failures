"""Random search over a simple diblock design space."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from ..evaluator import Prediction
from ..polymer import Block, Polymer


@dataclass
class SearchResult:
    best: Prediction
    history: list[Prediction]


class RandomSearch:
    """
    Optimizer is intentionally separated from the physics evaluator.

    Candidates are generated here; scoring is delegated to `evaluate_fn`.
    """

    def __init__(
        self,
        evaluate_fn: Callable[[Polymer], Prediction],
        block_a: str = "styrene",
        block_b: str = "MMA",
        chi: float = 0.04,
        f_range: tuple[float, float] = (0.1, 0.5),
        N_range: tuple[float, float] = (50, 300),
        seed: int | None = None,
    ) -> None:
        self.evaluate_fn = evaluate_fn
        self.block_a = block_a
        self.block_b = block_b
        self.chi = chi
        self.f_range = f_range
        self.N_range = N_range
        self.rng = random.Random(seed)

    def _candidate(self, index: int) -> Polymer:
        f = self.rng.uniform(*self.f_range)
        N = self.rng.uniform(*self.N_range)
        return Polymer(
            name=f"random-{index}",
            architecture="diblock",
            blocks=[
                Block(self.block_a, f),
                Block(self.block_b, 1.0 - f),
            ],
            chi=self.chi,
            degree_of_polymerization=N,
        )

    def run(self, n_candidates: int = 20, target_morphology: str | None = None) -> SearchResult:
        history: list[Prediction] = []
        best: Prediction | None = None

        for i in range(n_candidates):
            polymer = self._candidate(i)
            pred = self.evaluate_fn(polymer)
            history.append(pred)

            if target_morphology is not None:
                # Prefer exact morphology matches, then lower free-energy proxy.
                matched = target_morphology.lower() in pred.morphology.lower()
                best_matched = (
                    best is not None and target_morphology.lower() in best.morphology.lower()
                )
                better = False
                if best is None:
                    better = True
                elif matched and not best_matched:
                    better = True
                elif matched == best_matched and pred.free_energy_score < best.free_energy_score:
                    better = True
            else:
                better = best is None or pred.free_energy_score < best.free_energy_score

            if better:
                best = pred

        assert best is not None
        return SearchResult(best=best, history=history)
