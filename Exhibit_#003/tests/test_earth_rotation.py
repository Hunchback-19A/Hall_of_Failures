"""Unit tests for EarthRotation (IERS) — network is mocked."""

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from megadatetime import EarthRotation, EarthRotationError, EarthRotationState
from megadatetime._http import NetworkError
from megadatetime.earth_rotation import _parse_iers_csv, _select_current_row

FIXTURE = Path(__file__).parent / "fixtures" / "finals2000A.daily.csv"
# Freeze "today" so row selection does not depend on the real calendar date.
FROZEN_UTC_NOW = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def iers_csv():
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_earth_raw():
    EarthRotation._last_raw = None
    yield
    EarthRotation._last_raw = None


def test_now_returns_structured_state(iers_csv):
    with patch(
        "megadatetime.earth_rotation.fetch_text", return_value=iers_csv
    ), patch("megadatetime.earth_rotation.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN_UTC_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        state = EarthRotation.now()

    assert isinstance(state, EarthRotationState)
    assert state.observation_date == date(2026, 5, 13)
    assert state.ut1_utc == pytest.approx(0.0291751)
    assert state.polar_motion is not None
    assert state.polar_motion[0] == pytest.approx(0.169051)
    assert state.polar_motion[1] == pytest.approx(0.411759)
    assert state.lod == pytest.approx(1.0393)
    assert state.data_type == "final"
    assert "iers.org" in state.source or "datacenter.iers.org" in state.source


def test_raw_returns_unmodified_csv(iers_csv):
    with patch(
        "megadatetime.earth_rotation.fetch_text", return_value=iers_csv
    ), patch("megadatetime.earth_rotation.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN_UTC_NOW
        EarthRotation.now()

    raw = EarthRotation.raw()
    assert raw == iers_csv
    assert raw.startswith("MJD;Year;Month;Day")


def test_raw_before_now_raises():
    with pytest.raises(EarthRotationError, match="now\\(\\) first"):
        EarthRotation.raw()


def test_network_failure_is_clear():
    with patch(
        "megadatetime.earth_rotation.fetch_text",
        side_effect=NetworkError("Could not reach datacenter.iers.org (offline)"),
    ):
        with pytest.raises(EarthRotationError, match="Could not reach"):
            EarthRotation.now()

    with pytest.raises(EarthRotationError):
        EarthRotation.raw()


def test_parse_iers_csv_extracts_rows(iers_csv):
    rows = _parse_iers_csv(iers_csv)
    assert len(rows) == 4
    assert rows[0]["observation_date"] == date(2026, 5, 11)
    assert rows[0]["ut1_utc"] == pytest.approx(0.0309709)


def test_select_current_row_prefers_latest_on_or_before_today(iers_csv):
    rows = _parse_iers_csv(iers_csv)
    selected = _select_current_row(rows, today=date(2026, 5, 12))
    assert selected is not None
    assert selected["observation_date"] == date(2026, 5, 12)


def test_select_current_row_can_use_prediction_when_needed(iers_csv):
    rows = _parse_iers_csv(iers_csv)
    selected = _select_current_row(rows, today=date(2026, 6, 9))
    assert selected is not None
    assert selected["observation_date"] == date(2026, 6, 9)
    assert selected["data_type"] == "prediction"


def test_empty_csv_raises():
    with patch(
        "megadatetime.earth_rotation.fetch_text",
        return_value="MJD;Year;Month;Day;Type;x_pole;y_pole;UT1-UTC\n",
    ), patch("megadatetime.earth_rotation.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN_UTC_NOW
        with pytest.raises(EarthRotationError, match="no usable"):
            EarthRotation.now()


def test_as_dict_and_str(iers_csv):
    with patch(
        "megadatetime.earth_rotation.fetch_text", return_value=iers_csv
    ), patch("megadatetime.earth_rotation.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN_UTC_NOW
        state = EarthRotation.now()

    data = state.as_dict()
    assert data["observation_date"] == "2026-05-13"
    assert "UT1-UTC" in str(state)
    assert "polar_motion" in str(state)
