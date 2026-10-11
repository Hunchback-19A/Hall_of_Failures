"""Design target representation for inverse exploration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DesignTarget:
    """
    Target specification for design exploration.

    Only currently supported engine parameters are allowed as constraints:
    morphology, domain spacing, architecture, N, f, and χ / χN-related bounds.
    """

    morphology: str | None = None
    domain_spacing_nm: float | None = None
    temperature_K: float | None = None
    architecture: str | None = "diblock"
    # Composition / chain-length constraints
    f_min: float = 0.10
    f_max: float = 0.50
    N_min: float = 80.0
    N_max: float = 300.0
    # χ-related constraints (optional)
    chi: float | None = None  # if set, use this constant χ for all grid candidates
    chi_min: float | None = None
    chi_max: float | None = None
    chiN_min: float | None = None
    chiN_max: float | None = None
    # Optional chemistry filters (monomer keys / aliases)
    block_a: str | None = None
    block_b: str | None = None
    # Ranking weights (educational defaults; higher score is better)
    weight_morphology: float = 4.0
    weight_spacing: float = 2.0
    weight_thermodynamics: float = 1.0
    weight_confidence: float = 1.0
    top_k: int = 5

    def validate(self) -> None:
        if self.architecture is not None:
            arch = self.architecture.lower().strip()
            if arch not in {"diblock", "triblock"}:
                raise ValueError("architecture must be 'diblock' or 'triblock'")
            self.architecture = arch
        if not (0.0 < self.f_min <= self.f_max <= 0.5):
            raise ValueError("Require 0 < f_min <= f_max <= 0.5 (minority fraction window)")
        if not (0.0 < self.N_min <= self.N_max):
            raise ValueError("Require 0 < N_min <= N_max")
        if self.domain_spacing_nm is not None and self.domain_spacing_nm <= 0:
            raise ValueError("domain_spacing_nm must be > 0")
        if self.temperature_K is not None and self.temperature_K <= 0:
            raise ValueError("temperature_K must be > 0")
        if self.chi is not None and self.chi < 0:
            raise ValueError("chi must be >= 0")
        if self.chi_min is not None and self.chi_max is not None and self.chi_min > self.chi_max:
            raise ValueError("chi_min must be <= chi_max")
        if self.chiN_min is not None and self.chiN_max is not None and self.chiN_min > self.chiN_max:
            raise ValueError("chiN_min must be <= chiN_max")
        if self.top_k < 1:
            raise ValueError("top_k must be >= 1")
        for name, w in (
            ("weight_morphology", self.weight_morphology),
            ("weight_spacing", self.weight_spacing),
            ("weight_thermodynamics", self.weight_thermodynamics),
            ("weight_confidence", self.weight_confidence),
        ):
            if w < 0:
                raise ValueError(f"{name} must be >= 0")

    def summary_lines(self) -> list[str]:
        lines = ["Design target:"]
        lines.append(f"  morphology: {self.morphology or '(any)'}")
        lines.append(
            f"  domain spacing: {self.domain_spacing_nm:.3g} nm"
            if self.domain_spacing_nm is not None
            else "  domain spacing: (any)"
        )
        lines.append(f"  architecture: {self.architecture or '(any)'}")
        lines.append(f"  f_minor in [{self.f_min:.3g}, {self.f_max:.3g}]")
        lines.append(f"  N in [{self.N_min:.3g}, {self.N_max:.3g}]")
        if self.temperature_K is not None:
            lines.append(f"  temperature: {self.temperature_K:.3g} K")
        if self.chi is not None:
            lines.append(f"  χ (fixed for grid): {self.chi:.4g}")
        if self.chi_min is not None or self.chi_max is not None:
            lines.append(f"  χ bounds: [{self.chi_min}, {self.chi_max}]")
        if self.chiN_min is not None or self.chiN_max is not None:
            lines.append(f"  χN bounds: [{self.chiN_min}, {self.chiN_max}]")
        if self.block_a or self.block_b:
            lines.append(f"  chemistry filter: A={self.block_a or '*'}, B={self.block_b or '*'}")
        return lines
