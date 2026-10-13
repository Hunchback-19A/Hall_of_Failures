# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Turn a stored calculation into morphology files, in bounded batches."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from polymer_design.instrument.limits import max_candidates, max_visualization_batch
from polymer_design.instrument.provenance import pscf_commit, software_version
from polymer_design.visualization.exporters.avogadro import (
    write_avogadro_cjson,
    write_gaussian_cube,
)
from polymer_design.visualization.exporters.segment_profile import write_segment_figures
from polymer_design.visualization.notes import (
    BATCH_SCHEMA,
    EXPORTER_VERSION,
    MORPHOLOGY_SCHEMA,
    REQUEST_SCHEMA,
    SEGMENT_FIGURE_NOTE,
    VISUALIZATION_NOTE,
)
from polymer_design.visualization.representation import (
    display_from_pscf,
    illustrative_morphology,
    morphology_kind,
)

Progress = Callable[[str], None]


@dataclass
class VisualizeRequest:
    client: str
    calculation_id: str
    calculation_path: Path
    result: dict[str, Any]
    selected: list[dict[str, Any]]
    export_format: str
    illustrative: bool
    batch_size: int
    batch_index: int | None
    all_batches: bool
    overwrite: bool
    output_dir: Path
    grid_edge: int


def load_visualize_request(
    path: Path,
    *,
    client: str | None = None,
    export_format: str | None = None,
    illustrative: bool | None = None,
    batch_index: int | None = None,
    all_batches: bool | None = None,
    batch_size: int | None = None,
    overwrite: bool | None = None,
    output_dir: Path | None = None,
    grid_edge: int | None = None,
) -> VisualizeRequest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    schema = str(payload.get("schema") or "")
    if schema == REQUEST_SCHEMA:
        return _from_visualize_file(
            path,
            payload,
            client=client,
            export_format=export_format,
            illustrative=illustrative,
            batch_index=batch_index,
            all_batches=all_batches,
            batch_size=batch_size,
            overwrite=overwrite,
            output_dir=output_dir,
            grid_edge=grid_edge,
        )
    if schema != "polymer_design.result.v1":
        raise ValueError(
            f"{path.name} is not a calculation result or a {REQUEST_SCHEMA} request"
        )
    return _from_result(
        path,
        payload,
        client=client or "human",
        candidate_ids=None,
        export_format=export_format or "avogadro",
        illustrative=bool(illustrative),
        batch_index=batch_index,
        all_batches=bool(all_batches),
        batch_size=batch_size,
        overwrite=bool(overwrite),
        output_dir=output_dir,
        grid_edge=grid_edge if grid_edge is not None else 24,
    )


def export_visualizations(request: VisualizeRequest, progress: Progress | None = None) -> dict[str, Any]:
    """Write one batch, or every batch when all_batches is set. Never more than the batch limit at a time."""
    report = progress or _silent
    selected = request.selected
    total = len(selected)
    ceiling = max_candidates()
    if total > ceiling:
        raise ValueError(
            f"Visualization request has {total} candidates; the calculation limit is {ceiling}. "
            "The request was rejected and was not truncated."
        )
    batch_limit = max_visualization_batch()
    if request.batch_size > batch_limit:
        raise ValueError(
            f"Visualization batch size {request.batch_size} is above the limit of {batch_limit}. "
            "The batch was rejected and was not shortened."
        )
    if request.batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    _require_pictures(request)
    batch_count = (total + request.batch_size - 1) // request.batch_size
    if request.all_batches and request.batch_index is not None:
        raise ValueError("Ask for one batch or for all batches, not both")
    if request.batch_index is None and not request.all_batches:
        indexes = [1]
    elif request.all_batches:
        indexes = list(range(1, batch_count + 1))
    else:
        if request.batch_index < 1 or request.batch_index > batch_count:
            raise ValueError(
                f"Batch {request.batch_index} is outside 1..{batch_count} for {total} candidates"
            )
        indexes = [request.batch_index]
    written: list[dict[str, Any]] = []
    for number in indexes:
        start = (number - 1) * request.batch_size
        chunk = selected[start : start + request.batch_size]
        report(
            f"Visualization export batch {number}/{batch_count}: "
            f"{len(chunk)} file(s), {total - start - len(chunk)} remaining after this batch"
        )
        record = _write_batch(request, number, batch_count, start, chunk)
        written.append(record)
        report(
            "Visualization export\n"
            f"Requested: {total}\n"
            f"Batch limit: {batch_limit}\n"
            f"Completed: {record['completed']}\n"
            f"Remaining: {record['remaining']}\n"
            f"Status: {record['status']}"
        )
    return {
        "schema": BATCH_SCHEMA,
        "client": request.client,
        "requested": total,
        "batch_limit": batch_limit,
        "batches": written,
        "status": written[-1]["status"] if len(written) == 1 else "batches_written",
    }


