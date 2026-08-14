"""
EarthRotation — Earth orientation parameters from free IERS rapid data.

MegaDateTime models calendar dates. EarthRotation reports physical Earth
orientation quantities published by the International Earth Rotation and
Reference Systems Service (IERS).

Source (free, no API key): https://www.iers.org/
Daily rapid file (CSV): finals2000A.daily.csv from the IERS Data Center.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ._http import NetworkError, fetch_text

# Single free provider / product — keep this module intentionally simple.
IERS_FINALS2000A_DAILY_CSV_URL = (
    "https://datacenter.iers.org/products/eop/rapid/daily/csv/"
    "finals2000A.daily.csv"
)


class EarthRotationError(RuntimeError):
    """Raised when IERS data cannot be downloaded or parsed."""


@dataclass(frozen=True)
class EarthRotationState:
    """
    Structured Earth-orientation snapshot for one observation date.

    Units follow the IERS rapid product:
    - polar motion ``x`` / ``y`` in arcseconds
    - ``ut1_utc`` in seconds
    - ``lod`` (length of day) in milliseconds, when present
    """

    observation_date: date
    mjd: Optional[float]
    ut1_utc: Optional[float]
    polar_motion: Optional[Tuple[float, float]]
    lod: Optional[float]
    data_type: Optional[str]
    source: str
    fetched_at: datetime

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly dictionary of parsed fields."""
        x = y = None
        if self.polar_motion is not None:
            x, y = self.polar_motion
        return {
            "observation_date": self.observation_date.isoformat(),
            "mjd": self.mjd,
            "ut1_utc": self.ut1_utc,
            "polar_motion_x_arcsec": x,
            "polar_motion_y_arcsec": y,
            "lod_ms": self.lod,
            "data_type": self.data_type,
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat().replace("+00:00", "Z"),
        }

    def __str__(self) -> str:
        pm = (
            f"(x={self.polar_motion[0]:.6f}\", y={self.polar_motion[1]:.6f}\")"
            if self.polar_motion is not None
            else "None"
        )
        ut1 = f"{self.ut1_utc:.7f} s" if self.ut1_utc is not None else "None"
        return (
            "EarthRotationState("
            f"observation_date={self.observation_date.isoformat()}, "
            f"UT1-UTC={ut1}, "
            f"polar_motion={pm}, "
            f"type={self.data_type!r})"
        )


class EarthRotation:
    """
    Fetch and parse free IERS rapid Earth orientation parameters.

    Example::

        from megadatetime import EarthRotation

        print(EarthRotation.now())
        print(EarthRotation.raw())
    """

    _last_raw: Optional[str] = None

    @classmethod
    def now(cls, timeout: float = 30.0) -> EarthRotationState:
        """
        Return Earth's current rotation-related information from IERS.

        Downloads the free ``finals2000A.daily.csv`` product and selects the
        most recent row on or before today's UTC date that contains usable
        polar-motion / UT1-UTC values.

        Raises:
            EarthRotationError: if the download fails or no usable row is found.
        """
        try:
            csv_text = fetch_text(IERS_FINALS2000A_DAILY_CSV_URL, timeout=timeout)
        except NetworkError as exc:
            raise EarthRotationError(str(exc)) from exc

        cls._last_raw = csv_text
        fetched_at = datetime.now(timezone.utc)

        try:
            rows = _parse_iers_csv(csv_text)
            selected = _select_current_row(rows, today=fetched_at.date())
        except EarthRotationError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise EarthRotationError(f"Failed to parse IERS CSV: {exc}") from exc

        if selected is None:
            raise EarthRotationError(
                "IERS file was downloaded, but no usable Earth orientation "
                "row was found for today or earlier."
            )

        return EarthRotationState(
            observation_date=selected["observation_date"],
            mjd=selected.get("mjd"),
            ut1_utc=selected.get("ut1_utc"),
            polar_motion=selected.get("polar_motion"),
            lod=selected.get("lod"),
            data_type=selected.get("data_type"),
            source=IERS_FINALS2000A_DAILY_CSV_URL,
            fetched_at=fetched_at,
        )

    @classmethod
    def raw(cls) -> str:
        """
        Return the unmodified CSV text from the last successful ``now()`` call.

        Raises:
            EarthRotationError: if ``now()`` has not been called successfully yet.
        """
        if cls._last_raw is None:
            raise EarthRotationError(
                "No IERS response stored yet. Call EarthRotation.now() first."
            )
        return cls._last_raw


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return float(text)


def _unique_fieldnames(names: List[str]) -> List[str]:
    """Rename duplicate CSV headers (IERS repeats ``Type`` several times)."""
    seen: Dict[str, int] = {}
    unique: List[str] = []
    for name in names:
        key = name or ""
        count = seen.get(key, 0)
        if count == 0:
            unique.append(key)
        else:
            unique.append(f"{key}_{count}")
        seen[key] = count + 1
    return unique


def _parse_iers_csv(csv_text: str) -> List[Dict[str, Any]]:
    """Parse IERS finals2000A.daily.csv into a list of row dicts."""
    stream = io.StringIO(csv_text)
    header_line = stream.readline()
    if not header_line.strip():
        raise EarthRotationError("IERS CSV has no header row.")

    fieldnames = _unique_fieldnames(next(csv.reader([header_line], delimiter=";")))
    reader = csv.DictReader(stream, fieldnames=fieldnames, delimiter=";")

    rows: List[Dict[str, Any]] = []
    for line_no, row in enumerate(reader, start=2):
        try:
            year = int(row["Year"])
            month = int(row["Month"])
            day = int(row["Day"])
            observation_date = date(year, month, day)
        except (KeyError, TypeError, ValueError):
            continue

        x = _parse_float(row.get("x_pole"))
        y = _parse_float(row.get("y_pole"))
        ut1 = _parse_float(row.get("UT1-UTC"))
        lod = _parse_float(row.get("LOD"))
        mjd = _parse_float(row.get("MJD"))

        # First Type column describes the Bulletin A / rapid series quality.
        data_type = (row.get("Type") or "").strip() or None

        polar_motion = (x, y) if x is not None and y is not None else None

        # Keep rows that carry at least one orientation quantity.
        if polar_motion is None and ut1 is None:
            continue

        rows.append(
            {
                "observation_date": observation_date,
                "mjd": mjd,
                "ut1_utc": ut1,
                "polar_motion": polar_motion,
                "lod": lod,
                "data_type": data_type,
                "_line_no": line_no,
            }
        )
    return rows


def _select_current_row(
    rows: List[Dict[str, Any]], today: date
) -> Optional[Dict[str, Any]]:
    """
    Choose the best row for ``now()``.

    Prefer the latest row on or before *today* that includes both polar motion
    and UT1-UTC. Fall back to the latest earlier row with any orientation data.
    """
    eligible = [r for r in rows if r["observation_date"] <= today]
    if not eligible:
        return None

    complete = [
        r
        for r in eligible
        if r.get("polar_motion") is not None and r.get("ut1_utc") is not None
    ]
    pool = complete or eligible
    return max(pool, key=lambda r: r["observation_date"])
