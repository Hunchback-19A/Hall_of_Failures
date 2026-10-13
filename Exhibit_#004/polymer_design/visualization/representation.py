# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Morphology grids. Avogadro is not involved here."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from polymer_design.visualization.notes import MORPHOLOGY_SCHEMA, VISUALIZATION_NOTE

_KINDS = {
    "lamellae": "lam",
    "hexagonal cylinders": "hex",
    "gyroid": "gyr",
    "bcc spheres": "bcc",
    "lam": "lam",
    "hex": "hex",
    "gyr": "gyr",
    "bcc": "bcc",
}


def morphology_kind(name: str) -> str | None:
    return _KINDS.get(str(name).strip().casefold()) or _KINDS.get(str(name).strip())


def display_from_pscf(field: dict[str, Any]) -> dict[str, Any]:
    """Turn a stored PSCF concentration grid into a 3D picture grid.

    A 3D PSCF mesh is used as calculated. A 1D mesh is repeated along the
    missing axes. A hexagonal 2D mesh is resampled onto its lattice vectors.
    Any other 2D mesh is repeated along z. Those viewing axes are marked
    derived_from_pscf.
    """
    mesh = [int(size) for size in field["mesh"]]
    values = field["values"]
    phi_a = [row[0] for row in values]
    dimension = len(mesh)
    if dimension == 3:
        grid = phi_a
        shape = mesh
        source = "pscf_calculated"
        note = "The cube is the PSCF monomer-0 concentration on its own mesh."
    elif dimension == 2 and str(field.get("crystal_system") or "").casefold() == "hexagonal":
        grid, shape = _embed_hexagonal_mesh(phi_a, mesh, field.get("cell_parameters") or [])
        source = "derived_from_pscf"
        note = (
            "PSCF computed this cell on a 2D hexagonal mesh. "
            "The cube places that mesh on the hexagonal lattice vectors and repeats the cell, "
            "so the cylinders are round and packed in a honeycomb. "
            "The Cartesian axes are for viewing. They are not a second PSCF result."
        )
    elif dimension == 2:
        nx, ny = mesh
        nz = nx
        grid = [phi_a[ix + nx * iy] for iz in range(nz) for iy in range(ny) for ix in range(nx)]
        shape = [nx, ny, nz]
        source = "derived_from_pscf"
        note = (
            "PSCF computed this cell on a 2D mesh. "
            "The cube repeats that mesh along z. The z direction is not a PSCF result."
        )
    elif dimension == 1:
        nx = mesh[0]
        grid = [phi_a[ix] for _iz in range(nx) for _iy in range(nx) for ix in range(nx)]
        shape = [nx, nx, nx]
        source = "derived_from_pscf"
        note = (
            "PSCF computed this cell on a 1D mesh. "
            "The cube repeats that mesh along y and z so the layers are visible. "
            "Those directions are not a PSCF result."
        )
    else:
        raise ValueError(f"Cannot display a {dimension}-dimensional concentration grid")
    spacing = _spacing(field.get("cell_parameters") or [], shape)
    return {
        "schema": MORPHOLOGY_SCHEMA,
        "representation_type": "monomer_concentration",
        "density_source": source,
        "quantity": "volume fraction of monomer 0 (block A in the PSCF example)",
        "monomer_b": "one minus monomer 0 on this incompressible diblock mesh",
        "mesh": shape,
        "spacing": spacing,
        "order": "x_fastest_then_y_then_z",
        "phi_a": grid,
        "source_mesh": mesh,
        "space_group": field.get("space_group"),
        "crystal_system": field.get("crystal_system"),
        "note": note,
        "warning": VISUALIZATION_NOTE,
    }


