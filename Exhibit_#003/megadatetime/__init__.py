"""
megadatetime — educational extensions around calendar and time concepts.

MegaDateTime   — extended proleptic Gregorian calendar calculations
SatelliteTime  — present-time data from a free external source (TimeAPI.io)
EarthRotation  — Earth orientation parameters from free IERS data
"""

from .mega_datetime import MAXYEAR, MINYEAR, MegaDateTime
from .satellite_time import SatelliteTime, SatelliteTimeError
from .earth_rotation import EarthRotation, EarthRotationError, EarthRotationState

__all__ = [
    "MegaDateTime",
    "MINYEAR",
    "MAXYEAR",
    "SatelliteTime",
    "SatelliteTimeError",
    "EarthRotation",
    "EarthRotationError",
    "EarthRotationState",
]

__version__ = "0.2.0"
