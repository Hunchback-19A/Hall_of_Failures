"""
Monte Carlo Tree Search skeleton for hierarchical polymer design.

Architecture lesson from MCTS copolymer inverse-design work:
  grow a decision tree over design choices; evaluate leaf candidates with an
  external simulator/scoring function. Chemistry stays outside the search kernel.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable

from ..evaluator import Prediction
from ..polymer import Block, Polymer
from .random_search import SearchResult


@dataclass
class DesignNode:
    """Node in a simple design tree over discretized f bins."""

    f_value: float | None
    visits: int = 0
    total_reward: float = 0.0
    children: list[DesignNode] = field(default_factory=list)
    untried: list[float] = field(default_factory=list)

    @property
    def mean_reward(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits


class MonteCarloTreeSearch:
    """
    Very small MCTS over minority fraction choices at fixed χ and N.

    This is a framework demo, not a production materials-discovery solver.
    """

    def __init__(
        self,
        evaluate_fn: Callable[[Polymer], Prediction],
        block_a: str = "styrene",
        block_b: str = "MMA",
        chi: float = 0.05,
        N: float = 200.0,
        f_choices: list[float] | None = None,
        exploration: float = 1.2,
        seed: int | None = None,
    ) -> None:
        self.evaluate_fn = evaluate_fn
        self.block_a = block_a
        self.block_b = block_b
        self.chi = chi
        self.N = N
        self.f_choices = f_choices or [0.12, 0.20, 0.28, 0.35, 0.42, 0.50]
        self.exploration = exploration
        self.rng = random.Random(seed)

    def _polymer(self, f: float, tag: str) -> Polymer:
        return Polymer(
            name=tag,
            architecture="diblock",
            blocks=[Block(self.block_a, f), Block(self.block_b, 1.0 - f)],
            chi=self.chi,
            degree_of_polymerization=self.N,
        )

    def _reward(self, pred: Prediction, target_morphology: str | None) -> float:
        # Higher is better inside UCT; convert proxy score accordingly.
        reward = -pred.free_energy_score
        if target_morphology is not None and target_morphology.lower() in pred.morphology.lower():
            reward += 20.0
        return reward

    def _uct(self, parent: DesignNode, child: DesignNode) -> float:
        if child.visits == 0:
            return float("inf")
        exploit = child.mean_reward
        explore = self.exploration * math.sqrt(math.log(parent.visits + 1) / child.visits)
        return exploit + explore

    def run(
        self,
        iterations: int = 30,
        target_morphology: str | None = None,
    ) -> SearchResult:
        root = DesignNode(f_value=None, untried=list(self.f_choices))
        history: list[Prediction] = []
        best_pred: Prediction | None = None
        best_reward = float("-inf")

        for i in range(iterations):
            node = root
            # Selection / expansion over first-level f choices.
            if node.untried:
                f = node.untried.pop(self.rng.randrange(len(node.untried)))
                child = DesignNode(f_value=f)
                node.children.append(child)
                node = child
            elif node.children:
                node = max(node.children, key=lambda c: self._uct(root, c))
            else:
                break

            assert node.f_value is not None
            pred = self.evaluate_fn(self._polymer(node.f_value, f"mcts-{i}"))
            history.append(pred)
            reward = self._reward(pred, target_morphology)

            # Backup
            node.visits += 1
            node.total_reward += reward
            root.visits += 1
            root.total_reward += reward

            if reward > best_reward:
                best_reward = reward
                best_pred = pred

        assert best_pred is not None
        return SearchResult(best=best_pred, history=history)
