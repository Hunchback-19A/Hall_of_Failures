"""Compatibility shim — logic lives in polymer_engine.morphology."""

from polymer_engine.morphology.morphology_prediction import (
    MorphologyPredictor,
    MorphologyResult,
)
from polymer_engine.morphology.phase_map import (
    CYLINDER_MAX as _CYLINDER_MAX,
    GYROID_MAX as _GYROID_MAX,
    SPHERE_MAX as _SPHERE_MAX,
    near_boundary as _near_boundary,
    ordered_morphology_from_f as _ordered_morphology_from_f,
)

__all__ = [
    "MorphologyPredictor",
    "MorphologyResult",
    "_SPHERE_MAX",
    "_CYLINDER_MAX",
    "_GYROID_MAX",
    "_ordered_morphology_from_f",
    "_near_boundary",
]
