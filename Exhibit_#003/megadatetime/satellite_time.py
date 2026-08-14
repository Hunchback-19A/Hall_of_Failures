"""
SatelliteTime — present UTC time from a free public source (TimeAPI.io).

MegaDateTime extends calendar representation. SatelliteTime answers a different
question: “what time is it right now?” using an external measurement source.

Source (free, no API key): https://timeapi.io/
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ._http import NetworkError, fetch_json
from .mega_datetime import MegaDateTime

# Single free provider — keep this module intentionally simple.
TIMEAPI_UTC_URL = "https://timeapi.io/api/Time/current/zone?timeZone=UTC"


class SatelliteTimeError(RuntimeError):
    """Raised when TimeAPI.io cannot be used or its response cannot be parsed."""


class SatelliteTime:
    """
    Fetch current UTC time from TimeAPI.io and expose it as MegaDateTime.

    Example::

        from megadatetime import SatelliteTime

        print(SatelliteTime.now())
        print(SatelliteTime.raw())
    """

    _last_raw: Optional[Dict[str, Any]] = None

    @classmethod
    def now(cls, timeout: float = 20.0) -> MegaDateTime:
        """
        Retrieve current UTC time from TimeAPI.io as a MegaDateTime.

        Stores the unmodified JSON response for later inspection via ``raw()``.

        Raises:
            SatelliteTimeError: if the API is unreachable or the payload is invalid.
                Does **not** silently fall back to the local system clock.
        """
        try:
            payload = fetch_json(TIMEAPI_UTC_URL, timeout=timeout)
        except NetworkError as exc:
            raise SatelliteTimeError(str(exc)) from exc

        if not isinstance(payload, dict):
            raise SatelliteTimeError(
                "TimeAPI.io returned an unexpected payload type "
                f"({type(payload).__name__}); expected a JSON object."
            )

        # Keep the original response exactly as received (dict form of JSON).
        cls._last_raw = payload

        try:
            mega = _payload_to_megadatetime(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise SatelliteTimeError(
                f"Could not parse TimeAPI.io UTC timestamp: {exc}"
            ) from exc

        return mega

    @classmethod
    def raw(cls) -> Dict[str, Any]:
        """
        Return the unmodified JSON object from the last successful ``now()`` call.

        Raises:
            SatelliteTimeError: if ``now()`` has not been called successfully yet.
        """
        if cls._last_raw is None:
            raise SatelliteTimeError(
                "No TimeAPI.io response stored yet. Call SatelliteTime.now() first."
            )
        return cls._last_raw


def _payload_to_megadatetime(payload: Dict[str, Any]) -> MegaDateTime:
    """Convert a TimeAPI.io JSON object into MegaDateTime (UTC)."""
    # Prefer explicit numeric fields when present.
    if all(key in payload for key in ("year", "month", "day", "hour", "minute")):
        year = int(payload["year"])
        month = int(payload["month"])
        day = int(payload["day"])
        hour = int(payload["hour"])
        minute = int(payload["minute"])
        second = int(payload.get("seconds", payload.get("second", 0)) or 0)
        millis = payload.get("milliSeconds", payload.get("milliseconds", 0)) or 0
        microsecond = int(millis) * 1000
        return MegaDateTime(year, month, day, hour, minute, second, microsecond)

    # Fallback: ISO-like dateTime string (often without timezone suffix).
    text = payload.get("dateTime") or payload.get("datetime")
    if not isinstance(text, str) or not text:
        raise ValueError("missing numeric date fields and 'dateTime'")

    normalized = text.replace("Z", "+00:00")
    # TimeAPI may return more than 6 fractional digits; trim to microseconds.
    if "." in normalized:
        head, frac_and_tz = normalized.split(".", 1)
        digits = []
        rest = ""
        for ch in frac_and_tz:
            if ch.isdigit():
                digits.append(ch)
            else:
                rest = frac_and_tz[len(digits) :]
                break
        frac = "".join(digits)[:6].ljust(6, "0")
        normalized = f"{head}.{frac}{rest}"

    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        # Endpoint requested timeZone=UTC, so treat naive values as UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return MegaDateTime(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second,
        dt.microsecond,
    )
