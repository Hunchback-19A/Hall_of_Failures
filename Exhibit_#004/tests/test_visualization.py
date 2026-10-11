"""Visualization is post-processing. These tests do not rank a schematic as a free energy."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from polymer_design.instrument.schema import parse_request
from polymer_design.visualization.exporters.avogadro import (
    _avogadro_cube_values,
    _surface_scalars,
    write_gaussian_cube,
)
from polymer_design.visualization.export import export_visualizations, load_visualize_request
from polymer_design.visualization.representation import display_from_pscf, illustrative_morphology
from polymer_engine.solvers.pscf_rpc.rgrid import parse_rgrid
from polymer_engine.solvers.pscf_rpc.runner import _command_with_concentration, find_pscf_rpc

_ROOT = Path(__file__).resolve().parents[1]
_LAM_COMMAND = _ROOT / "third_party" / "pscfpp" / "examples" / "rpc" / "scf" / "diblock" / "lam" / "command"
_W_LAM = _ROOT / "third_party" / "pscfpp" / "src" / "rpc" / "tests" / "field" / "in" / "w_lam.rf"


def _result(n: int, morphology: str = "lamellae") -> dict:
    return {
        "schema": "polymer_design.result.v1",
        "request_id": "screen",
        "client": "human",
        "solver": "analytical",
        "software_version": "0.1.0",
        "finished_at": "2026-10-08T00:00:00+00:00",
        "candidates": [
            {
                "id": f"c{index:04d}",
                "solver": "analytical",
                "preferred_morphology": morphology,
                "status": "converged",
                "software_version": "0.1.0",
                "pscf_commit": None,
                "visualization": {"available": False, "density_source": "unavailable", "fields": []},
            }
            for index in range(n)
        ],
    }


def _cores(mask: np.ndarray) -> list[tuple[float, float]]:
    visited = np.zeros(mask.shape, dtype=bool)
    ny, nx = mask.shape
    centers = []
    for y in range(ny):
        for x in range(nx):
            if not mask[y, x] or visited[y, x]:
                continue
            stack = [(x, y)]
            visited[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = cx + dx, cy + dy
                    if 0 <= xx < nx and 0 <= yy < ny and mask[yy, xx] and not visited[yy, xx]:
                        visited[yy, xx] = True
                        stack.append((xx, yy))
            if len(cells) < 3:
                continue
            centers.append((sum(point[0] for point in cells) / len(cells), sum(point[1] for point in cells) / len(cells)))
    return centers


def _ask_program(folder: Path, result: dict, *args: str) -> Path:
    source = folder / f"{result['request_id']}.result.json"
    source.write_text(json.dumps(result), encoding="utf-8")
    output = folder / "out" / result["request_id"]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "polymer_design",
            "visualize",
            str(source),
            "--out-dir",
            str(output),
            *args,
        ],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    cube = output / result["request_id"] / "batch_001" / "candidate_0001.cube"
    if not cube.is_file():
        raise AssertionError(completed.stderr)
    return cube


def _assert_current_cube(case: unittest.TestCase, cube: Path, morphology: dict) -> None:
    lines = cube.read_text(encoding="utf-8").splitlines()
    case.assertIn("red letter A", lines[1])
    case.assertIn("blue letter B", lines[1])
    case.assertIn("boundary of each region", lines[1])
    atoms = int(lines[2].split()[0])
    case.assertEqual(int(lines[6].split()[0]), 6)
    elements = [int(lines[6 + index].split()[0]) for index in range(atoms)]
    case.assertIn(8, elements)
    case.assertIn(7, elements)
    values = [float(item) for line in lines[6 + atoms :] for item in line.split()]
    expected = _avogadro_cube_values(morphology["mesh"], morphology["phi_a"])
    case.assertEqual(len(values), len(expected))
    case.assertTrue(
        all(math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-8) for left, right in zip(values, expected))
    )
    note = (cube.parent / "VISUALIZATION.txt").read_text(encoding="utf-8")
    case.assertIn("boundary of each region", note)
    case.assertIn("shell around a sphere or tube", note)


def _hex_result(folder: Path) -> dict:
    values = []
    for iy in range(8):
        for ix in range(8):
            ds = min(ix / 8.0, 1.0 - ix / 8.0)
            dt = min(iy / 8.0, 1.0 - iy / 8.0)
            phi = math.exp(-30.0 * (ds * ds + dt * dt))
            values.append([phi, 1.0 - phi])
    field_path = folder / "hex-field.json"
    field_path.write_text(
        json.dumps(
            {
                "schema": "polymer_design.concentration.v1",
                "candidate_id": "hex",
                "cell": "hex",
                "morphology": "hexagonal cylinders",
                "field": {
                    "mesh": [8, 8],
                    "values": values,
                    "cell_parameters": [1.0],
                    "crystal_system": "hexagonal",
                    "space_group": "p_6_m_m",
                },
            }
        ),
        encoding="utf-8",
    )
    result = _result(1, morphology="hexagonal cylinders")
    result["request_id"] = "hex-program"
    result["candidates"][0]["id"] = "hex"
    result["candidates"][0]["visualization"] = {
        "available": True,
        "density_source": "pscf_calculated",
        "fields": [{"cell": "hex", "file": field_path.name}],
    }
    return result


def _export(folder: Path, result: dict, **kwargs):
    path = folder / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    request = load_visualize_request(path, output_dir=folder / "visualizations", **kwargs)
    return export_visualizations(request, progress=lambda _message: None)


class VisualizationValidationTests(unittest.TestCase):
    def test_human_and_ai_hit_the_same_batch_refusal(self) -> None:
        messages = []
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            result_path = folder / "result.json"
            result_path.write_text(json.dumps(_result(10)), encoding="utf-8")
            for client in ("human", "ai"):
                request_path = folder / f"{client}.json"
                request_path.write_text(
                    json.dumps(
                        {
                            "schema": "polymer_design.visualize.v1",
                            "client": client,
                            "calculation": "result.json",
                            "illustrative": True,
                            "batch_size": 101,
                            "grid_edge": 2,
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError) as caught:
                    export_visualizations(load_visualize_request(request_path))
                messages.append(str(caught.exception))
        self.assertEqual(messages[0], messages[1])
        self.assertIn("101", messages[0])
        self.assertIn("not shortened", messages[0])

    def test_more_than_one_thousand_candidates_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            with self.assertRaises(ValueError) as caught:
                _export(folder, _result(1001), illustrative=True, grid_edge=2)
        self.assertIn("1001", str(caught.exception))
        self.assertIn("not truncated", str(caught.exception))

    def test_one_batch_does_not_write_the_rest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            summary = _export(folder, _result(150), illustrative=True, grid_edge=2, batch_size=100)
            batch = summary["batches"][0]
            self.assertEqual(batch["requested"], 150)
            self.assertEqual(batch["completed"], 100)
            self.assertEqual(batch["remaining"], 50)
            self.assertEqual(batch["status"], "batch_complete")
            self.assertTrue((folder / "visualizations" / "screen" / "batch_001" / "candidate_0001.cjson").is_file())
            self.assertFalse((folder / "visualizations" / "screen" / "batch_002").exists())

    def test_one_thousand_candidates_are_ten_batches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            summary = _export(
                folder,
                _result(1000),
                illustrative=True,
                grid_edge=2,
                batch_size=100,
                all_batches=True,
            )
            self.assertEqual(len(summary["batches"]), 10)
            root = folder / "visualizations" / "screen"
            self.assertTrue((root / "batch_001" / "candidate_0001.cjson").is_file())
            self.assertTrue((root / "batch_002" / "candidate_0101.cjson").is_file())
            self.assertTrue((root / "batch_010" / "candidate_1000.cjson").is_file())
            first = json.loads((root / "batch_001" / "batch.json").read_text(encoding="utf-8"))
            self.assertEqual(first["remaining"], 900)
            self.assertEqual(first["completed"], 100)
            last = json.loads((root / "batch_010" / "batch.json").read_text(encoding="utf-8"))
            self.assertEqual(last["remaining"], 0)
            self.assertEqual(last["completed"], 1000)

    def test_names_provenance_and_no_silent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            _export(folder, _result(1), illustrative=True, grid_edge=2, client="ai")
            picture = folder / "visualizations" / "screen" / "batch_001" / "candidate_0001.cjson"
            record = folder / "visualizations" / "screen" / "batch_001" / "candidate_0001.morphology.json"
            body = json.loads(picture.read_text(encoding="utf-8"))
            stored = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(body["chemicalJson"], 1)
            numbers = body["atoms"]["elements"]["number"]
            self.assertGreater(len(numbers), 1)
            self.assertEqual(numbers[0], 6)
            self.assertTrue(set(numbers) <= {6, 7, 8})
            self.assertIn(8, numbers)
            self.assertIn(7, numbers)
            self.assertIn("not a polymer atom", body["atoms"]["labels"][0].lower())
            self.assertTrue(any(label.lower().startswith("polymer a") for label in body["atoms"]["labels"]))
            self.assertTrue(any(label.lower().startswith("polymer b") for label in body["atoms"]["labels"]))
            self.assertNotIn("electronDensity", json.dumps(body["cube"]))
            self.assertEqual(body["cube"]["scalars"], _surface_scalars(stored["phi_a"]))
            self.assertTrue(all(0.0 <= value <= 1.0 for value in stored["phi_a"]))
            cube_text = picture.with_suffix(".cube").read_text(encoding="utf-8")
            cube_lines = cube_text.splitlines()
            atom_count = int(cube_lines[2].split()[0])
            self.assertGreater(atom_count, 0)
            self.assertIn("not polymer atoms", cube_lines[1].lower())
            self.assertIn("A-rich band", cube_lines[1])
            # Avogadro 2.0 reads the axis lines, then the atoms.
            self.assertGreater(float(cube_lines[3].split()[1]), 5.0)
            self.assertEqual(int(cube_lines[6].split()[0]), 6)
            float(cube_lines[6 + atom_count].split()[0])
            note = body["properties"]["morphologyVisualization"]
            self.assertEqual(note["density_source"], "illustrative")
            self.assertEqual(note["provenance"]["candidate_id"], "c0000")
            self.assertEqual(note["provenance"]["client"], "ai")
            self.assertEqual(note["provenance"]["calculation_id"], "screen")
            self.assertEqual(note["provenance"]["source_solver"], "analytical")
            self.assertIn("not an atomistic", note["warning"].lower())
            self.assertEqual(stored["density_source"], "illustrative")
            self.assertNotIn("pscf_calculated", json.dumps(stored))
            with self.assertRaises(ValueError) as caught:
                _export(folder, _result(1), illustrative=True, grid_edge=2)
            self.assertIn("already exists", str(caught.exception))
            _export(folder, _result(1), illustrative=True, grid_edge=2, overwrite=True)
            self.assertTrue(picture.is_file())

    def test_illustrative_request_writes_the_avogadro_cube(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            summary = _export(folder, _result(1), illustrative=True)
            batch = summary["batches"][0]
            cube_path = Path(batch["directory"]) / batch["files"][0]["cube"]
            lines = cube_path.read_text(encoding="utf-8").splitlines()
            atoms = int(lines[2].split()[0])
            self.assertGreater(atoms, 8)
            # Default lamellar sketch, repeated along the layers. Axes, then the cell-edge atoms.
            self.assertEqual([int(lines[index].split()[0]) for index in (3, 4, 5)], [72, 24, 24])
            self.assertEqual(int(lines[6].split()[0]), 6)
            self.assertEqual(len(lines[6].split()), 5)
            values = [float(item) for line in lines[6 + atoms :] for item in line.split()]
            self.assertGreater(max(values), 0.025)
            self.assertLess(min(values), -0.025)
            stored = json.loads(cube_path.with_suffix(".morphology.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["density_source"], "illustrative")
            self.assertEqual(stored["mesh"], [24, 24, 24])
            self.assertTrue(all(0.0 <= value <= 1.0 for value in stored["phi_a"]))
            picture = json.loads(cube_path.with_suffix(".cjson").read_text(encoding="utf-8"))
            self.assertEqual(picture["cube"]["dimensions"], [72, 24, 24])
            self.assertEqual(picture["atoms"]["elements"]["number"][0], 6)

    def test_other_illustrative_shapes_use_the_same_cell(self) -> None:
        expected = {
            "hexagonal cylinders": [48, 84, 48],
            "gyroid": [24, 24, 24],
            "BCC spheres": [48, 48, 48],
        }
        for name, shape in expected.items():
            with self.subTest(morphology=name):
                with tempfile.TemporaryDirectory() as raw:
                    folder = Path(raw)
                    summary = _export(folder, _result(1, morphology=name), illustrative=True)
                    batch = summary["batches"][0]
                    cube_path = Path(batch["directory"]) / batch["files"][0]["cube"]
                    lines = cube_path.read_text(encoding="utf-8").splitlines()
                    atoms = int(lines[2].split()[0])
                    dims = [int(lines[index].split()[0]) for index in (3, 4, 5)]
                    self.assertEqual(dims, shape)
                    self.assertEqual(int(lines[6].split()[0]), 6)
                    values = [float(item) for line in lines[6 + atoms :] for item in line.split()]
                    self.assertEqual(len(values), shape[0] * shape[1] * shape[2])
                    self.assertGreater(max(values), 0.025)
                    self.assertLess(min(values), -0.025)
                    stored = json.loads(cube_path.with_suffix(".morphology.json").read_text(encoding="utf-8"))
                    self.assertEqual(stored["density_source"], "illustrative")
                    self.assertEqual(stored["morphology"], name)
                    stored_mesh = shape if name == "hexagonal cylinders" else [24, 24, 24]
                    self.assertEqual(stored["mesh"], stored_mesh)
                    self.assertGreater(max(stored["phi_a"]) - min(stored["phi_a"]), 0.4)

    def test_gaussian_cube_stores_z_fastest_for_avogadro(self) -> None:
        nx, ny, nz = 3, 2, 4
        phi = [0.5] * (nx * ny * nz)
        phi[1 + nx * 0 + nx * ny * 2] = 0.95
        morphology = {
            "mesh": [nx, ny, nz],
            "phi_a": phi,
            "density_source": "illustrative",
            "representation_type": "schematic_density",
            "morphology": "marker",
            "crystal_system": "hexagonal",
            "note": "order check",
        }
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "order.cube"
            write_gaussian_cube(path, morphology, {"morphology": "marker"})
            lines = path.read_text(encoding="utf-8").splitlines()
            atoms = int(lines[2].split()[0])
            values = [float(item) for line in lines[6 + atoms :] for item in line.split()]
        # Avogadro index is ix * ny * nz + iy * nz + iz.
        self.assertEqual(values.index(max(values)), 1 * ny * nz + 2)

    def test_the_program_writes_the_current_pictures(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            sketch = _ask_program(
                folder,
                _result(1, morphology="hexagonal cylinders"),
                "--illustrative",
                "--grid-edge",
                "8",
            )
            stored = json.loads(sketch.with_suffix(".morphology.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["density_source"], "illustrative")
            self.assertEqual(stored["crystal_system"], "hexagonal")
            nx, ny, _nz = stored["mesh"]
            self.assertGreater(ny / nx, 1.6)
            _assert_current_cube(self, sketch, stored)
            calculated = _ask_program(folder, _hex_result(folder),)
            shown = json.loads(calculated.with_suffix(".morphology.json").read_text(encoding="utf-8"))
            self.assertEqual(shown["density_source"], "derived_from_pscf")
            self.assertEqual(shown["crystal_system"], "hexagonal")
            self.assertNotEqual(shown["mesh"][0], shown["mesh"][1])
            self.assertIn("not a second PSCF result", shown["note"])
            _assert_current_cube(self, calculated, shown)

    def test_hexagonal_sketch_is_a_honeycomb(self) -> None:
        shown = illustrative_morphology("hex", 16)
        nx, ny, nz = shown["mesh"]
        self.assertEqual(shown["crystal_system"], "hexagonal")
        self.assertGreater(ny / nx, 1.6)
        plane = np.asarray(shown["phi_a"], dtype=float).reshape((nz, ny, nx))[nz // 2]
        centers = _cores(plane > 0.85)
        self.assertGreaterEqual(len(centers), 6)
        width = nx / 16.0
        # One neighbor spacing is 16 voxels in x. y uses the same step, so the cell is sqrt(3) tall.
        physical = [(x / 16.0, y / (ny / 2.0) * math.sqrt(3.0)) for x, y in centers]
        interior = [
            point
            for point in physical
            if 0.45 < point[0] < width - 0.45 and 0.45 < point[1] < 2.0 * math.sqrt(3.0) - 0.45
        ]
        self.assertGreaterEqual(len(interior), 2)
        origin = interior[len(interior) // 2]
        neighbors = sorted(physical, key=lambda point: math.hypot(point[0] - origin[0], point[1] - origin[1]))
        neighbors = [point for point in neighbors if 0.7 < math.hypot(point[0] - origin[0], point[1] - origin[1]) < 1.25]
        self.assertGreaterEqual(len(neighbors), 6)
        nearest = neighbors[:6]
        lengths = [math.hypot(point[0] - origin[0], point[1] - origin[1]) for point in nearest]
        self.assertLess(max(lengths) - min(lengths), 0.2)
        angles = sorted(math.atan2(point[1] - origin[1], point[0] - origin[0]) for point in nearest)
        gaps = [angles[index + 1] - angles[index] for index in range(5)]
        gaps.append(angles[0] + 2.0 * math.pi - angles[-1])
        for gap in gaps:
            self.assertLess(abs(gap - math.pi / 3.0), 0.35)

    def test_a_hexagonal_pscf_mesh_is_drawn_as_a_honeycomb(self) -> None:
        values = []
        for iy in range(16):
            for ix in range(16):
                ds = min(ix / 16.0, 1.0 - ix / 16.0)
                dt = min(iy / 16.0, 1.0 - iy / 16.0)
                phi = math.exp(-40.0 * (ds * ds + dt * dt))
                values.append([phi, 1.0 - phi])
        shown = display_from_pscf(
            {
                "mesh": [16, 16],
                "values": values,
                "cell_parameters": [1.0],
                "crystal_system": "hexagonal",
                "space_group": "p_6_m_m",
            }
        )
        self.assertEqual(shown["density_source"], "derived_from_pscf")
        self.assertEqual(shown["source_mesh"], [16, 16])
        self.assertIn("hexagonal lattice", shown["note"])
        self.assertIn("not a second PSCF result", shown["note"])
        nx, ny, nz = shown["mesh"]
        self.assertNotEqual(nx, ny)
        plane = np.asarray(shown["phi_a"], dtype=float).reshape((nz, ny, nx))[nz // 2]
        centers = _cores(plane > 0.55 * float(plane.max()))
        self.assertGreaterEqual(len(centers), 6)
        origin = min(centers, key=lambda point: (point[0] - nx / 2) ** 2 + (point[1] - ny / 2) ** 2)
        ranked = sorted(
            centers,
            key=lambda point: math.hypot(point[0] - origin[0], point[1] - origin[1]),
        )
        ranked = [point for point in ranked if math.hypot(point[0] - origin[0], point[1] - origin[1]) > 1.0]
        self.assertGreaterEqual(len(ranked), 6)
        nearest = ranked[:6]
        lengths = [math.hypot(point[0] - origin[0], point[1] - origin[1]) for point in nearest]
        self.assertLess((max(lengths) - min(lengths)) / min(lengths), 0.2)
        angles = sorted(math.atan2(point[1] - origin[1], point[0] - origin[0]) for point in nearest)
        gaps = [angles[index + 1] - angles[index] for index in range(5)]
        gaps.append(angles[0] + 2.0 * math.pi - angles[-1])
        for gap in gaps:
            self.assertLess(abs(gap - math.pi / 3.0), 0.30)

    def test_a_weak_block_still_crosses_both_avogadro_surfaces(self) -> None:
        # Hex-like: the B-rich side bottoms out just above 0.30, so a fixed 0.30 cut draws nothing.
        rich = [0.86, 0.80, 0.72, 0.60, 0.56]
        poor = [0.48, 0.40, 0.35, 0.33, 0.313]
        scalars = _surface_scalars((rich + poor) * 12)
        self.assertGreater(max(scalars), 0.025)
        self.assertLess(min(scalars), -0.025)

    def test_calculated_export_draws_both_blocks_without_a_sketch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            low = [0.313 + index * (0.45 - 0.313) / 15 for index in range(16)]
            values = [[value, 1.0 - value] for value in low] + [[0.85, 0.15]] * 48
            field_path = folder / "fields" / "bcc-bcc.json"
            field_path.parent.mkdir(parents=True)
            field_path.write_text(
                json.dumps(
                    {
                        "schema": "polymer_design.concentration.v1",
                        "candidate_id": "bcc",
                        "cell": "bcc",
                        "morphology": "BCC spheres",
                        "field": {
                            "dimension": 3,
                            "mesh": [4, 4, 4],
                            "values": values,
                            "cell_parameters": [2.0, 2.0, 2.0],
                            "space_group": "I_m_-3_m",
                            "crystal_system": "cubic",
                            "density_source": "pscf_calculated",
                            "quantity": "monomer_concentration",
                        },
                    }
                ),
                encoding="utf-8",
            )
            result_path = folder / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "schema": "polymer_design.result.v1",
                        "request_id": "screen",
                        "client": "human",
                        "solver": "pscf_rpc",
                        "software_version": "0.1.0",
                        "finished_at": "2026-10-08T00:00:00+00:00",
                        "candidates": [
                            {
                                "id": "bcc",
                                "solver": "pscf_rpc",
                                "preferred_morphology": "BCC spheres",
                                "status": "converged",
                                "software_version": "0.1.0",
                                "pscf_commit": None,
                                "visualization": {
                                    "available": True,
                                    "density_source": "pscf_calculated",
                                    "fields": [{"cell": "bcc", "file": "fields/bcc-bcc.json"}],
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            export_visualizations(
                load_visualize_request(result_path, output_dir=folder / "visualizations", illustrative=False),
                progress=lambda _message: None,
            )
            batch = folder / "visualizations" / "screen" / "batch_001"
            picture = json.loads((batch / "candidate_0001.cjson").read_text(encoding="utf-8"))
            stored = json.loads((batch / "candidate_0001.morphology.json").read_text(encoding="utf-8"))
            scalars = picture["cube"]["scalars"]
            self.assertGreater(max(scalars), 0.025)
            self.assertLess(min(scalars), -0.025)
            self.assertEqual(stored["density_source"], "pscf_calculated")
            self.assertGreaterEqual(min(stored["phi_a"]), 0.30)
            self.assertNotIn("illustrative", stored["density_source"])

    def test_a_strong_field_keeps_the_offset_from_one_half(self) -> None:
        phi = [0.10, 0.20, 0.40, 0.60, 0.80, 0.90] * 10
        scale = 0.025 / 0.20
        expected = [round((value - 0.5) * scale, 8) for value in phi]
        self.assertEqual(_surface_scalars(phi), expected)

    def test_surface_values_cross_the_avogadro_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            _export(folder, _result(1), illustrative=True, grid_edge=8)
            picture = folder / "visualizations" / "screen" / "batch_001" / "candidate_0001.cjson"
            record = folder / "visualizations" / "screen" / "batch_001" / "candidate_0001.morphology.json"
            scalars = json.loads(picture.read_text(encoding="utf-8"))["cube"]["scalars"]
            stored = json.loads(record.read_text(encoding="utf-8"))
            self.assertGreater(max(scalars), 0.025)
            self.assertLess(min(scalars), -0.025)
            self.assertGreater(min(stored["phi_a"]), 0.0)
            self.assertLess(max(stored["phi_a"]), 1.0)

    def test_segment_figures_show_both_blocks_and_the_interface(self) -> None:
        import numpy as np
        from PIL import Image

        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            _export(folder, _result(1), illustrative=True, grid_edge=16)
            batch = folder / "visualizations" / "screen" / "batch_001"
            profile = np.asarray(Image.open(batch / "candidate_0001.profile.png"))
            segment = np.asarray(Image.open(batch / "candidate_0001.segment.png"))
            interface = np.asarray(Image.open(batch / "candidate_0001.interface.png"))
            self.assertTrue(((profile[:, :, 0] > 180) & (profile[:, :, 2] < 80)).any())
            self.assertTrue(((profile[:, :, 2] > 180) & (profile[:, :, 0] < 80)).any())
            self.assertTrue(((segment[:, :, 0] > 180) & (segment[:, :, 1] < 80) & (segment[:, :, 2] < 80)).any())
            self.assertTrue(((segment[:, :, 2] > 180) & (segment[:, :, 0] < 80)).any())
            self.assertTrue(((segment[:, :, 1] > 180) & (segment[:, :, 0] < 80) & (segment[:, :, 2] < 80)).any())
            self.assertTrue(
                ((interface[:, :, 0] > 140) & (interface[:, :, 1] > 100) & (interface[:, :, 2] < 90)).any()
            )
            record = json.loads((batch / "batch.json").read_text(encoding="utf-8"))
            self.assertEqual(record["files"][0]["profile"], "candidate_0001.profile.png")
            note = (batch / "VISUALIZATION.txt").read_text(encoding="utf-8")
            self.assertIn("not a sushi", note.lower())

    def test_missing_density_is_not_replaced_by_a_picture(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            with self.assertRaises(ValueError) as caught:
                _export(folder, _result(1), illustrative=False)
            self.assertIn("Nothing was invented", str(caught.exception))
            self.assertFalse((folder / "visualizations").exists())

    def test_one_dimensional_pscf_grid_is_labeled_derived_when_extruded(self) -> None:
        field = {
            "mesh": [2],
            "values": [[0.2, 0.8], [0.9, 0.1]],
            "cell_parameters": [4.0],
            "space_group": "P_-1",
            "crystal_system": "lamellar",
            "density_source": "pscf_calculated",
        }
        shown = display_from_pscf(field)
        self.assertEqual(shown["density_source"], "derived_from_pscf")
        self.assertEqual(shown["source_mesh"], [2])
        self.assertEqual(len(shown["phi_a"]), 8)
        cube = {
            "mesh": [1, 1, 1],
            "values": [[0.3, 0.7]],
            "cell_parameters": [2.0],
            "space_group": "I_a_-3_d",
            "crystal_system": "cubic",
        }
        native = display_from_pscf(cube)
        self.assertEqual(native["density_source"], "pscf_calculated")
        self.assertEqual(native["phi_a"], [0.3])


class PscfFieldBoundaryTests(unittest.TestCase):
    def test_rgrid_reader_does_not_rename_a_w_field_as_concentration(self) -> None:
        parsed = parse_rgrid(_W_LAM.read_text(encoding="utf-8"))
        self.assertEqual(parsed["dimension"], 1)
        self.assertEqual(parsed["mesh"], [32])
        self.assertEqual(len(parsed["values"]), 32)
        self.assertNotIn("density_source", parsed)

    def test_concentration_command_follows_iterate(self) -> None:
        text = _command_with_concentration(_LAM_COMMAND.read_text(encoding="utf-8"))
        written = text.index("WRITE_C_RGRID out/c.rf")
        self.assertLess(text.index("ITERATE"), written)
        self.assertLess(written, text.index("FINISH"))
        self.assertEqual(text.count("ITERATE"), 1)

    def test_kept_lamellar_concentration_matches_the_known_free_energy(self) -> None:
        if find_pscf_rpc() is None:
            self.skipTest("pscf_rpc is not available")
        from polymer_design.instrument.engine import execute_request

        request = parse_request(
            {
                "solver": "pscf_rpc",
                "cells": ["lam"],
                "keep_concentration": True,
                "timeout_s": 180,
                "candidates": [
                    {
                        "id": "lam-056",
                        "architecture": "diblock",
                        "volume_fractions": [0.56, 0.44],
                        "chi": 0.06,
                        "N": 200,
                    }
                ],
            }
        )
        result = execute_request(request, progress=lambda _message: None)
        candidate = result["candidates"][0]
        self.assertAlmostEqual(candidate["free_energy"], 1.92567500294, places=8)
        grid = candidate["concentration_fields"][0]["field"]
        self.assertEqual(grid["density_source"], "pscf_calculated")
        self.assertEqual(grid["mesh"], [40])
        totals = [sum(row) for row in grid["values"]]
        self.assertTrue(all(0.0 < row[0] < 1.0 for row in grid["values"]))
        self.assertAlmostEqual(sum(totals) / len(totals), 1.0, places=4)
