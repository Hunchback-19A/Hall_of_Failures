# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Optional spreadsheet export. The scientific record remains the JSON result."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


def write_xlsx(path: Path, result: dict[str, Any]) -> None:
    rows = [_header()]
    for candidate in result["candidates"]:
        if candidate["morphologies"]:
            for item in candidate["morphologies"]:
                rows.append(_row(result, candidate, item))
        else:
            rows.append(_row(result, candidate, None))
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as book:
        book.writestr("[Content_Types].xml", _content_types())
        book.writestr("xl/workbook.xml", _workbook())
        book.writestr("xl/_rels/workbook.xml.rels", _rels())
        book.writestr("xl/worksheets/sheet1.xml", _sheet(rows))


def _header() -> list[str]:
    return [
        "request_id",
        "client",
        "candidate_id",
        "architecture",
        "volume_fractions",
        "chi",
        "N",
        "chiN",
        "solver",
        "pscf_commit",
        "cell",
        "morphology",
        "space_group",
        "converged",
        "free_energy_name",
        "free_energy",
        "relative_free_energy",
        "preferred_morphology",
        "batch_rank",
        "status",
        "warnings",
    ]


def _row(result: dict[str, Any], candidate: dict[str, Any], item: dict[str, Any] | None) -> list[str]:
    incoming = candidate["input"]
    return [
        str(result["request_id"]),
        str(result["client"]),
        str(candidate["id"]),
        str(incoming["architecture"]),
        " ".join(f"{value:.6g}" for value in incoming["volume_fractions"]),
        _num(incoming["chi"]),
        _num(incoming["degree_of_polymerization"]),
        _num(incoming["chiN"]),
        str(candidate["solver"]),
        "" if candidate.get("pscf_commit") is None else str(candidate["pscf_commit"]),
        "" if item is None else str(item.get("cell") or ""),
        "" if item is None else str(item.get("morphology") or ""),
        "" if item is None else str(item.get("space_group") or ""),
        "" if item is None else ("yes" if item["converged"] else "no"),
        "" if item is None else str(item.get("free_energy_name") or ""),
        "" if item is None or item.get("free_energy") is None else _num(item["free_energy"]),
        "" if item is None or item.get("relative_free_energy") is None else _num(item["relative_free_energy"]),
        "" if candidate.get("preferred_morphology") is None else str(candidate["preferred_morphology"]),
        "" if candidate.get("batch_rank") is None else str(candidate["batch_rank"]),
        str(candidate["status"]),
        " | ".join(candidate.get("warnings") or []),
    ]


def _num(value: float) -> str:
    return f"{value:.10g}"


def _sheet(rows: list[list[str]]) -> str:
    body = []
    for r_index, row in enumerate(rows, start=1):
        cells = []
        for c_index, value in enumerate(row, start=1):
            ref = f"{_column(c_index)}{r_index}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            )
        body.append(f'<row r="{r_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(body)}</sheetData></worksheet>'
    )


def _column(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _content_types() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )


def _workbook() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="candidates" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )


def _rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
