"""Run Ranvier programs from Axon.

This is a laboratory runner. It compiles and interprets .cog source.
It does not stimulate tissue, open a biological interface, or control a brain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from ranvier.compiler import CompiledProgram, Compiler, MODEL_FILES
from ranvier.errors import CognitionError
from ranvier.interpreter import Interpreter
from ranvier.labels import NETWORK
from ranvier.parser import AssociateStmt, Declaration


@dataclass
class RunResult:
    ok: bool
    report: str
    errors: list[CognitionError] = field(default_factory=list)
    compiled: Optional[CompiledProgram] = None
    path: Optional[Path] = None


def run_cog_file(
    path: Union[str, Path],
    models_dir: Optional[Union[str, Path]] = None,
) -> RunResult:
    """Save-then-run entry point used by the Axon Run button."""
    source = Path(path)
    try:
        compiler = Compiler(models_dir=models_dir)
        compiled = compiler.compile_file(source)
    except CognitionError as exc:
        return RunResult(ok=False, report=str(exc), errors=[exc], path=source)
    except OSError as exc:
        err = CognitionError(f"Could not read {source}: {exc}")
        return RunResult(ok=False, report=str(err), errors=[err], path=source)

    if compiled.errors:
        return RunResult(
            ok=False,
            report=compiled.report(),
            errors=list(compiled.errors),
            compiled=compiled,
            path=source,
        )

    trace = Interpreter(compiled).run()
    report = format_simulation_report(source, compiled, trace)
    return RunResult(ok=True, report=report, compiled=compiled, path=source)


def format_simulation_report(path: Path, compiled: CompiledProgram, trace: str) -> str:
    """IDLE-style run output written as a scientific notebook report."""
    loaded = _loaded_model_files(compiled)
    networks = _program_networks(compiled)
    lines = [
        "Ranvier Simulation Report",
        "",
        f"File: {path.name}",
        "",
        "Never compile a destiny when you only measured a state.",
        "",
        "Loaded:",
    ]
    if loaded:
        lines.extend(f"- {name}" for name in loaded)
    else:
        lines.append("- (no models loaded in this program)")
    lines.extend(["", "Networks:"])
    if networks:
        lines.extend(f"- {name}" for name in networks)
    else:
        lines.append("- (none declared)")
    lines.extend(
        [
            "",
            "Trace:",
            trace.rstrip(),
            "",
            "Status:",
            "Simulation completed.",
            "",
            "No biological interface detected.",
        ]
    )
    return "\n".join(lines)


def _program_networks(compiled: CompiledProgram) -> list[str]:
    names: set[str] = set()
    for stmt in compiled.source.statements:
        if isinstance(stmt, Declaration) and stmt.label == "NETWORK":
            names.add(stmt.name)
        elif isinstance(stmt, AssociateStmt):
            names.add(stmt.network)
    for name, binding in compiled.bindings.items():
        if binding.label is NETWORK and binding.origin == "declared":
            names.add(name)
    return sorted(names)


def _loaded_model_files(compiled: CompiledProgram) -> list[str]:
    names: list[str] = []
    notes = " ".join(compiled.notes).lower()
    for key, filename in MODEL_FILES.items():
        if f"loaded {key}" in notes:
            names.append(filename)
    return names
