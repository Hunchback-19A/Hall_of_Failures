# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Structured design requests. The file is JSON, including when named .inp."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from polymer_design.instrument.limits import max_candidates

SCHEMA = "polymer_design.request.v1"
SOLVERS = frozenset({"analytical", "phase_field", "scft", "pscf_rpc"})
CELLS = ("lam", "hex", "gyr", "bcc")
# Vendored example identity. These are the space groups in the example param
# files, not a result calculated for an arbitrary composition.
EXAMPLE_CELLS: dict[str, dict[str, str | int]] = {
    "lam": {"morphology": "lamellae", "dimension": 1, "lattice": "lamellar", "space_group": "P_-1"},
    "hex": {"morphology": "hexagonal cylinders", "dimension": 2, "lattice": "hexagonal", "space_group": "p_6_m_m"},
    "gyr": {"morphology": "gyroid", "dimension": 3, "lattice": "cubic", "space_group": "I_a_-3_d"},
    "bcc": {"morphology": "BCC spheres", "dimension": 3, "lattice": "cubic", "space_group": "I_m_-3_m"},
}
_REQUEST_KEYS = frozenset({
    "schema",
    "client",
    "request_id",
    "solver",
    "cells",
    "timeout_s",
    "candidates",
    "metadata",
    "keep_concentration",
})
_CANDIDATE_KEYS = frozenset({
    "id",
    "name",
    "architecture",
    "volume_fractions",
    "chi",
    "chiN",
    "degree_of_polymerization",
    "N",
})
_SUM_TOLERANCE = 1e-3


@dataclass
class CandidateSpec:
    id: str
    name: str
    architecture: str
    volume_fractions: list[float]
    chi: float
    degree_of_polymerization: float

    @property
    def chiN(self) -> float:
        return self.chi * self.degree_of_polymerization


@dataclass
class DesignRequest:
    client: str
    request_id: str
    solver: str
    cells: list[str]
    timeout_s: float
    candidates: list[CandidateSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    keep_concentration: bool = False


def load_request(path: Path) -> DesignRequest:
    """Load a JSON request. A .inp name is only a filename; the contents are JSON."""
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name} is not JSON. Design requests are JSON "
            "(a .inp suffix does not change the format)."
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("Design request must be a JSON object")
    return parse_request(payload)


