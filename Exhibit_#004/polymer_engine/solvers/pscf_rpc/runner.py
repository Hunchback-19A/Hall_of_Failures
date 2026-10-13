# Copyright (C) 2026 Disquietude
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Run vendored PSCF diblock examples with pscf_rpc."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from polymer_engine.solvers.pscf_rpc.paramfile import (
    iteration_converged,
    parse_f_helmholtz,
    rewrite_diblock_param,
)
from polymer_engine.solvers.pscf_rpc.rgrid import parse_rgrid

_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
_EXAMPLES = (
    _PACKAGE_ROOT
    / "third_party"
    / "pscfpp"
    / "examples"
    / "rpc"
    / "scf"
    / "diblock"
)

CELLS: dict[str, dict[str, str | int]] = {
    "lam": {"dimension": 1, "morphology": "lamellae"},
    "hex": {"dimension": 2, "morphology": "hexagonal cylinders"},
    "gyr": {"dimension": 3, "morphology": "gyroid"},
    "bcc": {"dimension": 3, "morphology": "BCC spheres"},
}

CHIN_CONVENTION = (
    "PSCF diblock examples use block lengths that sum to 1. "
    "The adapter writes χN into the chi entry and does not pass a separate N."
)


@dataclass
class CellRun:
    cell: str
    morphology: str
    dimension: int
    free_energy: float | None
    converged: bool
    returncode: int | None
    detail: str
    concentration: dict | None = None


_WSL_DISTRO = "Ubuntu"
_WSL_MARK = "wsl:"


def _wsl_executable() -> str | None:
    return shutil.which("wsl.exe") or shutil.which("wsl")


