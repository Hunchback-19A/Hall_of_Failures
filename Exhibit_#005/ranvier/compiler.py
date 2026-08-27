"""Ranvier compiler.

Parse → load models → semantically validate → produce a compiled program
that the interpreter may run only if no conceptual errors remain.

This is the safety layer between human intention and brain-related
representation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from .errors import CognitionError, ModelError, format_error_block
from .parser import Program, parse, parse_file
from .validator import Binding, ValidationResult, Validator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

MODEL_FILES = {
    "atlas": "brain_atlas.json",
    "connectivity": "brain_connectivity.json",
    "function": "brain_function.json",
    "behavior": "brain_behavior.json",
}


@dataclass
class CompiledProgram:
    source: Program
    bindings: dict[str, Binding]
    notes: list[str]
    errors: list[CognitionError]
    models: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def report(self) -> str:
        if self.errors:
            return format_error_block(self.errors)
        return "Ranvier compilation succeeded. 0 prophecies compiled."


class Compiler:
    def __init__(self, models_dir: Optional[Union[str, Path]] = None):
        self.models_dir = Path(models_dir) if models_dir else MODELS_DIR
        self.models = load_models(self.models_dir)

    def compile_source(self, source: str, filename: str = "<memory>") -> CompiledProgram:
        program = parse(source, filename=filename)
        return self._compile(program)

    def compile_file(self, path: Union[str, Path]) -> CompiledProgram:
        program = parse_file(str(path))
        return self._compile(program)

    def _compile(self, program: Program) -> CompiledProgram:
        validator = Validator(self.models)
        result: ValidationResult = validator.validate(program)
        return CompiledProgram(
            source=program,
            bindings=result.bindings,
            notes=result.notes,
            errors=result.errors,
            models=self.models,
        )


def load_models(models_dir: Optional[Union[str, Path]] = None) -> dict:
    root = Path(models_dir) if models_dir else MODELS_DIR
    models: dict = {}
    missing: list[str] = []
    for key, filename in MODEL_FILES.items():
        path = root / filename
        if not path.exists():
            missing.append(str(path))
            continue
        with open(path, encoding="utf-8") as handle:
            models[key] = json.load(handle)
    if missing and not models:
        raise ModelError(
            "No Ranvier brain models were found.",
            hint="expected JSON files in models/",
        )
    return models


def compile_file(path: Union[str, Path], models_dir: Optional[Union[str, Path]] = None) -> CompiledProgram:
    return Compiler(models_dir=models_dir).compile_file(path)


def compile_source(source: str, filename: str = "<memory>", models_dir: Optional[Union[str, Path]] = None) -> CompiledProgram:
    return Compiler(models_dir=models_dir).compile_source(source, filename=filename)