def persist_concentration_fields(result: dict[str, Any], result_path: Path) -> None:
    """Move PSCF grids out of the result JSON and onto disk beside it."""
    folder = result_path.parent / f"{result_path.name}.fields"
    for candidate in result.get("candidates", []):
        grids = candidate.pop("concentration_fields", [])
        if not grids:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for item in grids:
            name = f"{_safe(str(candidate['id']))}-{_safe(str(item['cell']))}.json"
            payload = {
                "schema": "polymer_design.concentration.v1",
                "candidate_id": candidate["id"],
                "cell": item["cell"],
                "morphology": item.get("morphology"),
                "field": item["field"],
            }
            (folder / name).write_text(json.dumps(payload) + "\n", encoding="utf-8")
            files.append({"cell": item["cell"], "file": f"{folder.name}/{name}"})
        block = candidate.setdefault("visualization", {})
        block["fields"] = files
        block["available"] = True
        block["density_source"] = "pscf_calculated"
    command = f"python -m polymer_design visualize {result_path} --format avogadro"
    for candidate in result.get("candidates", []):
        block = candidate.get("visualization")
        if isinstance(block, dict):
            block["export_command"] = command


def _from_visualize_file(path: Path, payload: dict[str, Any], **overrides: Any) -> VisualizeRequest:
    unknown = sorted(set(payload) - {
        "schema",
        "client",
        "calculation",
        "candidates",
        "format",
        "illustrative",
        "batch",
        "all_batches",
        "batch_size",
        "overwrite",
        "output_dir",
        "grid_edge",
    })
    if unknown:
        raise ValueError(
            "Unrecognized visualization field(s): "
            + ", ".join(unknown)
            + ". The batch ceiling is run_limits.json, not a request field."
        )
    if "max_visualization_batch" in payload or "max_candidates" in payload:
        raise ValueError("A visualization request cannot raise a batch ceiling.")
    client = str(overrides["client"] or payload.get("client", "human")).casefold()
    if client not in {"human", "ai"}:
        raise ValueError("client must be 'human' or 'ai'")
    calculation = payload.get("calculation")
    if not isinstance(calculation, str) or not calculation:
        raise ValueError("calculation must be the path of a stored result JSON")
    calculation_path = Path(calculation)
    if not calculation_path.is_absolute():
        calculation_path = path.parent / calculation_path
    result = json.loads(calculation_path.read_text(encoding="utf-8"))
    if result.get("schema") != "polymer_design.result.v1":
        raise ValueError(f"{calculation_path.name} is not a polymer_design.result.v1 file")
    illustrative = payload.get("illustrative", False)
    if not isinstance(illustrative, bool):
        raise ValueError("illustrative must be true or false")
    if overrides["illustrative"] is not None:
        illustrative = bool(overrides["illustrative"])
    all_batches = bool(payload.get("all_batches", False))
    if overrides["all_batches"] is not None:
        all_batches = bool(overrides["all_batches"])
    batch_index = payload.get("batch")
    if overrides["batch_index"] is not None:
        batch_index = overrides["batch_index"]
    if batch_index is not None:
        batch_index = int(batch_index)
    batch_size = int(payload.get("batch_size", max_visualization_batch()))
    if overrides["batch_size"] is not None:
        batch_size = int(overrides["batch_size"])
    overwrite = bool(payload.get("overwrite", False))
    if overrides["overwrite"]:
        overwrite = True
    export_format = str(overrides["export_format"] or payload.get("format") or "avogadro")
    output_value = overrides["output_dir"] or payload.get("output_dir") or "visualizations"
    output_dir = Path(output_value)
    if not output_dir.is_absolute():
        output_dir = path.parent / output_dir
    grid_edge = int(payload.get("grid_edge", 24))
    if overrides["grid_edge"] is not None:
        grid_edge = int(overrides["grid_edge"])
    return _from_result(
        calculation_path,
        result,
        client=client,
        candidate_ids=payload.get("candidates"),
        export_format=export_format,
        illustrative=illustrative,
        batch_index=batch_index,
        all_batches=all_batches,
        batch_size=batch_size,
        overwrite=overwrite,
        output_dir=output_dir,
        grid_edge=grid_edge,
    )


