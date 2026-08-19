"""Common simulation input/output contracts for polymer solvers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationInput:
    """
    Shared input for analytical and numerical polymer solvers.

    Polymer parameters are intentionally explicit and transparent.
    """

    name: str = "unnamed"
    architecture: str = "diblock"
    volume_fractions: list[float] = field(default_factory=lambda: [0.5, 0.5])
    chi: float = 0.05
    degree_of_polymerization: float = 100.0
    # Reproducibility / numerical settings (used by numerical solvers)
    n_grid: int = 64
    timestep: float = 1.0e-3
    n_iterations: int = 2000
    random_seed: int = 0
    box_length: float = 1.0
    # Extra method-specific knobs
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def chiN(self) -> float:
        return self.chi * self.degree_of_polymerization

    @property
    def f_minor(self) -> float:
        return min(self.volume_fractions) if self.volume_fractions else 0.5

    def validate(self) -> None:
        if self.architecture.lower() not in {"diblock", "triblock"}:
            raise ValueError("architecture must be diblock or triblock")
        if len(self.volume_fractions) < 2:
            raise ValueError("volume_fractions needs at least two entries")
        total = sum(self.volume_fractions)
        if abs(total - 1.0) > 1e-3:
            raise ValueError(f"volume_fractions must sum to 1 (got {total})")
        if self.chi < 0:
            raise ValueError("chi must be >= 0")
        if self.degree_of_polymerization <= 0:
            raise ValueError("degree_of_polymerization must be > 0")
        if self.n_grid < 8:
            raise ValueError("n_grid must be >= 8")
        if self.timestep <= 0:
            raise ValueError("timestep must be > 0")
        if self.n_iterations < 1:
            raise ValueError("n_iterations must be >= 1")
        if self.box_length <= 0:
            raise ValueError("box_length must be > 0")


@dataclass
class SimulationOutput:
    """
    Shared output schema.

    Numerical method details and convergence info are first-class fields so
    results stay auditable (GAMESS-like transparency).
    """

    solver_name: str
    morphology: str
    energy: float
    chiN: float
    structure: dict[str, Any] = field(default_factory=dict)
    convergence: dict[str, Any] = field(default_factory=dict)
    method_details: dict[str, Any] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    success: bool = True

    def summary_lines(self) -> list[str]:
        lines = [
            "=" * 64,
            f"Simulation output [{self.solver_name}]",
            "=" * 64,
            f"Morphology: {self.morphology}",
            f"Energy: {self.energy:.6g}",
            f"χN: {self.chiN:.4g}",
            f"Success: {self.success}",
            "",
            "Method details:",
        ]
        for k, v in self.method_details.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("Convergence:")
        for k, v in self.convergence.items():
            lines.append(f"  {k}: {v}")
        if self.structure:
            lines.append("")
            lines.append("Structure:")
            for k, v in self.structure.items():
                if isinstance(v, list) and len(v) > 8:
                    lines.append(f"  {k}: list[{len(v)}] (truncated)")
                else:
                    lines.append(f"  {k}: {v}")
        if self.assumptions:
            lines.append("")
            lines.append("Assumptions:")
            for a in self.assumptions:
                lines.append(f"  - {a}")
        if self.notes:
            lines.append("")
            lines.append("Notes:")
            for n in self.notes:
                lines.append(f"  - {n}")
        lines.append("=" * 64)
        return lines

    def format(self) -> str:
        return "\n".join(self.summary_lines())


class Solver(ABC):
    """Base class for polymer physics solvers."""

    name: str = "solver"

    @abstractmethod
    def solve(self, sim_input: SimulationInput) -> SimulationOutput:
        raise NotImplementedError
