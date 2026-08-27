"""Ranvier errors.

Python's type system stops ``"text" + 5``.
Ranvier's type system stops ``prediction = identity``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass
class CognitionError(Exception):
    """Base error for the Ranvier language."""

    message: str
    hint: Optional[str] = None
    filename: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    source_line: Optional[str] = None
    error_type: str = field(default="CognitionError", init=False)

    def __post_init__(self) -> None:
        name = type(self).__name__
        self.error_type = "ValueError" if name == "CognitionValueError" else name

    def __str__(self) -> str:
        return self.format_report()

    def format_report(self) -> str:
        location = ""
        if self.filename and self.line is not None:
            location = f'  File "{self.filename}", line {self.line}\n'
        elif self.line is not None:
            location = f"  Line {self.line}\n"

        caret = ""
        if self.source_line is not None:
            caret = f"    {self.source_line.rstrip()}\n"
            if self.column is not None:
                caret += f"    {' ' * max(self.column - 1, 0)}^\n"

        kind = getattr(self, "error_type", None) or type(self).__name__
        hint = f"\n  Did you mean:\n    {self.hint}" if self.hint else ""
        return f"{location}{caret}{kind}: {self.message}{hint}"


class LabelError(CognitionError):
    """Invalid conversion between semantic labels, e.g. REGION → FUNCTION."""


class CognitionValueError(CognitionError):
    """A value is the wrong kind of thing for this operation.

    Named CognitionValueError so it does not shadow the builtin ValueError.
    The language still prints it as ``ValueError``.
    """


class ModelError(CognitionError):
    """A brain data model is missing, inconsistent, or conceptually unsafe."""


class CoordinateError(CognitionError):
    """A requested anatomical coordinate or landmark does not exist."""


class AttributionError(CognitionError):
    """A single observation was treated as a complete cause."""


class ProphecyError(CognitionError):
    """A prediction was treated as a permanent classification."""


def region_to_function_error(**kwargs) -> LabelError:
    return LabelError(
        "Cannot assign cognitive function directly to anatomical region.",
        hint="associate the function with a network model?",
        **kwargs,
    )


def function_to_region_error(**kwargs) -> LabelError:
    return LabelError(
        "Cannot assign an anatomical region directly to a cognitive function.",
        hint="associate the function with a network model, not a single region?",
        **kwargs,
    )


def structure_to_personality_error(**kwargs) -> LabelError:
    return LabelError(
        "Cannot compile personality from physical structure.",
        hint="keep anatomy as STRUCTURE or REGION, and keep traits uncompiled?",
        **kwargs,
    )


def state_to_id_error(**kwargs) -> LabelError:
    return LabelError(
        "A measured condition cannot become a persistent identity.",
        hint="keep the measurement as STATE, or describe a PATTERN over time?",
        **kwargs,
    )


def prediction_to_id_error(**kwargs) -> ProphecyError:
    return ProphecyError(
        "Future estimate cannot become permanent classification.",
        hint="keep the estimate as PREDICTION, and update a STATE only after a new measurement?",
        **kwargs,
    )


def destiny_error(**kwargs) -> ProphecyError:
    return ProphecyError(
        "Future estimate cannot become permanent classification.",
        hint="declare PREDICTION, not DESTINY. Ranvier does not compile destiny.",
        **kwargs,
    )


def coordinates_missing_error(location: str, **kwargs) -> CoordinateError:
    return CoordinateError(
        "Coordinates do not exist.",
        hint=f"lookup a known landmark of this region instead of {location!r}?",
        **kwargs,
    )


def attribution_error(**kwargs) -> AttributionError:
    return AttributionError(
        "Insufficient causal model.",
        hint="consider environmental, biological, and contextual factors.",
        **kwargs,
    )


def format_error_block(errors: Sequence[CognitionError]) -> str:
    parts = [err.format_report() for err in errors]
    n = len(errors)
    suffix = "error" if n == 1 else "errors"
    parts.append(f"\nRanvier compilation failed: {n} {suffix}.")
    parts.append('Never compile a destiny when you only measured a state.')
    return "\n\n".join(parts)
