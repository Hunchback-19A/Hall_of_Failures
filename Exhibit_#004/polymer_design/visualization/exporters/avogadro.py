# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Write a cube Avogadro 2 can show as the two blocks in the cell.

Avogadro draws a surface where a fromFile cube equals +0.025 and another
where it equals -0.025. One surface is the A-rich part of the fraction and
the other is the B-rich part. A lamellar fraction varies along one direction,
so that direction is repeated. A hexagonal packing is already drawn on its
lattice, with round tubes, and is not squared again. An illustrative BCC
lattice is repeated so several spheres sit in the cell.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from polymer_design.visualization.notes import EXPORTER_VERSION, VISUALIZATION_NOTE

# Gaussian-cube spacing is stored in bohr. Avogadro 2 multiplies by this factor.
_VIEW_STEP = 3.0
_BOHR_TO_ANGSTROM = 0.529177249
_CUBE_STEP = _VIEW_STEP / _BOHR_TO_ANGSTROM
# Surfaces::m_isoValue in Avogadro 2.0. A fromFile cube is meshed at both signs.
_SURFACE_LEVEL = 0.025
# Preferred distance from one half. A side that never reaches it is drawn further in.
_SHEET_FRACTION = 0.20
# Smallest share of the grid placed inside each surface, when that block exists.
_MIN_SIDE = 0.12
_LAYER_REPEATS = 3
_PACKING_REPEATS = 2
# Carbons along the cell edges. Avogadro frames the view on atoms, and a file
# with none leaves the camera inside a layer, which draws as an empty window.
_FRAME_ELEMENT = 6
_FRAME_SPACING = 1.5
_FRAME_PAD = 3.0


