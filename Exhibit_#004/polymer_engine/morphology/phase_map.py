"""
Simplified composition windows for classical AB diblock morphologies.

Educational fixed windows inspired by the Matsen–Bates mean-field picture.
This is NOT a full SCFT phase diagram.
"""

from __future__ import annotations

# Approximate composition windows for an ordered AB diblock.
SPHERE_MAX = 0.17
CYLINDER_MAX = 0.32
GYROID_MAX = 0.37
# 0.37–0.50 (and symmetric) → lamellae


def ordered_morphology_from_f(f_minor: float) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if f_minor < SPHERE_MAX:
        morph = "spheres"
        reasons.append(
            f"Minority volume fraction f_minor = {f_minor:.3f} < {SPHERE_MAX}: "
            "high interfacial curvature favors discrete spherical domains."
        )
    elif f_minor < CYLINDER_MAX:
        morph = "cylinders"
        reasons.append(
            f"f_minor = {f_minor:.3f} is in ~[{SPHERE_MAX}, {CYLINDER_MAX}): "
            "hexagonally packed cylinders are typical."
        )
    elif f_minor < GYROID_MAX:
        morph = "gyroid"
        reasons.append(
            f"f_minor = {f_minor:.3f} is in the narrow network window "
            f"~[{CYLINDER_MAX}, {GYROID_MAX}): double-gyroid is often stable."
        )
    else:
        morph = "lamellae"
        reasons.append(
            f"f_minor = {f_minor:.3f} ≥ {GYROID_MAX}: near-symmetric composition "
            "favors flat interfaces (lamellae)."
        )
    return morph, reasons


def near_boundary(f_minor: float, tol: float = 0.02) -> bool:
    for edge in (SPHERE_MAX, CYLINDER_MAX, GYROID_MAX, 0.5):
        if abs(f_minor - edge) <= tol:
            return True
    return False