def _wsl_file_exists(linux_path: str) -> bool:
    wsl = _wsl_executable()
    if wsl is None or os.name != "nt":
        return False
    completed = subprocess.run(
        [wsl, "-d", _WSL_DISTRO, "-u", "root", "-e", "test", "-x", linux_path],
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _bundled_executable() -> Path | None:
    """Windows build shipped beside the vendored PSCF data files."""
    if os.name != "nt":
        return None
    candidate = _PACKAGE_ROOT / "third_party" / "pscfpp" / "bin" / "pscf_rpc.exe"
    if candidate.is_file():
        return candidate
    return None


def find_pscf_rpc() -> str | None:
    """Resolve PSCF_RPC, the bundled Windows exe, then PATH.

    A PSCF_RPC value that is a Linux path is launched through WSL. That
    path is a developer override. Windows users are not probed for Ubuntu.
    """
    override = os.environ.get("PSCF_RPC", "").strip()
    if override:
        path = Path(override)
        if path.is_file():
            return str(path)
        if override.startswith("/") and _wsl_file_exists(override):
            return _WSL_MARK + override
        return None
    bundled = _bundled_executable()
    if bundled is not None:
        return str(bundled)
    found = shutil.which("pscf_rpc") or shutil.which("pscf_rpc.exe")
    return found


def pscf_command(executable: str, dimension: int, cwd: Path) -> tuple[list[str], Path | None]:
    """Build the process argv. A wsl: path runs the Linux binary with --cd."""
    args = ["-d", str(dimension), "-p", "param", "-c", "command", "-e"]
    if executable.startswith(_WSL_MARK):
        wsl = _wsl_executable() or "wsl.exe"
        linux_bin = executable[len(_WSL_MARK) :]
        return (
            [wsl, "-d", _WSL_DISTRO, "-u", "root", "--cd", str(cwd), "--", linux_bin, *args],
            None,
        )
    return [executable, *args], cwd


def decode_process_output(data: bytes | None) -> str:
    """Decode pscf_rpc output. wsl.exe often writes UTF-16 into a pipe."""
    if not data:
        return ""
    if data.startswith(b"\xff\xfe") or (len(data) >= 4 and data[1] == 0 and data[3] == 0):
        return data.decode("utf-16")
    return data.decode("utf-8", errors="replace")


def example_dir(cell: str) -> Path:
    if cell not in CELLS:
        known = ", ".join(CELLS)
        raise ValueError(f"Unknown PSCF cell '{cell}'. Known: {known}")
    return _EXAMPLES / cell


def run_cell(
    cell: str,
    f_a: float,
    chi_n: float,
    *,
    executable: str,
    work_dir: Path,
    timeout_s: float,
    keep_concentration: bool = False,
) -> CellRun:
    """Copy one vendored example, substitute f and χN, and run pscf_rpc."""
    spec = CELLS[cell]
    source = example_dir(cell)
    param_src = source / "param"
    command_src = source / "command"
    field_src = source / "in" / "w.bf"
    for required in (param_src, command_src, field_src):
        if not required.is_file():
            return CellRun(
                cell=cell,
                morphology=str(spec["morphology"]),
                dimension=int(spec["dimension"]),
                free_energy=None,
                converged=False,
                returncode=None,
                detail=f"Missing vendored example file: {required}",
            )
    case = work_dir / cell
    (case / "in").mkdir(parents=True, exist_ok=True)
    (case / "out").mkdir(parents=True, exist_ok=True)
    param_text = rewrite_diblock_param(param_src.read_text(encoding="utf-8"), f_a, chi_n)
    (case / "param").write_text(param_text, encoding="utf-8", newline="\n")
    command_text = command_src.read_text(encoding="utf-8")
    if keep_concentration:
        command_text = _command_with_concentration(command_text)
    (case / "command").write_text(command_text, encoding="utf-8", newline="\n")
    shutil.copyfile(field_src, case / "in" / "w.bf")
    dimension = int(spec["dimension"])
    argv, process_cwd = pscf_command(executable, dimension, case)
    try:
        completed = subprocess.run(
            argv,
            cwd=process_cwd,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CellRun(
            cell=cell,
            morphology=str(spec["morphology"]),
            dimension=dimension,
            free_energy=None,
            converged=False,
            returncode=None,
            detail=f"pscf_rpc exceeded {timeout_s:g} s",
        )
    except OSError as exc:
        return CellRun(
            cell=cell,
            morphology=str(spec["morphology"]),
            dimension=dimension,
            free_energy=None,
            converged=False,
            returncode=None,
            detail=str(exc),
        )
    log_text = decode_process_output(completed.stdout) + "\n" + decode_process_output(completed.stderr)
    energy = parse_f_helmholtz(log_text)
    converged = energy is not None and iteration_converged(log_text)
    if energy is None:
        detail = "Log has no fHelmholtz line."
    elif not iteration_converged(log_text):
        detail = "Iterator did not report Converged."
    else:
        detail = "fHelmholtz from pscf_rpc."
    if completed.returncode != 0:
        detail = f"pscf_rpc exit {completed.returncode}. {detail}"
    concentration = None
    if keep_concentration:
        field_path = case / "out" / "c.rf"
        if field_path.is_file() and field_path.stat().st_size > 0:
            try:
                concentration = parse_rgrid(field_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                detail = f"{detail} Concentration file out/c.rf could not be read: {exc}"
            else:
                concentration["density_source"] = "pscf_calculated"
                concentration["quantity"] = "monomer_concentration"
        elif completed.returncode == 0:
            detail = f"{detail} Concentration file out/c.rf was not written."
    return CellRun(
        cell=cell,
        morphology=str(spec["morphology"]),
        dimension=dimension,
        free_energy=energy,
        converged=converged and completed.returncode == 0,
        returncode=completed.returncode,
        detail=detail,
        concentration=concentration,
    )


def run_cells(
    f_a: float,
    chi_n: float,
    cells: list[str],
    *,
    timeout_s: float,
    keep_concentration: bool = False,
) -> tuple[str | None, list[CellRun]]:
    """Run each cell. The first item is an error when the executable is absent."""
    executable = find_pscf_rpc()
    if executable is None:
        return (
            "pscf_rpc was not found. On Windows the bundled program is "
            "third_party/pscfpp/bin/pscf_rpc.exe. Otherwise set PSCF_RPC or put "
            "pscf_rpc on PATH.",
            [],
        )
    import tempfile

    runs: list[CellRun] = []
    with tempfile.TemporaryDirectory(prefix="pscf_rpc_") as tmp:
        work = Path(tmp)
        for cell in cells:
            runs.append(
                run_cell(
                    cell,
                    f_a,
                    chi_n,
                    executable=executable,
                    work_dir=work,
                    timeout_s=timeout_s,
                    keep_concentration=keep_concentration,
                )
            )
    return None, runs


def _command_with_concentration(text: str) -> str:
    """Ask PSCF to write the concentration ITERATE computed.

    The write goes immediately after ITERATE. A later command in some example
    files reloads the starting field, and writing after that reload does not
    record the iterated concentration. ITERATE itself is unchanged.
    """
    lines = text.splitlines()
    command = "WRITE_C_RGRID out/c.rf"
    if any(line.strip().startswith("WRITE_C_RGRID") for line in lines):
        body = lines
    else:
        body = []
        placed = False
        for line in lines:
            body.append(line)
            if line.strip() == "ITERATE" and not placed:
                body.append(command)
                placed = True
        if not placed:
            finish = next((index for index, line in enumerate(body) if line.strip() == "FINISH"), None)
            if finish is None:
                body.append(command)
            else:
                body.insert(finish, command)
    return "\n".join(body) + "\n"


def best_converged(runs: list[CellRun]) -> CellRun | None:
    converged = [run for run in runs if run.converged and run.free_energy is not None]
    if not converged:
        return None
    return min(converged, key=lambda run: float(run.free_energy))
