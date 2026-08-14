"""
EarthTime — simulation-time abstraction separate from rendering.

Supports ordinary calendar dates today and extremely large timescales via
``megadatetime.MegaDateTime``. Geological reconstruction hooks stay here,
not in the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from megadatetime import MegaDateTime


Number = Union[int, float]


@dataclass
class GeologicContext:
    """
    Placeholder for future plate-reconstruction / deep-time metadata.

    Rendering must not depend on these fields yet; they document the intended
    extension point for geologic time simulation.
    """

    label: str = "Present day"
    years_before_present: float = 0.0
    reconstruction_model: Optional[str] = None  # e.g. future "PALEOMAP"


class EarthTime:
    """
    Custom time engine façade for EarthViewer.

    Internally stores a ``MegaDateTime`` so the viewer is not limited to
    Python's ``datetime`` year range. Use ``geologic`` for deep-time labels
    while the absolute calendar clock can still advance for animation demos.
    """

    def __init__(
        self,
        instant: Optional[MegaDateTime] = None,
        geologic: Optional[GeologicContext] = None,
    ) -> None:
        if instant is None:
            now = datetime.now(timezone.utc)
            instant = MegaDateTime(
                now.year,
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second,
                now.microsecond,
            )
        self._instant = instant
        self.geologic = geologic or GeologicContext()

    @classmethod
    def now_utc(cls) -> EarthTime:
        """Current UTC wall clock as EarthTime."""
        return cls()

    @classmethod
    def from_mega(cls, instant: MegaDateTime) -> EarthTime:
        return cls(instant=instant)

    @classmethod
    def from_datetime(cls, dt: datetime) -> EarthTime:
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return cls(
            MegaDateTime(
                dt.year,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second,
                dt.microsecond,
            )
        )

    @classmethod
    def geologic_snapshot(
        cls,
        years_before_present: Number,
        label: Optional[str] = None,
        base: Optional[MegaDateTime] = None,
    ) -> EarthTime:
        """
        Build a deep-time context without inventing a new calendar.

        The absolute ``MegaDateTime`` stays at *base* (default: now) so the
        UI clock still works; ``geologic`` carries the scientific scenario.
        Plate meshes / reconstructions can later key off ``years_before_present``.
        """
        years = float(years_before_present)
        ctx = GeologicContext(
            label=label
            or (
                f"{abs(years):,.0f} years "
                f"{'before' if years >= 0 else 'after'} present"
            ),
            years_before_present=years,
            reconstruction_model=None,
        )
        return cls(instant=base, geologic=ctx)

    @property
    def mega(self) -> MegaDateTime:
        """Underlying MegaDateTime instant."""
        return self._instant

    def advance(self, seconds: Number) -> None:
        """Advance the absolute simulation clock by *seconds* (may be fractional)."""
        self._instant = self._instant + timedelta(seconds=float(seconds))

    def set_instant(self, instant: MegaDateTime) -> None:
        self._instant = instant

    def display(self) -> str:
        """Human-readable status line for the GUI."""
        clock = str(self._instant)
        if (
            self.geologic.years_before_present == 0.0
            and self.geologic.label == "Present day"
        ):
            return f"Sim time (UTC): {clock}"
        return (
            f"Sim time (UTC): {clock}  |  "
            f"Geologic: {self.geologic.label} "
            f"(YBP={self.geologic.years_before_present:g})"
        )

    def __repr__(self) -> str:
        return (
            f"EarthTime(mega={self._instant!r}, "
            f"geologic={self.geologic!r})"
        )
