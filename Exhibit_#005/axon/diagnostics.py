"""Axon diagnostics for Ranvier semantic errors.

The compiler already produces Python-like reports. This module restates them
as IDLE-style diagnostic cards so a REGION/FUNCTION mix-up is obvious at a glance.
"""

from __future__ import annotations

from typing import Sequence

from ranvier.errors import CognitionError


def format_diagnostic(error: CognitionError) -> str:
    """Return one diagnostic card."""
    kind = getattr(error, "error_type", None) or type(error).__name__
    source = (error.source_line or "").strip()
    location = _location(error)

    if kind == "LabelError":
        return _label_card(error, source, location)
    if kind == "ProphecyError":
        return _prophecy_card(error, source, location)
    if kind == "AttributionError":
        return _card(
            "AttributionError",
            location,
            source,
            "Insufficient causal model.",
            "One observed behaviour is not an entire cause.",
            error.hint or "consider environmental, biological, and contextual factors.",
        )
    if kind == "CoordinateError":
        return _card(
            "CoordinateError",
            location,
            source,
            "Coordinates do not exist.",
            error.message,
            error.hint,
        )
    if kind == "ModelError":
        return _card("ModelError", location, source, error.message, None, error.hint)
    if kind in {"ValueError", "SyntaxError"}:
        return _card(kind, location, source, error.message, None, error.hint)
    return _card(kind, location, source, error.message, None, error.hint)


def format_diagnostics(errors: Sequence[CognitionError]) -> str:
    if not errors:
        return "No diagnostics.\n\nNever compile a destiny when you only measured a state."
    cards = [format_diagnostic(err) for err in errors]
    n = len(errors)
    suffix = "diagnostic" if n == 1 else "diagnostics"
    cards.append(f"{n} {suffix}. Ranvier refused to compile a destiny.")
    return "\n\n".join(cards)


def _label_card(error: CognitionError, source: str, location: str) -> str:
    detail = "Invalid semantic assignment."
    rule = error.message
    suggestion = error.hint or "associate function with network model."
    message = error.message.lower()
    if "cognitive function directly to anatomical region" in message or (
        "FUNCTION" in source.upper() and "=" in source
    ):
        rule = "FUNCTION cannot directly equal REGION."
        suggestion = "associate function with network model."
    return _card(
        "LabelError",
        location,
        source,
        detail,
        rule,
        suggestion,
    )


def _prophecy_card(error: CognitionError, source: str, location: str) -> str:
    return _card(
        "ProphecyError",
        location,
        source,
        "Prediction cannot become identity.",
        error.message,
        error.hint,
    )


def _card(
    title: str,
    location: str,
    source: str,
    headline: str,
    body: str | None,
    suggestion: str | None,
) -> str:
    parts = [title]
    if location:
        parts.append(location)
    parts.extend(["", headline])
    if body and body != headline:
        parts.extend(["", body])
    if source:
        parts.extend(["", source])
    if suggestion:
        parts.extend(["", "Suggested:", suggestion])
    return "\n".join(parts)


def _location(error: CognitionError) -> str:
    if error.filename and error.line is not None:
        return f"File {error.filename}, line {error.line}"
    if error.line is not None:
        return f"Line {error.line}"
    return ""
