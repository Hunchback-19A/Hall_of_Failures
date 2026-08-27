"""Semantic validation for Ranvier.

The compiler must prevent:

    REGION → FUNCTION
    STATE → ID
    PREDICTION → ID
    STRUCTURE → PERSONALITY

Whenever possible it suggests an alternative, in the same spirit as Python's
"Did you mean...".
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Optional

from .errors import (
    CognitionError,
    CoordinateError,
    LabelError,
    ModelError,
    attribution_error,
    coordinates_missing_error,
    destiny_error,
    function_to_region_error,
    prediction_to_id_error,
    region_to_function_error,
    state_to_id_error,
    structure_to_personality_error,
)
from .labels import (
    CONNECTION,
    FORBIDDEN_LABELS,
    FUNCTION,
    ID,
    NETWORK,
    PATTERN,
    PERSONALITY,
    PREDICTION,
    PROCESS,
    REGION,
    RESERVED_IDENTITY_NAMES,
    SIGNAL,
    STATE,
    STRUCTURE,
    TEMP,
    TRACT,
    VALID_LABELS,
    CognitionLabel,
    assignment_allowed,
    get_label,
)
from .parser import (
    Assignment,
    AssociateStmt,
    ConnectStmt,
    Declaration,
    LookupStmt,
    MeasureStmt,
    NameExpr,
    ObserveStmt,
    PredictStmt,
    Program,
    Span,
    Stmt,
    SubscriptExpr,
)


@dataclass
class Binding:
    name: str
    label: CognitionLabel
    origin: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    bindings: dict[str, Binding]
    errors: list[CognitionError]
    notes: list[str]


class Validator:
    def __init__(self, models: dict):
        self.models = models
        self.bindings: dict[str, Binding] = {}
        self.errors: list[CognitionError] = []
        self.notes: list[str] = []
        self._imported: set[str] = set()

    def validate(self, program: Program) -> ValidationResult:
        for stmt in program.statements:
            self._validate_stmt(stmt)
        return ValidationResult(bindings=self.bindings, errors=list(self.errors), notes=list(self.notes))

    def _validate_stmt(self, stmt: Stmt) -> None:
        kind = type(stmt).__name__
        handler = {
            "LoadStmt": self._load,
            "Declaration": self._declaration,
            "Assignment": self._assignment,
            "AssociateStmt": self._associate,
            "ConnectStmt": self._connect,
            "MeasureStmt": self._measure,
            "ObserveStmt": self._observe,
            "PredictStmt": self._predict,
            "LookupStmt": self._lookup,
        }.get(kind)
        if handler is None:
            self.errors.append(
                CognitionError("Unrecognized statement.", **self._loc(stmt.span))
            )
            return
        handler(stmt)

    def _load(self, stmt) -> None:
        model = stmt.model.lower()
        aliases = {
            "atlas": "atlas",
            "brain_atlas": "atlas",
            "structure": "atlas",
            "connectivity": "connectivity",
            "brain_connectivity": "connectivity",
            "function": "function",
            "functions": "function",
            "brain_function": "function",
            "behavior": "behavior",
            "behaviour": "behavior",
            "brain_behavior": "behavior",
        }
        key = aliases.get(model)
        if key is None:
            self.errors.append(
                ModelError(
                    f"Unknown model {stmt.model!r}.",
                    hint="load atlas, connectivity, function, or behavior",
                    **self._loc(stmt.span),
                )
            )
            return
        if key in self._imported:
            self.notes.append(f"Model {key!r} already loaded.")
            return
        data = self.models.get(key)
        if not data:
            self.errors.append(
                ModelError(
                    f"Model {key!r} is not available.",
                    hint="check the files in models/",
                    **self._loc(stmt.span),
                )
            )
            return
        imported = 0
        for name, binding in _bindings_from_model(key, data):
            if name in self.bindings and self.bindings[name].label.name != binding.label.name:
                self.errors.append(
                    ModelError(
                        f"Model conflict: {name!r} is already {self.bindings[name].label} "
                        f"and cannot also be {binding.label} from {key}.",
                        hint="keep structure, connectivity, function, and behavior in separate models",
                        **self._loc(stmt.span),
                    )
                )
                continue
            self.bindings.setdefault(name, binding)
            imported += 1
        self._imported.add(key)
        self.notes.append(f"Loaded {key} ({imported} named entries).")

        if key == "function":
            self._check_function_model(data, stmt.span)

    def _check_function_model(self, data: dict, span: Span) -> None:
        for entry in data.get("functions", []):
            regions = entry.get("regions") or entry.get("mapped_regions") or []
            networks = entry.get("associated_networks") or []
            if len(regions) == 1 and not networks:
                self.errors.append(
                    ModelError(
                        f"Function {entry.get('function')!r} maps one-to-one onto a region. "
                        "Ranvier refuses that model.",
                        hint="represent the function as a NETWORK_PROCESS with associated_networks",
                        **self._loc(span),
                    )
                )

    def _declaration(self, stmt: Declaration) -> None:
        loc = self._loc(stmt.span)
        label = get_label(stmt.label)
        if stmt.label in FORBIDDEN_LABELS or (label and label.category.value == "forbidden"):
            if stmt.label in {"DESTINY", "FATE"}:
                self.errors.append(destiny_error(**loc))
            elif stmt.label == "PERSONALITY":
                source = self._expr_label(stmt.value) if stmt.value else STRUCTURE
                if source and source.category.value == "structural":
                    self.errors.append(structure_to_personality_error(**loc))
                else:
                    self.errors.append(structure_to_personality_error(**loc))
            else:
                self.errors.append(
                    LabelError(
                        f"{stmt.label} is not a Ranvier label.",
                        hint="use STATE, PATTERN, PREDICTION, or ID — never a destiny",
                        **loc,
                    )
                )
            return
        if label is None:
            suggestion = _closest(stmt.label, VALID_LABELS)
            self.errors.append(
                LabelError(
                    f"Unknown label {stmt.label!r}.",
                    hint=suggestion,
                    **loc,
                )
            )
            return
        if label is ID and stmt.name.lower() in RESERVED_IDENTITY_NAMES:
            self.errors.append(
                LabelError(
                    f"{stmt.name!r} is not a valid identity. Ranvier will not name a person as {stmt.name}.",
                    hint="use a subject code such as subject_001, never a moral conclusion",
                    **loc,
                )
            )
            return
        if stmt.name in self.bindings and self.bindings[stmt.name].label.name != label.name:
            existing = self.bindings[stmt.name]
            self.errors.append(
                LabelError(
                    f"{stmt.name!r} is already {existing.label} (from {existing.origin}) "
                    f"and cannot be redeclared as {label}.",
                    hint=f"keep {stmt.name} as {existing.label}, or choose a new name",
                    **loc,
                )
            )
            return
        self.bindings[stmt.name] = Binding(stmt.name, label, "declared")
        if stmt.value is not None:
            self._check_assignment(stmt.name, label, stmt.value, stmt.span)

    def _assignment(self, stmt: Assignment) -> None:
        loc = self._loc(stmt.span)
        if stmt.name.upper() in FORBIDDEN_LABELS:
            if stmt.name.upper() in {"DESTINY", "FATE"}:
                self.errors.append(destiny_error(**loc))
            elif stmt.name.upper() == "PERSONALITY":
                self.errors.append(structure_to_personality_error(**loc))
            else:
                self.errors.append(LabelError(f"{stmt.name} is not a Ranvier label.", **loc))
            return
        if stmt.name not in self.bindings:
            if stmt.name.lower() in RESERVED_IDENTITY_NAMES:
                self.errors.append(
                    LabelError(
                        f"Cannot assign into reserved identity name {stmt.name!r}.",
                        hint="Ranvier does not compile destiny, failure, or personality",
                        **loc,
                    )
                )
                return
            suggestion = _closest(stmt.name, self.bindings)
            self.errors.append(
                LabelError(
                    f"Unknown name {stmt.name!r}. Declare it with a label first.",
                    hint=f"REGION {stmt.name}" if not suggestion else suggestion,
                    **loc,
                )
            )
            return
        self._check_assignment(stmt.name, self.bindings[stmt.name].label, stmt.value, stmt.span)

    def _check_assignment(self, target_name: str, target_label: CognitionLabel, expr, span: Span) -> None:
        loc = self._loc(span)
        if isinstance(expr, SubscriptExpr):
            self._lookup_coords(expr, span)
            self.errors.append(
                LabelError(
                    f"Cannot assign a coordinate lookup to {target_label}.",
                    hint="coordinates describe anatomy (REGION/STRUCTURE), not functions or identities",
                    **loc,
                )
            )
            return

        source_name = expr.name
        if source_name.lower() in RESERVED_IDENTITY_NAMES and target_label is ID:
            if source_name.lower() in {"cause", "entire_cause"}:
                self.errors.append(attribution_error(**loc))
            else:
                self.errors.append(state_to_id_error(**loc))
            return
        if _looks_like_coordinate(source_name) and source_name not in self.bindings:
            self.errors.append(coordinates_missing_error(source_name, **loc))
            return
        source_label = self._lookup_name(source_name, span, required=True)
        if source_label is None:
            return

        if target_name.lower() in RESERVED_IDENTITY_NAMES or (
            target_label is ID and source_name.lower() in RESERVED_IDENTITY_NAMES
        ):
            if source_label in {PREDICTION, PATTERN, STATE, TEMP}:
                self.errors.append(prediction_to_id_error(**loc) if source_label is PREDICTION else attribution_error(**loc))
            else:
                self.errors.append(attribution_error(**loc))
            return

        pair = (source_label.name, target_label.name)
        if pair == ("REGION", "FUNCTION") or pair == ("STRUCTURE", "FUNCTION"):
            self.errors.append(region_to_function_error(**loc))
            return
        if pair == ("FUNCTION", "REGION") or pair == ("FUNCTION", "STRUCTURE"):
            self.errors.append(function_to_region_error(**loc))
            return
        if target_label is PERSONALITY or target_label.name == "PERSONALITY":
            self.errors.append(structure_to_personality_error(**loc))
            return
        if source_label.category.value == "structural" and target_label.name == "PERSONALITY":
            self.errors.append(structure_to_personality_error(**loc))
            return
        if target_label is ID and source_label is not ID:
            if source_label is PREDICTION:
                self.errors.append(prediction_to_id_error(**loc))
            elif source_label in {STATE, TEMP, PATTERN}:
                self.errors.append(state_to_id_error(**loc))
            elif source_label.category.value == "functional":
                self.errors.append(
                    LabelError(
                        "A modeled function cannot become a person's identity.",
                        hint="keep FUNCTION attached to a NETWORK, never to ID",
                        **loc,
                    )
                )
            else:
                self.errors.append(state_to_id_error(**loc))
            return
        if source_label is PREDICTION and target_label is ID:
            self.errors.append(prediction_to_id_error(**loc))
            return
        if source_label is PREDICTION and target_label.name in FORBIDDEN_LABELS:
            self.errors.append(destiny_error(**loc))
            return
        if not assignment_allowed(source_label, target_label):
            self.errors.append(
                LabelError(
                    f"Cannot convert {source_label} → {target_label}.",
                    hint=_conversion_hint(source_label, target_label),
                    **loc,
                )
            )

    def _associate(self, stmt: AssociateStmt) -> None:
        loc = self._loc(stmt.span)
        fn = self._lookup_name(stmt.function, stmt.span, required=True)
        net = self._lookup_name(stmt.network, stmt.span, required=True)
        if fn is None or net is None:
            return
        if fn is not FUNCTION and fn is not PROCESS:
            self.errors.append(
                LabelError(
                    f"associate expects a FUNCTION or PROCESS, not {fn}.",
                    hint="FUNCTION decision_making",
                    **loc,
                )
            )
            return
        if net is REGION:
            self.errors.append(region_to_function_error(**loc))
            return
        if net is not NETWORK:
            self.errors.append(
                LabelError(
                    f"A function may be associated with a NETWORK, not {net}.",
                    hint="associate decision_making with decision_network",
                    **loc,
                )
            )
            return
        self.notes.append(f"Associated FUNCTION {stmt.function} WITH NETWORK {stmt.network}.")

    def _connect(self, stmt: ConnectStmt) -> None:
        loc = self._loc(stmt.span)
        src = self._lookup_name(stmt.source, stmt.span, required=True)
        dst = self._lookup_name(stmt.target, stmt.span, required=True)
        tract = self._lookup_name(stmt.tract, stmt.span, required=True)
        if src is None or dst is None or tract is None:
            return
        if src not in {REGION, STRUCTURE} or dst not in {REGION, STRUCTURE}:
            self.errors.append(
                LabelError(
                    "connect links anatomical REGION/STRUCTURE values.",
                    hint="connect frontal_lobe to temporal_lobe via arcuate_fasciculus",
                    **loc,
                )
            )
            return
        if tract not in {TRACT, CONNECTION}:
            self.errors.append(
                LabelError(
                    f"connect requires a TRACT, not {tract}.",
                    hint="white-matter pathways are TRACT, not FUNCTION",
                    **loc,
                )
            )
            return
        link_name = f"{stmt.source}__{stmt.target}"
        self.bindings[link_name] = Binding(link_name, CONNECTION, "connect")
        self.notes.append(f"Connected {stmt.source} to {stmt.target} via {stmt.tract}.")

    def _measure(self, stmt: MeasureStmt) -> None:
        loc = self._loc(stmt.span)
        state = self._lookup_name(stmt.state, stmt.span, required=True)
        target = self._lookup_name(stmt.of, stmt.span, required=True)
        if state is None or target is None:
            return
        if state not in {STATE, TEMP, PATTERN, SIGNAL}:
            self.errors.append(
                LabelError(
                    f"measure records a STATE/TEMP/PATTERN, not {state}.",
                    hint="STATE current_attention",
                    **loc,
                )
            )
            return
        if target not in {REGION, NETWORK, STRUCTURE, PROCESS}:
            self.errors.append(
                LabelError(
                    f"Cannot take a measurement of {target}.",
                    hint="measure a STATE of a NETWORK or REGION — never of an ID",
                    **loc,
                )
            )
            return
        if target is ID:
            self.errors.append(state_to_id_error(**loc))
            return
        self.notes.append(
            f"Measured {state} {stmt.state} OF {target} {stmt.of}. A measurement is not a classification."
        )

    def _observe(self, stmt: ObserveStmt) -> None:
        loc = self._loc(stmt.span)
        if stmt.as_name.lower() in RESERVED_IDENTITY_NAMES:
            self.errors.append(attribution_error(**loc))
            return
        outcome = self._lookup_name(stmt.as_name, stmt.span, required=True)
        behavior = self.bindings.get(stmt.behavior)
        if behavior is None:
            # Behaviors may arrive from the behavior model or be free observation names.
            self.bindings[stmt.behavior] = Binding(stmt.behavior, STATE, "observed")
        if outcome is None:
            return
        if outcome is ID:
            self.errors.append(attribution_error(**loc))
            return
        if outcome not in {STATE, PATTERN, TEMP}:
            self.errors.append(
                LabelError(
                    f"An observation must be recorded as STATE or PATTERN, not {outcome}.",
                    hint="keep behavior separate from biological mechanism",
                    **loc,
                )
            )
            return
        self.notes.append(
            f"Observed {stmt.behavior} as {stmt.as_name}. Behavior is an outcome, not a cause."
        )

    def _predict(self, stmt: PredictStmt) -> None:
        loc = self._loc(stmt.span)
        pred = self._lookup_name(stmt.prediction, stmt.span, required=True)
        src = self._lookup_name(stmt.source, stmt.span, required=True)
        if pred is None or src is None:
            return
        if pred is not PREDICTION:
            if pred is ID or stmt.prediction.lower() in RESERVED_IDENTITY_NAMES:
                self.errors.append(prediction_to_id_error(**loc))
                return
            self.errors.append(
                LabelError(
                    f"predict writes a PREDICTION, not {pred}.",
                    hint="PREDICTION success_probability",
                    **loc,
                )
            )
            return
        if src not in {STATE, TEMP, PATTERN, SIGNAL, PROCESS}:
            self.errors.append(
                LabelError(
                    f"A prediction must be grounded in STATE, PATTERN, or PROCESS, not {src}.",
                    hint="predict success_probability from learning_trend",
                    **loc,
                )
            )
            return
        self.notes.append(
            f"Predicted {stmt.prediction} from {stmt.source}. This remains a PREDICTION, not an identity."
        )

    def _lookup(self, stmt: LookupStmt) -> None:
        if isinstance(stmt.expr, SubscriptExpr):
            self._lookup_coords(stmt.expr, stmt.span)
            return
        name = stmt.expr.name
        label = self._lookup_name(name, stmt.span, required=True)
        if label is None:
            return
        if label not in {REGION, STRUCTURE, NETWORK, TRACT}:
            self.errors.append(
                LabelError(
                    f"lookup queries anatomical models, not {label}.",
                    hint="lookup frontal_lobe",
                    **self._loc(stmt.span),
                )
            )
            return
        region = self._find_region(name)
        if region is None and label in {REGION, STRUCTURE}:
            self.errors.append(
                CoordinateError(
                    "Coordinates do not exist.",
                    hint="load atlas before looking up a region",
                    **self._loc(stmt.span),
                )
            )
            return
        self.notes.append(f"Lookup {name}: coordinates resolved.")

    def _lookup_coords(self, expr: SubscriptExpr, span: Span) -> None:
        loc = self._loc(span)
        region = self._find_region(expr.name)
        if region is None:
            self.errors.append(coordinates_missing_error(expr.key, **loc))
            return
        landmarks = set(region.get("landmarks", {}).keys())
        landmarks.update({"centroid", "bounds", "min", "max"})
        if expr.key not in landmarks:
            suggestion = _closest(expr.key, landmarks)
            self.errors.append(
                CoordinateError(
                    "Coordinates do not exist.",
                    hint=suggestion or f"known landmarks: {', '.join(sorted(landmarks))}",
                    **loc,
                )
            )
            return
        self.notes.append(f"Lookup {expr.name}[{expr.key!r}]: coordinates resolved.")

    def _find_region(self, name: str) -> Optional[dict]:
        atlas = self.models.get("atlas") or {}
        for entry in atlas.get("regions", []):
            if entry.get("region") == name or entry.get("name") == name:
                return entry
        for entry in atlas.get("structures", []):
            if entry.get("structure") == name or entry.get("name") == name:
                return entry
        return None

    def _lookup_name(self, name: str, span: Span, required: bool = False) -> Optional[CognitionLabel]:
        if name in self.bindings:
            return self.bindings[name].label
        if name.upper() in FORBIDDEN_LABELS:
            return get_label(name.upper())
        if required:
            suggestion = _closest(name, self.bindings)
            extra = " load atlas/connectivity/function/behavior, or declare the name"
            self.errors.append(
                LabelError(
                    f"Unknown name {name!r}.",
                    hint=(suggestion + extra) if suggestion else f"declare it with a semantic label, or{extra}",
                    **self._loc(span),
                )
            )
        return None

    def _expr_label(self, expr) -> Optional[CognitionLabel]:
        if expr is None:
            return None
        if isinstance(expr, NameExpr):
            if expr.name in self.bindings:
                return self.bindings[expr.name].label
            return None
        return REGION

    def _loc(self, span: Span) -> dict:
        return {
            "filename": span.filename,
            "line": span.line,
            "column": span.column,
            "source_line": span.text,
        }


def _bindings_from_model(key: str, data: dict) -> list[tuple[str, Binding]]:
    out: list[tuple[str, Binding]] = []
    if key == "atlas":
        for entry in data.get("regions", []):
            name = entry.get("region") or entry.get("name")
            if name:
                out.append((name, Binding(name, REGION, "atlas", entry)))
        for entry in data.get("structures", []):
            name = entry.get("structure") or entry.get("name")
            if name:
                out.append((name, Binding(name, STRUCTURE, "atlas", entry)))
        for entry in data.get("networks", []):
            name = entry.get("network") or entry.get("name")
            if name:
                out.append((name, Binding(name, NETWORK, "atlas", entry)))
    elif key == "connectivity":
        for entry in data.get("tracts", []):
            name = entry.get("tract") or entry.get("name")
            if name:
                out.append((name, Binding(name, TRACT, "connectivity", entry)))
        for entry in data.get("connections", []):
            name = entry.get("connection") or entry.get("name")
            if name:
                out.append((name, Binding(name, CONNECTION, "connectivity", entry)))
        for entry in data.get("networks", []):
            name = entry.get("network") or entry.get("name")
            if name:
                out.append((name, Binding(name, NETWORK, "connectivity", entry)))
    elif key == "function":
        for entry in data.get("functions", []):
            name = entry.get("function") or entry.get("name")
            if name:
                out.append((name, Binding(name, FUNCTION, "function", entry)))
        for entry in data.get("processes", []):
            name = entry.get("process") or entry.get("name")
            if name:
                out.append((name, Binding(name, PROCESS, "function", entry)))
        for entry in data.get("signals", []):
            name = entry.get("signal") or entry.get("name")
            if name:
                out.append((name, Binding(name, SIGNAL, "function", entry)))
        for entry in data.get("networks", []):
            name = entry.get("network") or entry.get("name")
            if name:
                out.append((name, Binding(name, NETWORK, "function", entry)))
    elif key == "behavior":
        for entry in data.get("behaviors", []):
            name = entry.get("behavior") or entry.get("name")
            if name:
                out.append((name, Binding(name, STATE, "behavior", entry)))
            observed = entry.get("observed_state")
            if observed:
                out.append((observed, Binding(observed, STATE, "behavior", entry)))
        for entry in data.get("patterns", []):
            name = entry.get("pattern") or entry.get("name")
            if name:
                out.append((name, Binding(name, PATTERN, "behavior", entry)))
    return out


def _closest(name: str, pool) -> Optional[str]:
    keys = list(pool) if not isinstance(pool, dict) else list(pool.keys())
    matches = difflib.get_close_matches(name, [str(k) for k in keys], n=1, cutoff=0.6)
    return matches[0] if matches else None


def _looks_like_coordinate(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ("coordinate", "location", "voxel", "xyz"))


def _conversion_hint(source: CognitionLabel, target: CognitionLabel) -> str:
    if source is REGION and target is FUNCTION:
        return "associate the function with a network model?"
    if source is PREDICTION and target is ID:
        return "keep the estimate as PREDICTION"
    if source in {STATE, TEMP, PATTERN} and target is ID:
        return "a measurement is not an identity"
    if target is NETWORK:
        return f"build a NETWORK from connected REGION values instead of converting {source}"
    if source is FUNCTION:
        return "associate the function with a NETWORK, do not recast it"
    return f"keep {source} as {source}, and keep {target} as {target}"