def parse_request(payload: dict[str, Any]) -> DesignRequest:
    unknown = sorted(set(payload) - _REQUEST_KEYS)
    if unknown:
        raise ValueError(
            "Unrecognized request field(s): "
            + ", ".join(unknown)
            + ". Batch ceilings are not request fields. They live in run_limits.json "
            "or in POLYMER_DESIGN_MAX_CANDIDATES and "
            "POLYMER_DESIGN_MAX_VISUALIZATION_BATCH."
        )
    if "max_candidates" in payload:
        raise ValueError(
            "max_candidates cannot be set inside a request. "
            "Edit polymer_design/run_limits.json or set POLYMER_DESIGN_MAX_CANDIDATES."
        )
    client = str(payload.get("client", "human")).casefold()
    if client not in {"human", "ai"}:
        raise ValueError("client must be 'human' or 'ai'")
    solver = str(payload.get("solver", "")).strip()
    if solver not in SOLVERS:
        known = ", ".join(sorted(SOLVERS))
        raise ValueError(f"solver must be one of: {known}")
    cells = _cells(payload.get("cells"), solver)
    timeout_s = float(payload.get("timeout_s", 3600.0))
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("candidates must be a non-empty list")
    limit = max_candidates()
    if len(raw_candidates) > limit:
        raise ValueError(
            f"Request has {len(raw_candidates)} candidates; the limit is {limit}. "
            "The request was rejected and was not truncated."
        )
    keep_concentration = payload.get("keep_concentration", False)
    if not isinstance(keep_concentration, bool):
        raise ValueError("keep_concentration must be true or false")
    if keep_concentration and solver != "pscf_rpc":
        raise ValueError("keep_concentration is only valid when solver is pscf_rpc")
    request_id = str(payload.get("request_id") or "request")
    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    candidates = [
        _candidate(item, index, solver) for index, item in enumerate(raw_candidates, start=1)
    ]
    ids = [item.id for item in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate id values must be unique")
    return DesignRequest(
        client=client,
        request_id=request_id,
        solver=solver,
        cells=cells,
        timeout_s=timeout_s,
        candidates=candidates,
        metadata=dict(metadata),
        keep_concentration=keep_concentration,
    )


def _cells(raw: Any, solver: str) -> list[str]:
    if raw is None:
        return list(CELLS) if solver == "pscf_rpc" else []
    if solver != "pscf_rpc":
        raise ValueError("cells is used only when solver is pscf_rpc")
    if not isinstance(raw, list) or not raw:
        raise ValueError("cells must be a non-empty list of lam, hex, gyr, bcc")
    names = [str(item) for item in raw]
    unknown = [name for name in names if name not in CELLS]
    if unknown:
        raise ValueError(
            "Unknown cell(s): " + ", ".join(unknown) + ". Known: lam, hex, gyr, bcc."
        )
    if len(names) != len(set(names)):
        raise ValueError("cells must not repeat a morphology")
    return names


def _candidate(raw: Any, index: int, solver: str) -> CandidateSpec:
    if not isinstance(raw, dict):
        raise ValueError(f"Candidate {index} must be an object")
    unknown = sorted(set(raw) - _CANDIDATE_KEYS)
    if unknown:
        raise ValueError(
            f"Candidate {index} has unrecognized field(s): " + ", ".join(unknown)
        )
    architecture = str(raw.get("architecture", "")).strip().lower()
    if architecture not in {"diblock", "triblock"}:
        raise ValueError(f"Candidate {index} architecture must be diblock or triblock")
    if solver == "pscf_rpc" and architecture != "diblock":
        raise ValueError(
            f"Candidate {index} is {architecture}. pscf_rpc runs AB diblocks only."
        )
    fractions = raw.get("volume_fractions")
    if not isinstance(fractions, list) or not fractions:
        raise ValueError(f"Candidate {index} needs volume_fractions")
    try:
        values = [float(item) for item in fractions]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Candidate {index} volume_fractions must be numbers") from exc
    expected = 2 if architecture == "diblock" else 3
    if len(values) != expected:
        raise ValueError(
            f"Candidate {index} {architecture} needs {expected} volume fractions"
        )
    if solver == "pscf_rpc" and any(item <= 0.0 or item >= 1.0 for item in values):
        raise ValueError(
            f"Candidate {index} block fractions must lie strictly between 0 and 1"
        )
    total = sum(values)
    if abs(total - 1.0) > _SUM_TOLERANCE:
        raise ValueError(
            f"Candidate {index} volume_fractions sum to {total:.6g}, not 1. "
            "They were not rescaled."
        )
    chi, degree = _thermo(raw, index)
    identifier = str(raw.get("id") or f"candidate-{index:04d}")
    name = str(raw.get("name") or identifier)
    return CandidateSpec(
        id=identifier,
        name=name,
        architecture=architecture,
        volume_fractions=values,
        chi=chi,
        degree_of_polymerization=degree,
    )


def _thermo(raw: dict[str, Any], index: int) -> tuple[float, float]:
    has_chi = "chi" in raw
    has_chin = "chiN" in raw
    has_n = "degree_of_polymerization" in raw
    has_short_n = "N" in raw
    if has_n and has_short_n and float(raw["degree_of_polymerization"]) != float(raw["N"]):
        raise ValueError(
            f"Candidate {index} gives both N and degree_of_polymerization, and they differ"
        )
    if not has_n and not has_short_n:
        raise ValueError(f"Candidate {index} needs degree_of_polymerization (N)")
    degree = float(raw["degree_of_polymerization"] if has_n else raw["N"])
    if degree <= 0:
        raise ValueError(f"Candidate {index} degree_of_polymerization must be > 0")
    if not has_chi and not has_chin:
        raise ValueError(f"Candidate {index} needs chi or chiN. Neither was inferred.")
    if has_chi:
        chi = float(raw["chi"])
        if chi < 0:
            raise ValueError(f"Candidate {index} chi must be >= 0")
    else:
        chi = float(raw["chiN"]) / degree
    if has_chin:
        stated = float(raw["chiN"])
        product = chi * degree
        scale = max(1.0, abs(stated))
        if abs(product - stated) > 1e-6 * scale:
            raise ValueError(
                f"Candidate {index} chi and chiN disagree "
                f"(chi * N = {product:.6g}, chiN = {stated:.6g}). "
                "Neither value was changed."
            )
    return chi, degree
