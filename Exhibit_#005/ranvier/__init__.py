"""Ranvier — a fictional language for brain-related models.

Named for the node of Ranvier on a neuron's axon: a gap in myelin
where the signal is renewed, not assumed.

Never compile a destiny when you only measured a state.
"""

from .compiler import CompiledProgram, Compiler, compile_file, compile_source, load_models
from .errors import (
    AttributionError,
    CognitionError,
    CognitionValueError,
    CoordinateError,
    LabelError,
    ModelError,
    ProphecyError,
)
from .interpreter import Interpreter, run_file
from .labels import (
    CONNECTION,
    FUNCTION,
    ID,
    NETWORK,
    PATTERN,
    PREDICTION,
    PROCESS,
    REGION,
    SIGNAL,
    STATE,
    STRUCTURE,
    TEMP,
    TRACT,
    CognitionLabel,
)
from .parser import parse, parse_file

__version__ = "0.1.0"
# When this version was created (Python-style build date, not the session clock).
__release_date__ = "Aug 20 2026, 16:23:15"
__all__ = [
    "CognitionLabel",
    "REGION",
    "NETWORK",
    "STRUCTURE",
    "TRACT",
    "CONNECTION",
    "FUNCTION",
    "PROCESS",
    "SIGNAL",
    "TEMP",
    "STATE",
    "PATTERN",
    "PREDICTION",
    "ID",
    "CognitionError",
    "LabelError",
    "CognitionValueError",
    "ModelError",
    "CoordinateError",
    "AttributionError",
    "ProphecyError",
    "Compiler",
    "CompiledProgram",
    "Interpreter",
    "compile_file",
    "compile_source",
    "load_models",
    "parse",
    "parse_file",
    "run_file",
]