def illustrative_morphology(kind: str, edge: int) -> dict[str, Any]:
    """A labeled schematic. It is not a PSCF field and not a calculation."""
    if kind not in {"lam", "hex", "gyr", "bcc"}:
        raise ValueError(f"No illustrative picture is defined for {kind}")
    if edge < 2 or edge > 48:
        raise ValueError("illustrative grid_edge must be from 2 to 48")
    builders = {
        "lam": _lamellae,
        "gyr": _gyroid,
        "bcc": _bcc,
    }
    names = {
        "lam": "lamellae",
        "hex": "hexagonal cylinders",
        "gyr": "gyroid",
        "bcc": "BCC spheres",
    }
    note = (
        "This grid is a textbook sketch of the named morphology. "
        "It was not calculated by PSCF, by the 1D SCFT solver, or by the analytical map."
    )
    crystal = None
    if kind == "hex":
        mesh, phi = _hexagonal(edge)
        crystal = "hexagonal"
        note += (
            " The cylinders sit on a hexagonal lattice, with six neighbors at the same distance, "
            "and the box repeats that packing."
        )
    else:
        phi = builders[kind](edge)
        mesh = [edge, edge, edge]
    record = {
        "schema": MORPHOLOGY_SCHEMA,
        "representation_type": "schematic_density",
        "density_source": "illustrative",
        "morphology": names[kind],
        "quantity": "schematic A-block fraction used only to draw the morphology",
        "mesh": mesh,
        "spacing": [1.0 / edge, 1.0 / edge, 1.0 / edge],
        "order": "x_fastest_then_y_then_z",
        "phi_a": phi,
        "note": note,
        "warning": VISUALIZATION_NOTE,
    }
    if crystal is not None:
        record["crystal_system"] = crystal
    return record


def _spacing(parameters: list[float], shape: list[int]) -> list[float]:
    if not parameters:
        return [1.0 / size for size in shape]
    period = float(parameters[0])
    if len(parameters) >= len(shape):
        return [float(parameters[axis]) / shape[axis] for axis in range(len(shape))]
    return [period / size for size in shape]


def _lamellae(edge: int) -> list[float]:
    values = []
    for _z in range(edge):
        for _y in range(edge):
            for x in range(edge):
                values.append(_clip(0.5 + 0.45 * math.sin(2.0 * math.pi * x / edge)))
    return values


def _hexagonal(edge: int) -> tuple[list[int], list[float]]:
    """Round cylinders on the rectangular cell of a hexagonal lattice.

    One neighbor spacing is 1. The cell is 1 by sqrt(3), with cylinders at
    (0, 0) and (0.5, sqrt(3) / 2). Two repeats fill the box. The tube axis is z.
    """
    repeats = 2
    nx_cell = edge
    ny_cell = max(2, int(round(edge * math.sqrt(3.0))))
    nx = nx_cell * repeats
    ny = ny_cell * repeats
    nz = edge * repeats
    xs = np.arange(nx, dtype=float) / nx_cell
    ys = np.arange(ny, dtype=float) / ny_cell * math.sqrt(3.0)
    xx, yy = np.meshgrid(xs, ys, indexing="xy")
    distance = _hex_distance(xx, yy)
    plane = np.clip(0.5 + 0.45 * _soft_core_array(distance, 0.32), 0.0, 1.0)
    volume = np.repeat(plane[np.newaxis, :, :], nz, axis=0)
    return [nx, ny, nz], volume.reshape(-1).tolist()


def _embed_hexagonal_mesh(
    phi_a: list[float], mesh: list[int], parameters: list[float]
) -> tuple[list[float], list[int]]:
    """Resample a PSCF hexagonal r-grid onto a Cartesian honeycomb.

    PSCF's 2D hexagonal basis is r1 = (a, 0), r2 = (-a/2, a*sqrt(3)/2).
    A square voxel grid shears that basis. This samples several repeats of
    the cell on equal Cartesian steps and extrudes the tubes along z.
    """
    nx, ny = mesh
    grid = np.asarray(phi_a, dtype=float).reshape((ny, nx))
    a = float(parameters[0]) if parameters else 1.0
    if a == 0.0:
        a = 1.0
    repeats = 3
    root3 = math.sqrt(3.0)
    half_height = 0.5 * root3 * a
    x_min = -0.5 * a * repeats
    width = a * (repeats + 0.5 * repeats)
    height = half_height * repeats
    n_y = max(2, ny * repeats)
    n_x = max(n_y, int(round(n_y * width / height)))
    n_z = n_y
    columns = np.arange(n_x, dtype=float)[None, :]
    rows = np.arange(n_y, dtype=float)[:, None]
    y = height * (rows + 0.5) / n_y
    t = y / half_height
    x = x_min + width * (columns + 0.5) / n_x
    s = x / a + 0.5 * t
    plane = _sample_periodic(grid, s, t)
    volume = np.repeat(plane[np.newaxis, :, :], n_z, axis=0)
    return volume.reshape(-1).tolist(), [n_x, n_y, n_z]


