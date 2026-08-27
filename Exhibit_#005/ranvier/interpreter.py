"""Ranvier interpreter.

Runs only programs that survived semantic validation. Execution here is not a
brain simulation. It is a laboratory trace: what was declared, what was
associated, what was measured, and what was explicitly *not* concluded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .compiler import CompiledProgram, Compiler
from .errors import CognitionError
from .parser import (
    Assignment,
    AssociateStmt,
    ConnectStmt,
    Declaration,
    LoadStmt,
    LookupStmt,
    MeasureStmt,
    NameExpr,
    ObserveStmt,
    PredictStmt,
    SubscriptExpr,
)


BANNER = "Ranvier 0.1 - never compile a destiny when you only measured a state."


class Interpreter:
    def __init__(self, compiled: CompiledProgram):
        self.compiled = compiled
        self.trace: list[str] = []

    def run(self) -> str:
        if self.compiled.errors:
            raise CognitionError("Refusing to run a program that failed semantic validation.")
        self.trace = [BANNER, ""]
        for stmt in self.compiled.source.statements:
            self._exec(stmt)
        self.trace.append("")
        self.trace.append("Program accepted. 0 prophecies compiled.")
        return "\n".join(self.trace)

    def _exec(self, stmt) -> None:
        if isinstance(stmt, LoadStmt):
            self._note_load(stmt.model)
        elif isinstance(stmt, Declaration):
            extra = ""
            if stmt.value is not None:
                extra = f" = { _expr_text(stmt.value) }"
            origin = ""
            binding = self.compiled.bindings.get(stmt.name)
            if binding and binding.origin == "atlas":
                origin = "  [atlas]"
            self.trace.append(f"Declared {stmt.label} {stmt.name}{extra}{origin}")
        elif isinstance(stmt, Assignment):
            self.trace.append(f"Assigned {stmt.name} = {_expr_text(stmt.value)}")
        elif isinstance(stmt, AssociateStmt):
            self.trace.append(
                f"Associated FUNCTION {stmt.function} WITH NETWORK {stmt.network}"
            )
            self.trace.append("  note: functions are network processes, not regional identities")
        elif isinstance(stmt, ConnectStmt):
            self.trace.append(
                f"Connected REGION {stmt.source} TO {stmt.target} VIA TRACT {stmt.tract}"
            )
        elif isinstance(stmt, MeasureStmt):
            self.trace.append(f"Measured {stmt.state} OF {stmt.of}")
            self.trace.append("  note: a measurement is not a classification")
        elif isinstance(stmt, ObserveStmt):
            self.trace.append(f"Observed {stmt.behavior} AS {stmt.as_name}")
            self.trace.append("  note: behavior is an outcome, not a biological cause")
        elif isinstance(stmt, PredictStmt):
            self.trace.append(f"Predicted {stmt.prediction} FROM {stmt.source}")
            self.trace.append("  note: this remains a PREDICTION, not an identity")
        elif isinstance(stmt, LookupStmt):
            self._lookup(stmt)

    def _note_load(self, model: str) -> None:
        key = {
            "atlas": "atlas",
            "brain_atlas": "atlas",
            "connectivity": "connectivity",
            "brain_connectivity": "connectivity",
            "function": "function",
            "functions": "function",
            "brain_function": "function",
            "behavior": "behavior",
            "behaviour": "behavior",
            "brain_behavior": "behavior",
        }.get(model.lower(), model.lower())
        meta = (self.compiled.models.get(key) or {}).get("meta") or {}
        purpose = meta.get("purpose", key)
        source = meta.get("primary_source") or meta.get("source") or ""
        suffix = f" — {source}" if source else ""
        self.trace.append(f"Loaded {key}: {purpose}{suffix}")

    def _lookup(self, stmt: LookupStmt) -> None:
        expr = stmt.expr
        atlas = self.compiled.models.get("atlas") or {}
        name = expr.name if isinstance(expr, (NameExpr, SubscriptExpr)) else None
        region = None
        for entry in atlas.get("regions", []):
            if entry.get("region") == name:
                region = entry
                break
        if region is None:
            self.trace.append(f"Lookup {name}: no atlas coordinates (name is bound, but not a region).")
            return
        if isinstance(expr, SubscriptExpr):
            landmarks = region.get("landmarks") or {}
            if expr.key == "centroid":
                value = region.get("centroid") or landmarks.get("centroid")
            elif expr.key == "bounds":
                value = region.get("bounds")
            else:
                value = landmarks.get(expr.key)
            self.trace.append(f"Lookup {name}[{expr.key!r}] = {value}")
            return
        self.trace.append(
            f"Lookup {name}: label={region.get('label_type')}  "
            f"centroid={region.get('centroid')}  bounds={region.get('bounds')}"
        )


def _expr_text(expr) -> str:
    if isinstance(expr, SubscriptExpr):
        return f"{expr.name}[{expr.key!r}]"
    if isinstance(expr, NameExpr):
        return expr.name
    return str(expr)


def run_file(path: Union[str, Path], models_dir: Optional[Union[str, Path]] = None) -> str:
    compiled = Compiler(models_dir=models_dir).compile_file(path)
    if compiled.errors:
        return compiled.report()
    return Interpreter(compiled).run()