def _from_result(
    calculation_path: Path,
    result: dict[str, Any],
    *,
    client: str,
    candidate_ids: Any,
    export_format: str,
    illustrative: bool,
    batch_index: int | None,
    all_batches: bool,
    batch_size: int | None,
    overwrite: bool,
    output_dir: Path | None,
    grid_edge: int,
) -> VisualizeRequest:
    if export_format != "avogadro":
        raise ValueError(
            "The only viewer export implemented here is avogadro (Chemical JSON with a cube). "
            f"Received {export_format}."
        )
    if client not in {"human", "ai"}:
        raise ValueError("client must be 'human' or 'ai'")
    candidates = list(result.get("candidates") or [])
    if candidate_ids is None:
        selected = candidates
    else:
        if not isinstance(candidate_ids, list) or not candidate_ids:
            raise ValueError("candidates must be a non-empty list of ids from the calculation")
        by_id = {item["id"]: item for item in candidates}
        missing = [str(item) for item in candidate_ids if item not in by_id]
        if missing:
            raise ValueError("Unknown candidate id(s): " + ", ".join(missing))
        selected = [by_id[item] for item in candidate_ids]
    if not selected:
        raise ValueError("No candidates to visualize")
    size = max_visualization_batch() if batch_size is None else int(batch_size)
    folder = output_dir or Path("visualizations")
    return VisualizeRequest(
        client=client,
        calculation_id=str(result.get("request_id") or calculation_path.stem),
        calculation_path=calculation_path.resolve(),
        result=result,
        selected=selected,
        export_format=export_format,
        illustrative=illustrative,
        batch_size=size,
        batch_index=batch_index,
        all_batches=all_batches,
        overwrite=overwrite,
        output_dir=folder,
        grid_edge=grid_edge,
    )


def _require_pictures(request: VisualizeRequest) -> None:
    if request.illustrative:
        return
    missing = [
        item["id"]
        for item in request.selected
        if not _field_index(request, item)
    ]
    if missing and len(missing) == len(request.selected):
        raise ValueError(
            "This stored calculation has no PSCF concentration grid, so an Avogadro "
            "volume was not written. Re-run the calculation with --keep-concentration "
            "to save the field PSCF computed, or pass --illustrative for a labeled "
            "schematic that is not a PSCF result. Nothing was invented in its place."
        )