def _sample_periodic(grid: np.ndarray, s: np.ndarray, t: np.ndarray) -> np.ndarray:
    ny, nx = grid.shape
    s = np.mod(s, 1.0)
    t = np.mod(t, 1.0)
    x = s * nx
    y = t * ny
    x0 = np.floor(x).astype(int) % nx
    y0 = np.floor(y).astype(int) % ny
    fx = x - np.floor(x)
    fy = y - np.floor(y)
    return (
        grid[y0, x0] * (1.0 - fx) * (1.0 - fy)
        + grid[y0, (x0 + 1) % nx] * fx * (1.0 - fy)
        + grid[(y0 + 1) % ny, x0] * (1.0 - fx) * fy
        + grid[(y0 + 1) % ny, (x0 + 1) % nx] * fx * fy
    )


def _hex_distance(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    period_y = math.sqrt(3.0)
    x = np.mod(x, 1.0)
    y = np.mod(y, period_y)
    best = np.full(np.broadcast(x, y).shape, np.inf)
    for cx, cy in ((0.0, 0.0), (0.5, period_y / 2.0)):
        for ix in (-1, 0, 1):
            for iy in (-1, 0, 1):
                best = np.minimum(best, np.hypot(x - (cx + ix), y - (cy + iy * period_y)))
    return best


def _soft_core_array(distance: np.ndarray, radius: float) -> np.ndarray:
    reach = 2.0 * radius
    core = np.cos(np.pi * distance / reach)
    return np.where(distance >= reach, -1.0, core)


def _gyroid(edge: int) -> list[float]:
    values = []
    for z in range(edge):
        for y in range(edge):
            for x in range(edge):
                fx = 2.0 * math.pi * x / edge
                fy = 2.0 * math.pi * y / edge
                fz = 2.0 * math.pi * z / edge
                level = (
                    math.sin(fx) * math.cos(fy)
                    + math.sin(fy) * math.cos(fz)
                    + math.sin(fz) * math.cos(fx)
                )
                # level spans [-1.5, 1.5]. 0.30 puts the two networks on either side of one half.
                values.append(_clip(0.5 + 0.30 * level))
    return values


def _bcc(edge: int) -> list[float]:
    centers = [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5)]
    radius = 0.22
    values = []
    for z in range(edge):
        for y in range(edge):
            for x in range(edge):
                point = (x / edge, y / edge, z / edge)
                distance = min(_periodic_distance3(point, center) for center in centers)
                values.append(_clip(0.5 + 0.45 * _soft_core(distance, radius)))
    return values


def _soft_core(distance: float, radius: float) -> float:
    """1 at the center, 0 at radius, -1 at twice that radius and beyond."""
    reach = 2.0 * radius
    if distance >= reach:
        return -1.0
    return math.cos(math.pi * distance / reach)


def _periodic_distance(x: float, y: float, cx: float, cy: float) -> float:
    dx = abs(x - cx)
    dy = abs(y - cy)
    dx = min(dx, 1.0 - dx)
    dy = min(dy, 1.0 - dy)
    return math.hypot(dx, dy)


def _periodic_distance3(point: tuple[float, float, float], center: tuple[float, float, float]) -> float:
    squares = 0.0
    for value, origin in zip(point, center):
        delta = abs(value - origin)
        delta = min(delta, 1.0 - delta)
        squares += delta * delta
    return math.sqrt(squares)


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))
