# Copyright (C) 2026 Disquietude
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Rewrite a PSCF diblock parameter file for one candidate.

PSCF's vendored diblock examples have no separate degree of polymerization.
Block lengths sum to 1 and the ``chi`` entry is χN at that reference length.
"""

from __future__ import annotations

import re

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_HELMHOLTZ = re.compile(rf"(?m)^fHelmholtz\s+({_NUMBER})\s*$")


def rewrite_diblock_param(text: str, f_a: float, chi_n: float) -> str:
    """Set block lengths to ``f_a`` and ``1-f_a``, and set ``chi`` to ``chi_n``."""
    if not 0.0 < f_a < 1.0:
        raise ValueError("f_a must be strictly between 0 and 1")
    f_b = 1.0 - f_a
    lines = text.splitlines(keepends=True)
    in_blocks = False
    in_chi = False
    block_index = 0
    wrote_blocks = 0
    wrote_chi = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        newline = "\n" if line.endswith("\n") else ""
        indent = line[: len(line) - len(line.lstrip(" \t"))]
        if stripped.startswith("blocks["):
            in_blocks = True
            block_index = 0
            out.append(line)
            continue
        if in_blocks:
            if stripped.startswith("]"):
                in_blocks = False
                out.append(line)
                continue
            if block_index < 2 and stripped[:1] in {"0", "1"}:
                value = f_a if block_index == 0 else f_b
                out.append(f"{indent}{block_index}   {value:.10g}{newline}")
                block_index += 1
                wrote_blocks += 1
                continue
        if stripped.startswith("chi("):
            in_chi = True
            out.append(line)
            continue
        if in_chi:
            if stripped.startswith(")"):
                in_chi = False
                out.append(line)
                continue
            if stripped:
                out.append(f"{indent}1   0   {chi_n:.10g}{newline}")
                wrote_chi = True
                continue
        out.append(line)
    if wrote_blocks != 2 or not wrote_chi:
        raise ValueError("PSCF param file is missing a diblock blocks[] or chi() entry")
    return "".join(out)


def parse_f_helmholtz(log_text: str) -> float | None:
    """Return the last ``fHelmholtz`` value printed by pscf_rpc, if any."""
    matches = _HELMHOLTZ.findall(log_text)
    if not matches:
        return None
    return float(matches[-1])


def iteration_converged(log_text: str) -> bool:
    """True when the Anderson mixer reports convergence and not a failure."""
    if "Iterator failed to converge." in log_text:
        return False
    return "Converged" in log_text
