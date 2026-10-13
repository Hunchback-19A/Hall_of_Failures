"""χN and segregation-regime classification (Flory–Huggins based)."""

from __future__ import annotations

from dataclasses import dataclass

# Mean-field Leibler ODT for a symmetric (f = 0.5) AB diblock melt.
SYMMETRIC_DIBLOCK_ODT_CHIN = 10.495

# Rough educational bands (not exact SST/WST boundaries).
WEAK_SEGREGATION_UPPER = 30.0
INTERMEDIATE_SEGREGATION_UPPER = 50.0


@dataclass
class ChiNResult:
    chi: float
    N: float
    chiN: float
    segregation_regime: str
    explanation: list[str]


def compute_chiN(chi: float, N: float) -> ChiNResult:
    """
    Compute segregation strength χN.

    Physically, χ measures unlike-contact enthalpy (per segment), while N is
    the degree of polymerization. Their product sets the drive for
    microphase separation relative to entropic mixing.
    """
    if chi < 0:
        raise ValueError("chi must be >= 0")
    if N <= 0:
        raise ValueError("N must be > 0")

    chiN = chi * N
    steps = [
        f"χN = χ × N = {chi:.4g} × {N:.4g} = {chiN:.4g}",
        f"Reference mean-field ODT for a symmetric diblock: χN_ODT ≈ {SYMMETRIC_DIBLOCK_ODT_CHIN}",
    ]

    if chiN < SYMMETRIC_DIBLOCK_ODT_CHIN:
        regime = "disordered / mixed"
        steps.append(
            f"χN ({chiN:.3f}) is below χN_ODT ({SYMMETRIC_DIBLOCK_ODT_CHIN}); "
            "mean-field theory predicts a disordered melt."
        )
    elif chiN < WEAK_SEGREGATION_UPPER:
        regime = "weak segregation"
        steps.append(
            f"χN ({chiN:.3f}) is above ODT but below ~{WEAK_SEGREGATION_UPPER}; "
            "interfaces are broad (weak-segregation picture)."
        )
    elif chiN < INTERMEDIATE_SEGREGATION_UPPER:
        regime = "intermediate segregation"
        steps.append(
            f"χN ({chiN:.3f}) lies in an intermediate window "
            f"(~{WEAK_SEGREGATION_UPPER}–{INTERMEDIATE_SEGREGATION_UPPER})."
        )
    else:
        regime = "strong segregation"
        steps.append(
            f"χN ({chiN:.3f}) is large; domains are sharply segregated "
            "(strong-segregation / narrow-interface picture)."
        )

    return ChiNResult(
        chi=chi,
        N=N,
        chiN=chiN,
        segregation_regime=regime,
        explanation=steps,
    )