def _write_batch(
    request: VisualizeRequest,
    number: int,
    batch_count: int,
    start: int,
    chunk: list[dict[str, Any]],
) -> dict[str, Any]:
    folder = request.output_dir / _safe(request.calculation_id) / f"batch_{number:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    failures = []
    for offset, candidate in enumerate(chunk):
        serial = start + offset + 1
        stem = f"candidate_{serial:04d}"
        targets = [
            folder / f"{stem}.cjson",
            folder / f"{stem}.cube",
            folder / f"{stem}.morphology.json",
            folder / f"{stem}.profile.png",
            folder / f"{stem}.segment.png",
            folder / f"{stem}.interface.png",
        ]
        if any(path.exists() for path in targets) and not request.overwrite:
            raise ValueError(
                f"{targets[0].name} already exists in {folder}. "
                "Pass --overwrite to replace visualization files."
            )
        try:
            morphology, provenance = _picture(request, candidate)
        except ValueError as exc:
            failures.append({"id": candidate["id"], "file": stem, "error": str(exc)})
            continue
        provenance["file_stem"] = stem
        write_avogadro_cjson(targets[0], morphology, provenance)
        write_gaussian_cube(targets[1], morphology, provenance)
        targets[2].write_text(json.dumps(morphology | {"provenance": provenance}, indent=2) + "\n", encoding="utf-8")
        figures = write_segment_figures(folder, stem, morphology)
        files.append({
            "id": candidate["id"],
            "stem": stem,
            "cjson": targets[0].name,
            "cube": targets[1].name,
            "profile": figures["profile"],
            "segment": figures["segment"],
            "interface": figures["interface"],
        })
    total = len(request.selected)
    completed_through = start + len(chunk)
    record = {
        "schema": BATCH_SCHEMA,
        "client": request.client,
        "calculation_id": request.calculation_id,
        "calculation_file": str(request.calculation_path),
        "requested": total,
        "batch_limit": max_visualization_batch(),
        "batch_index": number,
        "batch_count": batch_count,
        "completed": completed_through,
        "remaining": total - completed_through,
        "status": "batch_complete" if not failures else "batch_complete_with_failures",
        "illustrative": request.illustrative,
        "files": files,
        "failures": failures,
        "warning": VISUALIZATION_NOTE,
        "directory": str(folder.resolve()),
    }
    (folder / "batch.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (folder / "VISUALIZATION.txt").write_text(VISUALIZATION_NOTE + "\n\n" + SEGMENT_FIGURE_NOTE + "\n", encoding="utf-8")
    return record


def _picture(request: VisualizeRequest, candidate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    provenance = _provenance(request, candidate)
    if request.illustrative:
        kind = morphology_kind(str(candidate.get("preferred_morphology") or ""))
        if kind is None:
            raise ValueError(
                f"{candidate['id']} has no lamellae, hexagonal, gyroid, or BCC label to sketch"
            )
        morphology = illustrative_morphology(kind, request.grid_edge)
        provenance["density_source"] = "illustrative"
        provenance["representation_type"] = morphology["representation_type"]
        return morphology, provenance
    field = _load_field(request, candidate)
    if field is None:
        raise ValueError(
            f"{candidate['id']} has no stored PSCF concentration grid. "
            "An Avogadro file was not invented for it."
        )
    morphology = display_from_pscf(field)
    morphology["morphology"] = candidate.get("preferred_morphology")
    provenance["density_source"] = morphology["density_source"]
    provenance["representation_type"] = morphology["representation_type"]
    return morphology, provenance


def _field_index(request: VisualizeRequest, candidate: dict[str, Any]) -> dict[str, Any] | None:
    files = (candidate.get("visualization") or {}).get("fields") or []
    inline = candidate.get("concentration_fields") or []
    preferred = str(candidate.get("preferred_morphology") or "")
    for item in inline:
        if item.get("morphology") == preferred or not preferred:
            return {"inline": item["field"]}
    for item in files:
        if _cell_matches(item.get("cell"), preferred) or len(files) == 1:
            return {"file": item["file"]}
    if files:
        return {"file": files[0]["file"]}
    if inline:
        return {"inline": inline[0]["field"]}
    return None


def _load_field(request: VisualizeRequest, candidate: dict[str, Any]) -> dict[str, Any] | None:
    located = _field_index(request, candidate)
    if located is None:
        return None
    if "inline" in located:
        return located["inline"]
    path = Path(located["file"])
    if not path.is_absolute():
        path = request.calculation_path.parent / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["field"]


def _cell_matches(cell: Any, morphology: str) -> bool:
    kind = morphology_kind(morphology)
    return kind is not None and str(cell) == kind


def _provenance(request: VisualizeRequest, candidate: dict[str, Any]) -> dict[str, Any]:
    solver = candidate.get("solver") or request.result.get("solver")
    return {
        "candidate_id": candidate.get("id"),
        "calculation_id": request.calculation_id,
        "calculation_file": str(request.calculation_path),
        "source_solver": solver,
        "solver_version": candidate.get("software_version") or request.result.get("software_version") or software_version(),
        "pscf_commit": candidate.get("pscf_commit") or request.result.get("pscf_commit") or (
            pscf_commit() if solver == "pscf_rpc" else None
        ),
        "source_calculation_timestamp": request.result.get("finished_at"),
        "morphology": candidate.get("preferred_morphology"),
        "export_format": "cjson",
        "exporter_version": EXPORTER_VERSION,
        "client": request.client,
        "schema": MORPHOLOGY_SCHEMA,
    }


def _safe(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "calculation"


def _silent(_message: str) -> None:
    return None
