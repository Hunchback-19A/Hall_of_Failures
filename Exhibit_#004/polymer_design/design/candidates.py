"""
Candidate generation from local monomer definitions.

Primary method: enumerate a small grid over monomer pairs, f, and N.
No literature database and no web search.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from polymer_engine.thermodynamics.chi_models import SolubilityParameterChiModel

from polymer_design.design.target import DesignTarget
from polymer_design.polymer import Block, Polymer, load_monomers


@dataclass
class GeneratedCandidate:
    polymer: Polymer
    method: str
    assumptions: list[str]


class CandidateGridGenerator:
    """Build diblock candidates from monomers.json via a discrete grid."""

    def __init__(
        self,
        monomers_path: str | Path,
        f_values: list[float] | None = None,
        N_values: list[float] | None = None,
    ) -> None:
        self.monomers_path = Path(monomers_path)
        self.monomer_index = load_monomers(self.monomers_path)
        raw = json.loads(self.monomers_path.read_text(encoding="utf-8"))
        self.monomer_keys = sorted(raw.keys())
        self.f_values = f_values or [0.15, 0.25, 0.35, 0.45, 0.50]
        self.N_values = N_values or [100.0, 150.0, 200.0, 300.0]

    def _resolve_key(self, name: str | None) -> str | None:
        if name is None:
            return None
        hit = self.monomer_index.get(name.lower())
        if hit is None:
            raise ValueError(f"Unknown monomer '{name}' (not in monomers.json)")
        return str(hit["key"])

    def _estimate_chi(self, key_a: str, key_b: str, temperature_K: float | None) -> float:
        a = self.monomer_index[key_a.lower()]
        b = self.monomer_index[key_b.lower()]
        v_ref = 0.5 * (
            float(a["molar_volume_cm3_mol"]) + float(b["molar_volume_cm3_mol"])
        )
        model = SolubilityParameterChiModel(
            delta_a=float(a["solubility_parameter_MPa05"]),
            delta_b=float(b["solubility_parameter_MPa05"]),
            molar_volume_cm3_mol=v_ref,
            polymer_A=key_a,
            polymer_B=key_b,
            default_temperature_K=temperature_K if temperature_K is not None else 298.15,
        )
        return model.evaluate(temperature_K).chi

    def generate(self, target: DesignTarget) -> list[GeneratedCandidate]:
        target.validate()
        if target.architecture not in (None, "diblock"):
            raise ValueError(
                "CandidateGridGenerator currently supports architecture='diblock' only."
            )

        filter_a = self._resolve_key(target.block_a)
        filter_b = self._resolve_key(target.block_b)

        pairs: list[tuple[str, str]] = []
        for i, ka in enumerate(self.monomer_keys):
            for kb in self.monomer_keys[i + 1 :]:
                if filter_a and ka != filter_a and kb != filter_a:
                    continue
                if filter_b and ka != filter_b and kb != filter_b:
                    continue
                if filter_a and filter_b and {ka, kb} != {filter_a, filter_b}:
                    continue
                pairs.append((ka, kb))

        f_grid = [f for f in self.f_values if target.f_min - 1e-12 <= f <= target.f_max + 1e-12]
        N_grid = [N for N in self.N_values if target.N_min - 1e-12 <= N <= target.N_max + 1e-12]
        if not f_grid or not N_grid:
            return []

        assumptions = [
            "Candidates are generated from a local monomer grid (monomers.json), not a literature DB.",
            "χ is estimated from solubility parameters unless later overridden.",
            "Only diblock architectures are enumerated in this Phase 6 generator.",
            "This is design exploration, not claimed global optimization.",
        ]

        out: list[GeneratedCandidate] = []
        for ka, kb in pairs:
            if target.chi is not None:
                chi = float(target.chi)
                chi_method = "user-specified constant χ"
            else:
                chi = self._estimate_chi(ka, kb, target.temperature_K)
                chi_method = "solubility-parameter χ"
            if target.chi_min is not None and chi < target.chi_min:
                continue
            if target.chi_max is not None and chi > target.chi_max:
                continue
            for f in f_grid:
                for N in N_grid:
                    chiN = chi * N
                    if target.chiN_min is not None and chiN < target.chiN_min:
                        continue
                    if target.chiN_max is not None and chiN > target.chiN_max:
                        continue
                    polymer = Polymer(
                        name=f"{ka}-b-{kb}_f{f:.2f}_N{N:.0f}",
                        architecture="diblock",
                        blocks=[Block(ka, f), Block(kb, 1.0 - f)],
                        chi=chi,
                        degree_of_polymerization=N,
                        temperature_K=target.temperature_K,
                    )
                    out.append(
                        GeneratedCandidate(
                            polymer=polymer,
                            method=f"local monomer grid + {chi_method}",
                            assumptions=list(assumptions)
                            + ([f"Using fixed χ = {chi:.4g} for all candidates."] if target.chi is not None else []),
                        )
                    )
        return out
