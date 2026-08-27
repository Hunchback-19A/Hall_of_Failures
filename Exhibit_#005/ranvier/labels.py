"""Ranvier semantic labels.

These are analogous to Python data types, but they name the *category of
information* being modeled — not a storage layout and not a claim about
consciousness.

A REGION is not a FUNCTION. A STATE is not an ID. A PREDICTION is not a destiny.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class LabelCategory(str, Enum):
    STRUCTURAL = "structural"
    CONNECTIVITY = "connectivity"
    FUNCTIONAL = "functional"
    STATE = "state"
    IDENTITY = "identity"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class CognitionLabel:
    """Base semantic label.

    Labels are closed, comparable, and intentionally small. New biological
    measurements should usually become STATE, PATTERN, or PREDICTION — not a
    new kind of person.
    """

    name: str
    category: LabelCategory
    summary: str
    examples: tuple[str, ...] = ()
    restricted: bool = False

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Structural labels
# ---------------------------------------------------------------------------

REGION = CognitionLabel(
    name="REGION",
    category=LabelCategory.STRUCTURAL,
    summary="An anatomical brain region.",
    examples=("frontal_lobe", "hippocampus", "cerebellum"),
)

NETWORK = CognitionLabel(
    name="NETWORK",
    category=LabelCategory.STRUCTURAL,
    summary="A collection of connected regions.",
    examples=("decision_network", "language_network", "attention_network"),
)

STRUCTURE = CognitionLabel(
    name="STRUCTURE",
    category=LabelCategory.STRUCTURAL,
    summary="General physical anatomy.",
    examples=("cerebrum", "meninges", "ventricular_system"),
)

# ---------------------------------------------------------------------------
# Connectivity labels
# ---------------------------------------------------------------------------

TRACT = CognitionLabel(
    name="TRACT",
    category=LabelCategory.CONNECTIVITY,
    summary="A white-matter pathway.",
    examples=("corticospinal_tract", "arcuate_fasciculus", "corpus_callosum"),
)

CONNECTION = CognitionLabel(
    name="CONNECTION",
    category=LabelCategory.CONNECTIVITY,
    summary="A relationship between regions.",
    examples=("fronto_temporal_link",),
)

# ---------------------------------------------------------------------------
# Functional labels
# ---------------------------------------------------------------------------

FUNCTION = CognitionLabel(
    name="FUNCTION",
    category=LabelCategory.FUNCTIONAL,
    summary="A cognitive process or capability. Modeled as a network process, never as a single region.",
    examples=("decision_making", "memory", "attention", "language"),
)

PROCESS = CognitionLabel(
    name="PROCESS",
    category=LabelCategory.FUNCTIONAL,
    summary="A dynamic activity unfolding over time.",
    examples=("encoding", "myelination", "synaptic_pruning"),
)

SIGNAL = CognitionLabel(
    name="SIGNAL",
    category=LabelCategory.FUNCTIONAL,
    summary="A simulated activity pattern — not a thought and not a person.",
    examples=("simulated_gamma", "bold_proxy"),
)

# ---------------------------------------------------------------------------
# State labels
# ---------------------------------------------------------------------------

TEMP = CognitionLabel(
    name="TEMP",
    category=LabelCategory.STATE,
    summary="A temporary condition.",
    examples=("currently_learning", "temporary_stress", "myelination_in_progress"),
)

STATE = CognitionLabel(
    name="STATE",
    category=LabelCategory.STATE,
    summary="A measured condition at a specific time.",
    examples=("current_attention", "sleep_wake_cycle", "struggling_today"),
)

PATTERN = CognitionLabel(
    name="PATTERN",
    category=LabelCategory.STATE,
    summary="A repeated observation or trend.",
    examples=("looking_preference", "learning_trend"),
)

PREDICTION = CognitionLabel(
    name="PREDICTION",
    category=LabelCategory.STATE,
    summary="A probabilistic future possibility. It cannot become identity.",
    examples=("success_probability", "language_readiness"),
)

