"""
Benchmark case schema for morphology validation.

References are optional metadata only. This package never scrapes the web or
invents citations — leave `references` empty unless you add real sources by hand.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from polymer_design.polymer import Block, Polymer


@dataclass
class BenchmarkCase:
    """One polymer benchmark with an expected morphology label."""

    name: str
    polymer: Polymer
    expected_morphology: str
    approximate_composition: str
    experimental_notes: str = ""
    references: list[dict[str, Any]] = field(default_factory=list)
    source_path: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def validate_metadata(self) -> None:
        if not self.expected_morphology.strip():
            raise ValueError(f"Benchmark '{self.name}' missing expected.morphology")
        for ref in self.references:
            if not isinstance(ref, dict):
                raise ValueError(
                    f"Benchmark '{self.name}': each reference must be a dict "
                    "(e.g. citation keys you supply yourself)."
                )


def load_benchmark(path: str | Path) -> BenchmarkCase:
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    if "name" not in data or "expected" not in data:
        raise ValueError(f"{path}: benchmark requires 'name' and 'expected'")

    expected = data["expected"]
    if not isinstance(expected, dict) or "morphology" not in expected:
        raise ValueError(f"{path}: expected.morphology is required")

    params = data.get("parameters", {})
    polymer = Polymer(
        name=data["name"],
        architecture=data.get("architecture", "diblock"),
        blocks=[
            Block(name=b["name"], fraction=float(b["fraction"])) for b in data["blocks"]
        ],
        chi=float(params["chi"]) if params.get("chi") is not None else None,
        degree_of_polymerization=float(params.get("degree_of_polymerization", 100)),
        temperature_K=(
            float(params["temperature"]) if params.get("temperature") is not None else None
        ),
        chi_model_spec=(
            dict(params["chi_model"]) if isinstance(params.get("chi_model"), dict) else None
        ),
    )
    polymer.validate()

    case = BenchmarkCase(
        name=data["name"],
        polymer=polymer,
        expected_morphology=str(expected["morphology"]).strip().lower(),
        approximate_composition=str(
            expected.get("approximate_composition", polymer.composition_summary())
        ),
        experimental_notes=str(data.get("experimental_notes", "")),
        references=list(data.get("references", [])),
        source_path=path,
        raw=data,
    )
    case.validate_metadata()
    return case


def load_benchmark_dir(directory: str | Path) -> list[BenchmarkCase]:
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Benchmark directory not found: {directory}")

    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"No benchmark JSON files in {directory}")

    return [load_benchmark(p) for p in paths]
