"""
Particle swarm optimization skeleton.

Architecture lesson from PSO + SCFT inverse-design literature:
  keep the optimizer independent of the simulator; particles propose candidates,
  an external scoring function returns fitness.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from ..evaluator import Prediction
from ..polymer import Block, Polymer
from .random_search import SearchResult


@dataclass
class Particle:
    # Design variables: [f_A, N]
    position: list[float]
    velocity: list[float]
    best_position: list[float]
    best_score: float


class ParticleSwarmOptimizer:
    """Minimal PSO over (f, N) for a fixed χ and chemistry pair."""

    def __init__(
        self,
        evaluate_fn: Callable[[Polymer], Prediction],
        block_a: str = "styrene",
        block_b: str = "MMA",
        chi: float = 0.04,
        f_bounds: tuple[float, float] = (0.1, 0.5),
        N_bounds: tuple[float, float] = (50.0, 400.0),
        swarm_size: int = 12,
        w: float = 0.6,
        c1: float = 1.4,
        c2: float = 1.4,
        seed: int | None = None,
    ) -> None:
        self.evaluate_fn = evaluate_fn
        self.block_a = block_a
        self.block_b = block_b
        self.chi = chi
        self.f_bounds = f_bounds
        self.N_bounds = N_bounds
        self.swarm_size = swarm_size
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.rng = random.Random(seed)

    def _clip(self, pos: list[float]) -> list[float]:
        f = min(max(pos[0], self.f_bounds[0]), self.f_bounds[1])
        N = min(max(pos[1], self.N_bounds[0]), self.N_bounds[1])
        return [f, N]

    def _polymer_from_position(self, pos: list[float], tag: str) -> Polymer:
        f, N = pos
        return Polymer(
            name=tag,
            architecture="diblock",
            blocks=[Block(self.block_a, f), Block(self.block_b, 1.0 - f)],
            chi=self.chi,
            degree_of_polymerization=N,
        )

    def _score(self, pred: Prediction, target_morphology: str | None) -> float:
        score = pred.free_energy_score
        if target_morphology is not None:
            if target_morphology.lower() not in pred.morphology.lower():
                score += 50.0
        return score

    def run(
        self,
        iterations: int = 15,
        target_morphology: str | None = None,
    ) -> SearchResult:
        particles: list[Particle] = []
        history: list[Prediction] = []

        global_best_pos: list[float] | None = None
        global_best_score = float("inf")
        global_best_pred: Prediction | None = None

        for i in range(self.swarm_size):
            pos = [
                self.rng.uniform(*self.f_bounds),
                self.rng.uniform(*self.N_bounds),
            ]
            vel = [
                self.rng.uniform(-0.05, 0.05),
                self.rng.uniform(-20.0, 20.0),
            ]
            pred = self.evaluate_fn(self._polymer_from_position(pos, f"pso-init-{i}"))
            history.append(pred)
            score = self._score(pred, target_morphology)
            particles.append(
                Particle(
                    position=pos,
                    velocity=vel,
                    best_position=list(pos),
                    best_score=score,
                )
            )
            if score < global_best_score:
                global_best_score = score
                global_best_pos = list(pos)
                global_best_pred = pred

        assert global_best_pos is not None and global_best_pred is not None

        for it in range(iterations):
            for i, particle in enumerate(particles):
                for d in range(2):
                    r1 = self.rng.random()
                    r2 = self.rng.random()
                    particle.velocity[d] = (
                        self.w * particle.velocity[d]
                        + self.c1 * r1 * (particle.best_position[d] - particle.position[d])
                        + self.c2 * r2 * (global_best_pos[d] - particle.position[d])
                    )
                particle.position = self._clip(
                    [
                        particle.position[0] + particle.velocity[0],
                        particle.position[1] + particle.velocity[1],
                    ]
                )
                pred = self.evaluate_fn(
                    self._polymer_from_position(particle.position, f"pso-{it}-{i}")
                )
                history.append(pred)
                score = self._score(pred, target_morphology)
                if score < particle.best_score:
                    particle.best_score = score
                    particle.best_position = list(particle.position)
                if score < global_best_score:
                    global_best_score = score
                    global_best_pos = list(particle.position)
                    global_best_pred = pred

        return SearchResult(best=global_best_pred, history=history)
