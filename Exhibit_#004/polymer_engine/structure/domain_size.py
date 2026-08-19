"""
Domain spacing and characteristic length estimates.

Uses textbook polymer scaling relations with clearly labeled assumptions.
This is NOT an SCFT or experimental fit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

from polymer_engine.thermodynamics.flory_huggins import (
    INTERMEDIATE_SEGREGATION_UPPER,
    SYMMETRIC_DIBLOCK_ODT_CHIN,
    WEAK_SEGREGATION_UPPER,
)

# Educational default statistical segment length (nm).
DEFAULT_SEGMENT_LENGTH_NM = 0.50

# Leibler peak for symmetric diblocks: q* R_g ≈ 1.95 (mean-field WSL).
LEIBLER_QSTAR_RG = 1.95

# Order-1 prefactor for strong-segregation lamellar scaling D/a ~ χ^{1/6} N^{2/3}.
SSL_PREFACTOR = 1.10


@dataclass
class DomainSizeResult:
    domain_spacing_nm: float | None
    characteristic_length_nm: float
    radius_of_gyration_nm: float
    model: str
    assumptions: list[str]
    explanation: list[str] = field(default_factory=list)
    segment_length_nm: float = DEFAULT_SEGMENT_LENGTH_NM


def radius_of_gyration_nm(N: float, a_nm: float = DEFAULT_SEGMENT_LENGTH_NM) -> float:
    """Ideal-chain radius of gyration: R_g = a * sqrt(N/6)."""
    if N <= 0:
        raise ValueError("N must be > 0")
    if a_nm <= 0:
        raise ValueError("segment length a must be > 0")
    return a_nm * sqrt(N / 6.0)


class DomainSizeEstimator:
    """
    Estimate domain spacing D and a characteristic coil size R_g.

    Regime selection (educational thresholds already used in this package):
      χN < χN_ODT     → disordered: no microdomain spacing; report R_g only
      ODT ≤ χN < 50   → weak / intermediate: WSL-like D ~ N^{1/2}
      χN ≥ 50         → strong segregation: SSL-like D ~ a χ^{1/6} N^{2/3}
    """

    def __init__(self, segment_length_nm: float = DEFAULT_SEGMENT_LENGTH_NM) -> None:
        if segment_length_nm <= 0:
            raise ValueError("segment_length_nm must be > 0")
        self.segment_length_nm = segment_length_nm

    def estimate(
        self,
        *,
        N: float,
        chi: float,
        chiN: float,
        morphology: str,
        f_minor: float | None = None,
    ) -> DomainSizeResult:
        a = self.segment_length_nm
        rg = radius_of_gyration_nm(N, a)
        assumptions = [
            f"Statistical segment length a = {a:.3g} nm (default educational value unless overridden).",
            "Ideal-chain R_g = a * sqrt(N/6); conformational asymmetry neglected.",
            "Prefactors are order-1 educational constants, not chemistry-specific fits.",
            "Cylinders/spheres/gyroids use the same scaling form as lamellae with a simple morphology factor.",
        ]

        explanation = [
            f"R_g = a*sqrt(N/6) = {a:.3g}*sqrt({N:.4g}/6) = {rg:.4g} nm",
        ]

        if chiN < SYMMETRIC_DIBLOCK_ODT_CHIN:
            return DomainSizeResult(
                domain_spacing_nm=None,
                characteristic_length_nm=rg,
                radius_of_gyration_nm=rg,
                model="disordered (no microdomain spacing; coil size only)",
                assumptions=assumptions,
                explanation=explanation
                + [
                    f"χN = {chiN:.4g} < χN_ODT ≈ {SYMMETRIC_DIBLOCK_ODT_CHIN}: "
                    "no ordered domain spacing is predicted.",
                ],
                segment_length_nm=a,
            )

        morph_factor, morph_note = self._morphology_factor(morphology)
        explanation.append(morph_note)

        if chiN >= INTERMEDIATE_SEGREGATION_UPPER:
            # Strong segregation scaling (Semenov-like): D ~ a χ^{1/6} N^{2/3}
            if chi <= 0:
                raise ValueError("chi must be > 0 for strong-segregation spacing")
            d_lam = SSL_PREFACTOR * a * (chi ** (1.0 / 6.0)) * (N ** (2.0 / 3.0))
            spacing = morph_factor * d_lam
            model = "strong segregation scaling approximation"
            explanation.extend(
                [
                    "Strong-segregation model:",
                    f"  D_lam/a ≈ {SSL_PREFACTOR} * χ^(1/6) * N^(2/3)",
                    f"  D_lam = {d_lam:.4g} nm",
                    f"  D = morphology_factor * D_lam = {morph_factor:.3g} * {d_lam:.4g} = {spacing:.4g} nm",
                ]
            )
            assumptions.append(
                "SSL formula is the classic lamellar scaling; applied here as an educational estimate."
            )
        else:
            # Weak / intermediate: Leibler peak spacing D = 2π / q* with q* R_g ≈ 1.95
            d_lam = (2.0 * 3.141592653589793 / LEIBLER_QSTAR_RG) * rg
            spacing = morph_factor * d_lam
            if chiN < WEAK_SEGREGATION_UPPER:
                model = "weak segregation scaling approximation"
            else:
                model = "intermediate segregation (WSL-like spacing approximation)"
            explanation.extend(
                [
                    f"{model}:",
                    f"  Assume q* R_g ≈ {LEIBLER_QSTAR_RG} (symmetric diblock mean-field peak).",
                    f"  D_lam = 2π R_g / {LEIBLER_QSTAR_RG} = {d_lam:.4g} nm",
                    f"  D = morphology_factor * D_lam = {morph_factor:.3g} * {d_lam:.4g} = {spacing:.4g} nm",
                ]
            )
            assumptions.append(
                "WSL spacing ignores higher-order χN corrections near the ODT."
            )

        if f_minor is not None:
            assumptions.append(
                f"Composition f_minor = {f_minor:.3f} is not used in the scaling prefactor "
                "(future models may add f-dependence)."
            )

        return DomainSizeResult(
            domain_spacing_nm=spacing,
            characteristic_length_nm=spacing,
            radius_of_gyration_nm=rg,
            model=model,
            assumptions=assumptions,
            explanation=explanation,
            segment_length_nm=a,
        )

    @staticmethod
    def _morphology_factor(morphology: str) -> tuple[float, str]:
        key = morphology.lower()
        if "lamella" in key:
            return 1.0, "Morphology factor = 1.00 (lamellae reference)."
        if "gyroid" in key:
            return 1.05, "Morphology factor = 1.05 (gyroid; crude relative to lamellae)."
        if "cylinder" in key:
            return 1.10, "Morphology factor = 1.10 (cylinders; crude hexagonal-spacing proxy)."
        if "sphere" in key:
            return 1.15, "Morphology factor = 1.15 (spheres; crude BCC-spacing proxy)."
        return 1.0, f"Morphology factor = 1.00 (default; morphology='{morphology}')."
