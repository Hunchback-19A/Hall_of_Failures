"""
Traceable scientific interpretation of existing numerical outputs.

No new physics: statements must cite numerical fields already computed
(χN, ODT reference, amplitudes, domain spacing, solver class, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from polymer_engine.thermodynamics.flory_huggins import (
    INTERMEDIATE_SEGREGATION_UPPER,
    SYMMETRIC_DIBLOCK_ODT_CHIN,
    WEAK_SEGREGATION_UPPER,
)


@dataclass
class InterpretedClaim:
    """One interpretation with an explicit numerical reason."""

    interpretation: str
    reason: str


@dataclass
class ScientificInterpretation:
    system: str
    numerical_state: str
    claims: list[InterpretedClaim] = field(default_factory=list)
    predicted_behavior: InterpretedClaim | None = None
    structure_indication: InterpretedClaim | None = None
    design_relevance: InterpretedClaim | None = None
    confidence: InterpretedClaim | None = None
    is_toy_field_model: bool = False

    def claim_lines(self) -> list[str]:
        lines: list[str] = []
        for claim in self.claims:
            lines.append("Interpretation:")
            lines.append(claim.interpretation)
            lines.append("")
            lines.append("Reason:")
            lines.append(claim.reason)
            lines.append("")
        for label, claim in (
            ("Predicted behavior", self.predicted_behavior),
            ("Structure indication", self.structure_indication),
            ("Design relevance", self.design_relevance),
            ("Confidence", self.confidence),
        ):
            if claim is None:
                continue
            lines.append(f"{label}:")
            lines.append(claim.interpretation)
            lines.append("")
            lines.append("Reason:")
            lines.append(claim.reason)
            lines.append("")
        return lines


def _is_toy_morphology_label(label: str) -> bool:
    s = label.lower()
    return s.startswith("toy-") or "toy field" in s or "order-parameter" in s


def _segregation_claim(chiN: float) -> InterpretedClaim:
    odt = SYMMETRIC_DIBLOCK_ODT_CHIN
    if chiN < odt:
        return InterpretedClaim(
            interpretation=(
                "System remains in a disordered/mixed regime according to the selected model."
            ),
            reason=(
                f"χN = {chiN:.4g} is below the selected mean-field ODT reference "
                f"χN_ODT ≈ {odt} for a symmetric AB diblock."
            ),
        )
    if chiN < WEAK_SEGREGATION_UPPER:
        regime = "weak segregation"
    elif chiN < INTERMEDIATE_SEGREGATION_UPPER:
        regime = "intermediate segregation"
    else:
        regime = "strong segregation"
    return InterpretedClaim(
        interpretation="Segregation is favored under this model.",
        reason=(
            f"χN = {chiN:.4g} exceeds the selected ODT reference ≈ {odt} "
            f"({regime} window in this package's educational banding)."
        ),
    )


def interpret_prediction(prediction: Any) -> ScientificInterpretation:
    """Build interpretation from a SimplifiedPhysicsEvaluator Prediction."""
    polymer = prediction.polymer
    system = f"{polymer.name} ({polymer.architecture})"
    chiN = float(prediction.chiN)
    claims = [_segregation_claim(chiN)]

    morph = str(prediction.morphology)
    if _is_toy_morphology_label(morph):
        structure = InterpretedClaim(
            interpretation=(
                "Periodic composition modulation indicated only as a numerical field feature "
                "(not a classical polymer mesophase assignment)."
            ),
            reason=f"Engine morphology label = '{morph}'.",
        )
        is_toy = True
    else:
        if "disordered" in morph.lower() or "mixed" in morph.lower():
            structure = InterpretedClaim(
                interpretation=(
                    "No ordered microdomain morphology is assigned under the classical "
                    "educational phase map."
                ),
                reason=(
                    f"Predicted label = '{morph}'; segregation regime = "
                    f"'{prediction.segregation_regime}'."
                ),
            )
        else:
            structure = InterpretedClaim(
                interpretation=(
                    f"Classical educational phase map indicates a '{morph}' window "
                    f"for the mapped composition."
                ),
                reason=(
                    f"f_minor context and χN = {chiN:.4g} place the state in the "
                    f"'{morph}' rule-based window (not an SCFT free-energy ranking)."
                ),
            )
        is_toy = False

    spacing = getattr(prediction, "domain_spacing_nm", None)
    if spacing is not None:
        claims.append(
            InterpretedClaim(
                interpretation=(
                    f"Estimated characteristic microdomain spacing is approximately {spacing:.3g} nm."
                ),
                reason=(
                    f"Domain-size module returned D = {spacing:.3g} nm "
                    f"(model: {getattr(prediction, 'domain_size_model', 'n/a')})."
                ),
            )
        )
    else:
        claims.append(
            InterpretedClaim(
                interpretation=(
                    "No microdomain lattice spacing is reported for this state."
                ),
                reason=(
                    "domain_spacing_nm is unavailable (typically disordered/mixed under "
                    "the spacing model)."
                ),
            )
        )

    predicted = InterpretedClaim(
        interpretation=(
            "Composition fluctuations remain mixed-like."
            if chiN < SYMMETRIC_DIBLOCK_ODT_CHIN
            else "Composition fluctuations are expected to develop into a segregated melt state "
            "under the selected mean-field picture."
        ),
        reason=(
            f"Segregation regime reported by thermodynamics module: "
            f"'{prediction.segregation_regime}'."
        ),
    )

    design = InterpretedClaim(
        interpretation=(
            "Increasing χN (via χ or N) moves the design toward stronger segregation; "
            "morphology selection still depends on composition and model dimensionality."
            if chiN >= SYMMETRIC_DIBLOCK_ODT_CHIN
            else "Raising χN above the ODT reference is the primary route to enter an ordered "
            "window in this model family."
        ),
        reason=(
            f"Current state: χ = {prediction.chi:.4g}, N = {prediction.N:.4g}, "
            f"χN = {chiN:.4g}; architecture = {polymer.architecture}."
        ),
    )

    confidence = InterpretedClaim(
        interpretation=f"{prediction.confidence}",
        reason=(
            f"Evaluator confidence_score = {prediction.confidence_score:.2f} "
            f"(engine = {prediction.engine})."
        ),
    )

    return ScientificInterpretation(
        system=system,
        numerical_state=f"χN = {chiN:.4g}",
        claims=claims,
        predicted_behavior=predicted,
        structure_indication=structure,
        design_relevance=design,
        confidence=confidence,
        is_toy_field_model=is_toy,
    )


def interpret_simulation(
    output: Any,
    *,
    sim_input: Any | None = None,
) -> ScientificInterpretation:
    """Build interpretation from SimulationOutput (+ optional SimulationInput)."""
    solver = str(getattr(output, "solver_name", "unknown"))
    chiN = float(output.chiN)
    is_toy = solver == "phase_field" or _is_toy_morphology_label(str(output.morphology))

    if sim_input is not None:
        fracs = getattr(sim_input, "volume_fractions", None) or []
        frac_txt = ", ".join(f"{x:.3f}" for x in fracs) if fracs else "n/a"
        if solver == "scft":
            fA = f"{float(fracs[0]):.3f}" if fracs else "n/a"
            system = (
                f"{getattr(sim_input, 'name', 'simulation')} "
                f"(AB diblock mean-field SCFT; f_A = {fA})"
            )
        else:
            system = (
                f"{getattr(sim_input, 'name', 'simulation')} "
                f"({getattr(sim_input, 'architecture', 'n/a')}; f = [{frac_txt}])"
            )
            if is_toy:
                system += " — toy field simulation"
    else:
        system = f"Simulation via '{solver}'"
        if is_toy:
            system += " — toy field simulation"
        if solver == "scft":
            system += " — mean-field SCFT"

    claims = [_segregation_claim(chiN)]

    if is_toy:
        amp = None
        if isinstance(getattr(output, "structure", None), dict):
            amp = output.structure.get("phi_amplitude")
        structure = InterpretedClaim(
            interpretation=(
                "Periodic composition modulation detected in the toy field model."
                if (amp is not None and float(amp) >= 0.20)
                else "Weak order-parameter contrast in the toy field model "
                "(mixed-like numerical state)."
            ),
            reason=(
                f"Solver morphology label = '{output.morphology}'"
                + (f"; φ amplitude = {float(amp):.4g}." if amp is not None else ".")
                + " This is not a classical lamellae/cylinders/gyroid assignment."
            ),
        )
        predicted = InterpretedClaim(
            interpretation=(
                "The 1D field develops spatial composition contrast under the imposed "
                "segregation drive, within the limits of the toy PDE."
                if chiN >= SYMMETRIC_DIBLOCK_ODT_CHIN
                else "The toy field remains weakly contrasted relative to a strongly driven run."
            ),
            reason=(
                f"χN = {chiN:.4g}; energy = {float(output.energy):.6g}; "
                f"solver = {solver}."
            ),
        )
        design = InterpretedClaim(
            interpretation=(
                "Higher segregation strength can increase domain contrast in this toy PDE, "
                "but morphology design for real block copolymers requires appropriate "
                "dimensional / SCFT-class models."
            ),
            reason=(
                "Phase-field backend is an architectural demonstration "
                f"(method: {output.method_details.get('method', 'n/a')})."
            ),
        )
        conf_txt = "Low–Medium"
        conf_reason = (
            "Toy 1D Cahn–Hilliard demonstration without chain connectivity or SCFT free-energy "
            "comparison among classical mesophases."
        )
    elif solver == "scft":
        amp = None
        iters = None
        resid = None
        if isinstance(getattr(output, "structure", None), dict):
            amp = output.structure.get("phi_A_amplitude")
        if isinstance(getattr(output, "convergence", None), dict):
            iters = output.convergence.get("iterations")
            resid = output.convergence.get("residual")
        if amp is not None and float(amp) >= 0.02:
            structure = InterpretedClaim(
                interpretation=(
                    "Composition modulation increased under the current mean-field SCFT model "
                    "(1D density wave)."
                ),
                reason=(
                    f"φ_A amplitude = {float(amp):.4g}; morphology label = '{output.morphology}'. "
                    "1D SCFT cannot assign cylinders/gyroid; it indicates segregation into "
                    "A/B-rich domains along one periodic direction."
                ),
            )
        else:
            structure = InterpretedClaim(
                interpretation=(
                    "Density field remains near-homogeneous under the current mean-field SCFT model."
                ),
                reason=(
                    f"φ_A amplitude = {float(amp) if amp is not None else float('nan'):.4g}; "
                    f"label = '{output.morphology}'."
                ),
            )
        predicted = InterpretedClaim(
            interpretation=(
                "Microphase segregation is favored and a spatially modulated density profile "
                "is obtained from self-consistent chain statistics."
                if (amp is not None and float(amp) >= 0.02)
                else "The self-consistent solution remains weakly modulated / near mixed."
            ),
            reason=(
                f"χN = {chiN:.4g}; SCFT free energy F = {float(output.energy):.6g}; "
                f"iterations = {iters}; residual = {resid}."
            ),
        )
        design = InterpretedClaim(
            interpretation=(
                "Increasing χN strengthens segregation in this SCFT model; resolving classical "
                "3D morphologies requires 2D/3D unit-cell calculations and structure comparison."
            ),
            reason=(
                f"method = {output.method_details.get('method', 'n/a')}; "
                f"f_A = {output.structure.get('f_A', 'n/a')}."
            ),
        )
        conf_txt = "Medium"
        conf_reason = (
            "Gaussian-chain mean-field SCFT on a 1D periodic grid — physically meaningful for "
            "segregation/ODT trends, not for full morphology identification."
        )
    else:
        morph = str(output.morphology)
        structure = InterpretedClaim(
            interpretation=(
                f"Analytical/educational morphology indication: '{morph}'."
            ),
            reason=(
                f"AnalyticalSolver returned morphology = '{morph}' at χN = {chiN:.4g}."
            ),
        )
        spacing = None
        if isinstance(getattr(output, "structure", None), dict):
            spacing = output.structure.get("domain_spacing_nm")
        if spacing is not None:
            claims.append(
                InterpretedClaim(
                    interpretation=(
                        f"Estimated characteristic length scale is approximately {float(spacing):.3g} nm."
                    ),
                    reason=(
                        f"structure['domain_spacing_nm'] = {float(spacing):.3g} "
                        f"(model: {output.structure.get('domain_size_model', 'n/a')})."
                    ),
                )
            )
        predicted = InterpretedClaim(
            interpretation=(
                "Segregated microdomain formation is indicated by the analytical engine."
                if chiN >= SYMMETRIC_DIBLOCK_ODT_CHIN
                else "A mixed melt is indicated by the analytical engine."
            ),
            reason=f"χN = {chiN:.4g} relative to ODT ≈ {SYMMETRIC_DIBLOCK_ODT_CHIN}.",
        )
        design = InterpretedClaim(
            interpretation=(
                "Composition (f) and χN jointly control the educational morphology window; "
                "treat assignments as map-based, not SCFT-ranked."
            ),
            reason=f"solver = {solver}; free-energy proxy energy = {float(output.energy):.6g}.",
        )
        conf_txt = "Medium"
        conf_reason = (
            "Closed-form / rule-based analytical path; transparent but not a field-theoretic "
            "free-energy minimization among competing mesophases."
        )

    confidence = InterpretedClaim(interpretation=conf_txt, reason=conf_reason)

    return ScientificInterpretation(
        system=system,
        numerical_state=(
            f"χN = {chiN:.4g}"
            if solver != "scft"
            else f"χN = {chiN:.4g}; iterations/residual reported in Numerical details"
        ),
        claims=claims,
        predicted_behavior=predicted,
        structure_indication=structure,
        design_relevance=design,
        confidence=confidence,
        is_toy_field_model=is_toy,
    )
