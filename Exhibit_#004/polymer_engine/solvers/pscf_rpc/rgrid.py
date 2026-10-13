# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Read a PSCF real-space field file (.rf).

The reader does not decide whether the numbers are concentrations or
chemical-potential fields. The caller records that.
"""

from __future__ import annotations

from typing import Any


def parse_rgrid(text: str) -> dict[str, Any]:
    """Parse a PSCF r-grid file. Point order is Fortran: the first axis is fastest."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header: dict[str, Any] = {}
    index = 0
    mesh: list[int] | None = None
    while index < len(lines):
        line = lines[index]
        if line.startswith("format"):
            index += 1
            continue
        if line.startswith("mesh"):
            index += 1
            if index >= len(lines):
                raise ValueError("PSCF r-grid file has a mesh label and no dimensions")
            mesh = [int(part) for part in lines[index].split()]
            index += 1
            break
        if line.startswith("cell_param"):
            index += 1
            header["cell_parameters"] = [float(part) for part in lines[index].split()]
            index += 1
            continue
        key, value, index = _header_entry(lines, index)
        header[key] = value
    if mesh is None:
        raise ValueError("PSCF r-grid file has no mesh")
    n_monomer = int(header["N_monomer"])
    rows: list[list[float]] = []
    for line in lines[index:]:
        parts = [float(part) for part in line.split()]
        if len(parts) != n_monomer:
            raise ValueError(
                f"PSCF r-grid row has {len(parts)} values; N_monomer is {n_monomer}"
            )
        rows.append(parts)
    expected = 1
    for size in mesh:
        expected *= size
    if len(rows) != expected:
        raise ValueError(
            f"PSCF r-grid has {len(rows)} points; the mesh {mesh} requires {expected}"
        )
    return {
        "dimension": int(header["dim"]),
        "crystal_system": str(header["crystal_system"]),
        "cell_parameters": list(header.get("cell_parameters") or []),
        "space_group": str(header["group_name"]),
        "n_monomer": n_monomer,
        "mesh": mesh,
        "order": "fortran_first_index_fastest",
        "values": rows,
    }


def _header_entry(lines: list[str], index: int) -> tuple[str, str, int]:
    key = lines[index].split()[0]
    index += 1
    if index >= len(lines):
        raise ValueError(f"PSCF r-grid file ended after {key}")
    return key, lines[index].split()[0], index + 1