# ---------------------------------------------------------------------------
# Identity — highly restricted
# ---------------------------------------------------------------------------

ID = CognitionLabel(
    name="ID",
    category=LabelCategory.IDENTITY,
    summary="A persistent identity-level label. Highly restricted: measurements, states, and predictions must not collapse into it.",
    examples=("subject_001",),
    restricted=True,
)

# ---------------------------------------------------------------------------
# Forbidden concepts — recognized so the compiler can refuse them clearly
# ---------------------------------------------------------------------------

PERSONALITY = CognitionLabel(
    name="PERSONALITY",
    category=LabelCategory.FORBIDDEN,
    summary="Not a Ranvier label. Personality is not compiled from anatomy.",
    restricted=True,
)

DESTINY = CognitionLabel(
    name="DESTINY",
    category=LabelCategory.FORBIDDEN,
    summary="Not a Ranvier label. A future estimate cannot become fate.",
    restricted=True,
)

FATE = CognitionLabel(
    name="FATE",
    category=LabelCategory.FORBIDDEN,
    summary="Not a Ranvier label.",
    restricted=True,
)


LABELS: dict[str, CognitionLabel] = {
    label.name: label
    for label in (
        REGION,
        NETWORK,
        STRUCTURE,
        TRACT,
        CONNECTION,
        FUNCTION,
        PROCESS,
        SIGNAL,
        TEMP,
        STATE,
        PATTERN,
        PREDICTION,
        ID,
        PERSONALITY,
        DESTINY,
        FATE,
    )
}

VALID_LABELS: FrozenSet[str] = frozenset(
    name for name, label in LABELS.items() if label.category is not LabelCategory.FORBIDDEN
)

FORBIDDEN_LABELS: FrozenSet[str] = frozenset(
    name for name, label in LABELS.items() if label.category is LabelCategory.FORBIDDEN
)

# Names that look like identity conclusions. Using them as assignment targets
# or ID values is almost always a conceptual error.
RESERVED_IDENTITY_NAMES: FrozenSet[str] = frozenset(
    {
        "destiny",
        "fate",
        "failure",
        "success",
        "genius",
        "personality",
        "identity",
        "cause",
        "entire_cause",
        "soul",
        "character",
        "worth",
    }
)

# Same-label assignment is allowed. Cross-label assignment is allowed only
# inside these narrow families, and never into ID.
COMPATIBLE_ASSIGNMENT: FrozenSet[tuple[str, str]] = frozenset(
    {
        ("TEMP", "STATE"),
        ("STATE", "TEMP"),
        ("STATE", "PATTERN"),
        ("TEMP", "PATTERN"),
        ("PATTERN", "STATE"),
        ("SIGNAL", "PROCESS"),
        ("PROCESS", "SIGNAL"),
        ("TRACT", "CONNECTION"),
        ("CONNECTION", "TRACT"),
        ("REGION", "STRUCTURE"),
        ("STRUCTURE", "REGION"),
    }
)


def get_label(name: str) -> Optional[CognitionLabel]:
    return LABELS.get(name.upper())


def is_valid_label(name: str) -> bool:
    label = get_label(name)
    return bool(label and label.category is not LabelCategory.FORBIDDEN)


def assignment_allowed(source: CognitionLabel, target: CognitionLabel) -> bool:
    """Return True if a value of `source` may be assigned to a binding of `target`."""
    if target.category is LabelCategory.FORBIDDEN:
        return False
    if source.category is LabelCategory.FORBIDDEN:
        return False
    if target is ID and source is not ID:
        return False
    if source is ID and target is not ID:
        return False
    if source.name == target.name:
        return True
    return (source.name, target.name) in COMPATIBLE_ASSIGNMENT


def family_of(label: CognitionLabel) -> str:
    return label.category.value
