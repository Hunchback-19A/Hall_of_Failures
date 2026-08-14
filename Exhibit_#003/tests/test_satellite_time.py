"""Unit tests for SatelliteTime (TimeAPI.io) — network is mocked."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from megadatetime import MegaDateTime, SatelliteTime, SatelliteTimeError
from megadatetime._http import NetworkError

FIXTURE = Path(__file__).parent / "fixtures" / "timeapi_utc.json"


@pytest.fixture
def timeapi_payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clear_satellite_raw():
    SatelliteTime._last_raw = None
    yield
    SatelliteTime._last_raw = None


def test_now_returns_megadatetime(timeapi_payload):
    with patch(
        "megadatetime.satellite_time.fetch_json", return_value=timeapi_payload
    ):
        result = SatelliteTime.now()

    assert isinstance(result, MegaDateTime)
    # milliSeconds=123 → 123000 microseconds
    assert result == MegaDateTime(2026, 8, 10, 3, 30, 45, 123000)
    assert str(result) == "2026-08-10 03:30:45.123000"


def test_raw_returns_unmodified_payload(timeapi_payload):
    with patch(
        "megadatetime.satellite_time.fetch_json", return_value=timeapi_payload
    ):
        SatelliteTime.now()

    raw = SatelliteTime.raw()
    assert raw == timeapi_payload
    assert raw["timeZone"] == "UTC"
    assert raw["year"] == 2026


def test_raw_before_now_raises():
    with pytest.raises(SatelliteTimeError, match="now\\(\\) first"):
        SatelliteTime.raw()


def test_network_failure_is_clear_and_does_not_fallback():
    with patch(
        "megadatetime.satellite_time.fetch_json",
        side_effect=NetworkError("Could not reach timeapi.io (offline)"),
    ):
        with pytest.raises(SatelliteTimeError, match="Could not reach"):
            SatelliteTime.now()

    # Must not silently invent a system-clock value.
    with pytest.raises(SatelliteTimeError):
        SatelliteTime.raw()


def test_invalid_payload_raises():
    bad = {"timeZone": "UTC", "note": "missing fields"}
    with patch("megadatetime.satellite_time.fetch_json", return_value=bad):
        with pytest.raises(SatelliteTimeError, match="Could not parse"):
            SatelliteTime.now()


def test_datetime_string_fallback():
    payload = {
        "dateTime": "2026-08-10T03:30:45.1234567",
        "timeZone": "UTC",
    }
    with patch("megadatetime.satellite_time.fetch_json", return_value=payload):
        result = SatelliteTime.now()
    assert result == MegaDateTime(2026, 8, 10, 3, 30, 45, 123456)


def test_non_object_json_raises():
    with patch(
        "megadatetime.satellite_time.fetch_json",
        return_value=["not", "an", "object"],
    ):
        with pytest.raises(SatelliteTimeError, match="unexpected payload"):
            SatelliteTime.now()