def write_avogadro_cjson(path: Path, morphology: dict[str, Any], provenance: dict[str, Any]) -> None:
    mesh, scalars = _viewer_field(morphology)
    points, elements, bonds, labels = _scene_atoms(mesh)
    # Avogadro 2.0 stops before the cube if elements.number is empty.
    document = {
        "chemicalJson": 1,
        "name": _name(morphology, provenance),
        "atoms": {
            "elements": {"number": elements},
            "coords": {"3d": [round(coord, 6) for point in points for coord in point]},
            "labels": labels,
        },
        "bonds": {
            "connections": {"index": [atom for pair in bonds for atom in pair]},
            "order": [1] * len(bonds),
        },
        "properties": {
            "totalCharge": 0,
            "morphologyVisualization": {
                "exporter": "polymer_design.visualization",
                "exporter_version": EXPORTER_VERSION,
                "format": "cjson",
                "density_source": morphology["density_source"],
                "representation_type": morphology["representation_type"],
                "warning": VISUALIZATION_NOTE,
                "note": morphology.get("note", ""),
                "provenance": provenance,
            }
        },
        "cube": {
            "name": _cube_name(morphology),
            "type": "fromFile",
            "origin": [0.0, 0.0, 0.0],
            "spacing": [_VIEW_STEP, _VIEW_STEP, _VIEW_STEP],
            "dimensions": mesh,
            "scalars": _surface_scalars(scalars),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _name(morphology: dict[str, Any], provenance: dict[str, Any]) -> str:
    morphology_name = provenance.get("morphology") or morphology.get("morphology") or "morphology"
    return (
        f"Coarse-grained {morphology_name} "
        f"({morphology['density_source']}). Not an atomistic structure."
    )


def write_gaussian_cube(path: Path, morphology: dict[str, Any], provenance: dict[str, Any]) -> None:
    """Gaussian cube of the two blocks, with the cell edges and a color legend."""
    mesh, scalars = _viewer_field(morphology)
    points, elements, _bonds, _labels = _scene_atoms(mesh)
    header = [
        _name(morphology, provenance),
        (
            "The atoms on the box are the cell edges. Outside the box, the red letter A is polymer A "
            "and the blue letter B is polymer B. One surface is the A-rich band and the other is the B-rich band. "
            "Not electron density. Not polymer atoms. "
            + VISUALIZATION_NOTE
        ),
        f"{len(points)}  0.000000  0.000000  0.000000",
        # Avogadro 2.0 reads these three axis lines before the atoms.
        f"{mesh[0]}  {_CUBE_STEP:.8f}  0.000000  0.000000",
        f"{mesh[1]}  0.000000  {_CUBE_STEP:.8f}  0.000000",
        f"{mesh[2]}  0.000000  0.000000  {_CUBE_STEP:.8f}",
    ]
    for element, (x_angstrom, y_angstrom, z_angstrom) in zip(elements, points):
        header.append(
            f"{element}  0.000000  "
            f"{x_angstrom / _BOHR_TO_ANGSTROM:.6f}  "
            f"{y_angstrom / _BOHR_TO_ANGSTROM:.6f}  "
            f"{z_angstrom / _BOHR_TO_ANGSTROM:.6f}"
        )
    # Avogadro's cube index is x * ny * nz + y * nz + z. z changes fastest.
    surface = _avogadro_cube_values(mesh, scalars)
    rows = []
    for start in range(0, len(surface), 6):
        rows.append(" ".join(f"{value:.8e}" for value in surface[start : start + 6]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(header + rows) + "\n", encoding="utf-8")


def _avogadro_cube_values(mesh: list[int], scalars: list[float]) -> list[float]:
    """Reorder x-fastest scalars into Avogadro's cube layout, z fastest."""
    nx, ny, nz = (int(size) for size in mesh)
    values = np.asarray(_surface_scalars(scalars), dtype=float).reshape((nz, ny, nx))
    return np.transpose(values, (2, 1, 0)).reshape(-1).tolist()


def _scalars(morphology: dict[str, Any]) -> list[float]:
    mesh = [int(size) for size in morphology["mesh"]]
    scalars = [float(value) for value in morphology["phi_a"]]
    expected = mesh[0] * mesh[1] * mesh[2]
    if len(scalars) != expected:
        raise ValueError(f"Morphology grid has {len(scalars)} values; the mesh needs {expected}")
    return scalars


def _viewer_field(morphology: dict[str, Any]) -> tuple[list[int], list[float]]:
    """Grid Avogadro surfaces. Repeat a simple pattern so the shape is visible."""
    nx, ny, nz = (int(size) for size in morphology["mesh"])
    phi = np.asarray(_scalars(morphology), dtype=float).reshape((nz, ny, nx))
    spans = (
        float(np.ptp(phi[nz // 2, ny // 2, :])),
        float(np.ptp(phi[nz // 2, :, nx // 2])),
        float(np.ptp(phi[:, ny // 2, nx // 2])),
    )
    if _already_hexagonal(morphology):
        return [nx, ny, nz], phi.reshape(-1).tolist()
    varying = [axis for axis, span in enumerate(spans) if span > 0.05]
    if len(varying) == 1:
        phi = _repeat(phi, varying, _LAYER_REPEATS, shift=True)
    elif len(varying) == 2:
        phi = _repeat(phi, varying, _PACKING_REPEATS, shift=True)
    elif len(varying) == 3 and _illustrative_bcc(morphology):
        phi = _repeat(phi, (0, 1, 2), _PACKING_REPEATS, shift=False)
    return [int(phi.shape[2]), int(phi.shape[1]), int(phi.shape[0])], phi.reshape(-1).tolist()


def _repeat(phi: np.ndarray, axes: tuple[int, ...] | list[int], copies: int, shift: bool) -> np.ndarray:
    for axis in axes:
        array_axis = 2 - axis
        if shift:
            phi = np.roll(phi, phi.shape[array_axis] // 8, axis=array_axis)
        phi = np.concatenate([phi] * copies, axis=array_axis)
    return phi


def _already_hexagonal(morphology: dict[str, Any]) -> bool:
    if str(morphology.get("crystal_system") or "").casefold() == "hexagonal":
        return True
    return "hexagonal" in str(morphology.get("morphology") or "").casefold()


def _illustrative_bcc(morphology: dict[str, Any]) -> bool:
    if morphology.get("density_source") != "illustrative":
        return False
    return "bcc" in str(morphology.get("morphology") or "").casefold()


def _surface_scalars(phi_a: list[float]) -> list[float]:
    """Scale so Avogadro's ±0.025 surfaces bound the A-rich and B-rich parts.

    A strong field is cut at one half ± 0.20. A block that never reaches that
    far is cut closer to one half, so its surface still encloses part of the grid.
    """
    if not phi_a:
        return []
    values = np.asarray(phi_a, dtype=float)
    pos_span = _visible_cut(values, lower=False) - 0.5
    neg_span = 0.5 - _visible_cut(values, lower=True)
    scaled = np.empty(values.shape, dtype=float)
    above = values >= 0.5
    scaled[above] = 0.0 if pos_span <= 1e-12 else (values[above] - 0.5) / pos_span * _SURFACE_LEVEL
    scaled[~above] = 0.0 if neg_span <= 1e-12 else (values[~above] - 0.5) / neg_span * _SURFACE_LEVEL
    return [round(float(item), 8) for item in scaled]


def _visible_cut(values: np.ndarray, *, lower: bool) -> float:
    """Fraction where one surface sits. Stays on that block's side of one half."""
    default = 0.5 - _SHEET_FRACTION if lower else 0.5 + _SHEET_FRACTION
    beyond = float(np.mean(values < default) if lower else np.mean(values > default))
    if beyond >= _MIN_SIDE:
        return default
    side = values[values < 0.5] if lower else values[values > 0.5]
    if side.size == 0:
        return 0.5
    level = float(np.quantile(values, _MIN_SIDE if lower else 1.0 - _MIN_SIDE))
    if lower:
        return float(np.max(side) if level >= 0.5 else level)
    return float(np.min(side) if level <= 0.5 else level)


def _scene_atoms(
    mesh: list[int],
) -> tuple[list[tuple[float, float, float]], list[int], list[tuple[int, int]], list[str]]:
    """Cell-edge carbons, plus a red A and a blue B above the box."""
    points, bonds = _cell_frame(mesh)
    elements = [_FRAME_ELEMENT] * len(points)
    labels = ["Cell edge. Not a polymer atom."] * len(points)
    extra_points, extra_elements, extra_bonds, extra_labels = _color_legend(mesh, len(points))
    return points + extra_points, elements + extra_elements, bonds + extra_bonds, labels + extra_labels


def _color_legend(
    mesh: list[int], index0: int
) -> tuple[list[tuple[float, float, float]], list[int], list[tuple[int, int]], list[str]]:
    """Letters Avogadro can draw. The cube format has no text legend."""
    span_y = (mesh[1] - 1) * _VIEW_STEP
    span_z = (mesh[2] - 1) * _VIEW_STEP
    origin_y = span_y + _FRAME_PAD + 8.0
    origin_z = span_z / 2.0
    # Oxygen is red and nitrogen is blue in Avogadro's default atom colors.
    letters = (
        (_LETTER_A, 8, "Polymer A. Not a polymer atom.", 0.0),
        (_LETTER_B, 7, "Polymer B. Not a polymer atom.", 16.0),
    )
    points: list[tuple[float, float, float]] = []
    elements: list[int] = []
    bonds: list[tuple[int, int]] = []
    labels: list[str] = []
    for strokes, element, label, origin_x in letters:
        for stroke in strokes:
            ids = []
            for x_local, y_local in _sample_stroke(stroke):
                point = (origin_x + x_local, origin_y + y_local, origin_z)
                ids.append(index0 + len(points))
                points.append(tuple(round(value, 5) for value in point))
                elements.append(element)
                labels.append(label)
            bonds.extend(pair for pair in zip(ids, ids[1:]) if pair[0] != pair[1])
    return points, elements, bonds, labels


def _sample_stroke(stroke: tuple[tuple[float, float], ...]) -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []
    for start, end in zip(stroke, stroke[1:]):
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        steps = max(1, int(round(length / _LEGEND_SPACING)))
        for step in range(steps):
            weight = step / steps
            samples.append(
                (
                    start[0] + (end[0] - start[0]) * weight,
                    start[1] + (end[1] - start[1]) * weight,
                )
            )
    samples.append(stroke[-1])
    return samples


# Strokes in angstroms. Spacing stays inside Avogadro's bond cutoff, so each letter holds together.
_LEGEND_SPACING = 1.5
_LETTER_A = (
    ((0.0, 0.0), (4.5, 12.0)),
    ((9.0, 0.0), (4.5, 12.0)),
    ((2.2, 4.5), (6.8, 4.5)),
)
_LETTER_B = (
    ((0.0, 0.0), (0.0, 12.0)),
    ((0.0, 12.0), (5.5, 12.0), (7.0, 9.0), (5.5, 6.0), (0.0, 6.0)),
    ((0.0, 6.0), (6.0, 6.0), (7.5, 3.0), (6.0, 0.0), (0.0, 0.0)),
)


def _cell_frame(mesh: list[int]) -> tuple[list[tuple[float, float, float]], list[tuple[int, int]]]:
    """Carbons on the twelve edges of the cell, in angstroms, plus the bonds along those edges."""
    span = [(count - 1) * _VIEW_STEP for count in mesh]
    corners = [
        (x, y, z)
        for x in (-_FRAME_PAD, span[0] + _FRAME_PAD)
        for y in (-_FRAME_PAD, span[1] + _FRAME_PAD)
        for z in (-_FRAME_PAD, span[2] + _FRAME_PAD)
    ]
    edges = [
        (a, b)
        for i, a in enumerate(corners)
        for b in corners[i + 1 :]
        if sum(abs(a[axis] - b[axis]) > 1e-9 for axis in range(3)) == 1
    ]
    points: list[tuple[float, float, float]] = []
    index: dict[tuple[float, float, float], int] = {}
    bonds: list[tuple[int, int]] = []

    def add(point: tuple[float, float, float]) -> int:
        key = tuple(round(value, 5) for value in point)
        if key not in index:
            index[key] = len(points)
            points.append(key)
        return index[key]

    for start, end in edges:
        length = math.dist(start, end)
        steps = max(1, int(round(length / _FRAME_SPACING)))
        ids = [
            add(tuple(start[axis] + (end[axis] - start[axis]) * step / steps for axis in range(3)))
            for step in range(steps + 1)
        ]
        bonds.extend(pair for pair in zip(ids, ids[1:]) if pair[0] != pair[1])
    return points, bonds


def _cube_name(morphology: dict[str, Any]) -> str:
    return (
        "Coarse-grained A-block fraction. "
        "One surface is the A-rich band and the other is the B-rich band. "
        f"Source: {morphology['density_source']}. Not electron density."
    )
