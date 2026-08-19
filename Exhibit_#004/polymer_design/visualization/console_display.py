"""Compatibility shim — default console output uses scientific reports."""

from __future__ import annotations

from polymer_engine.reporting.scientific_report import format_prediction_scientific_report
from polymer_engine.output.report_generator import format_report as format_technical_report

# Keep technical formatter importable; primary console path is scientific.
format_report = format_prediction_scientific_report


def print_report(prediction, show_calculations: bool = True) -> None:
    print(format_prediction_scientific_report(prediction, show_calculations=show_calculations))


__all__ = ["format_report", "print_report", "format_technical_report"]
