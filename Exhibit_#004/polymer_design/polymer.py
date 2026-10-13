"""Polymer representation and JSON loading."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Block:
    name: str
    fraction: float

    def validate(self) -> None:
        if self.fraction <= 0.0:
            raise ValueError(f"Block '{self.name}' fraction must be > 0, got {self.fraction}")


@dataclass
class Polymer:
    """Chemically meaningful polymer description for the prototype."""

    name: str
    architecture: str
    blocks: list[Block]
    chi: float | None = None
    degree_of_polymerization: float = 100.0
    temperature_K: float | None = None
    chi_model_spec: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    SUPPORTED_ARCHITECTURES = ("diblock", "triblock")

    def validate(self) -> None:
        arch = self.architecture.lower().strip()
        if arch not in self.SUPPORTED_ARCHITECTURES:
            raise ValueError(
                f"Unsupported architecture '{self.architecture}'. "
                f"Supported: {', '.join(self.SUPPORTED_ARCHITECTURES)}"
            )
        if len(self.blocks) < 2:
            raise ValueError("A block copolymer needs at least two blocks.")
        if arch == "diblock" and len(self.blocks) != 2:
            raise ValueError("Diblock architecture expects exactly two blocks.")
        if arch == "triblock" and len(self.blocks) != 3:
            raise ValueError("Triblock architecture expects exactly three blocks.")
        for block in self.blocks:
            block.validate()
        total = sum(b.fraction for b in self.blocks)
        if abs(total - 1.0) > 1e-3:
            raise ValueError(f"Block fractions must sum to 1.0 (got {total:.4f})")
        if self.degree_of_polymerization <= 0:
            raise ValueError("degree_of_polymerization must be > 0")
        if self.chi is not None and self.chi < 0:
            raise ValueError("chi must be >= 0")
        if self.temperature_K is not None and self.temperature_K <= 0:
            raise ValueError("temperature_K must be > 0")

    @property
    def volume_fractions(self) -> list[float]:
        return [b.fraction for b in self.blocks]

    @property
    def block_names(self) -> list[str]:
        return [b.name for b in self.blocks]

    def minority_fraction(self) -> float:
        """Smallest contiguous composition used for morphology mapping."""
        if self.architecture.lower() == "triblock":
            # Map ABA-like end blocks as one chemical type when identical.
            ends = self.blocks[0].fraction + self.blocks[2].fraction
            mid = self.blocks[1].fraction
            return min(ends, mid)
        return min(self.volume_fractions)

    def composition_summary(self) -> str:
        parts = [f"{b.name} ({b.fraction:.3f})" for b in self.blocks]
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "chi": self.chi,
            "degree_of_polymerization": self.degree_of_polymerization,
        }
        if self.temperature_K is not None:
            params["temperature"] = self.temperature_K
        if self.chi_model_spec is not None:
            params["chi_model"] = self.chi_model_spec
        return {
            "name": self.name,
            "architecture": self.architecture,
            "blocks": [{"name": b.name, "fraction": b.fraction} for b in self.blocks],
            "parameters": params,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Polymer:
        params = data.get("parameters", {})
        temperature = params.get("temperature", params.get("temperature_K"))
        chi_model = params.get("chi_model")
        polymer = cls(
            name=data["name"],
            architecture=data["architecture"],
            blocks=[Block(name=b["name"], fraction=float(b["fraction"])) for b in data["blocks"]],
            chi=float(params["chi"]) if params.get("chi") is not None else None,
            degree_of_polymerization=float(params.get("degree_of_polymerization", 100)),
            temperature_K=float(temperature) if temperature is not None else None,
            chi_model_spec=dict(chi_model) if isinstance(chi_model, dict) else None,
            metadata={
                k: v
                for k, v in data.items()
                if k not in {"name", "architecture", "blocks", "parameters"}
            },
        )
        polymer.validate()
        return polymer


def load_monomers(path: str | Path) -> dict[str, dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    index: dict[str, dict[str, Any]] = {}
    for key, entry in raw.items():
        record = dict(entry)
        record["key"] = key
        index[key.lower()] = record
        for alias in entry.get("aliases", []):
            index[str(alias).lower()] = record
    return index


def load_polymers(path: str | Path) -> list[Polymer]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if isinstance(raw, dict):
        raw = [raw]
    return [Polymer.from_dict(item) for item in raw]


def load_polymer_file(path: str | Path) -> Polymer | list[Polymer]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if isinstance(raw, list):
        return [Polymer.from_dict(item) for item in raw]
    return Polymer.from_dict(raw)
