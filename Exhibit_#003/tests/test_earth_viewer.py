"""Headless tests for EarthViewer time + layer interfaces (no GUI)."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from megadatetime import MegaDateTime
from EarthViewer.time.earth_time import EarthTime
from EarthViewer.renderer.layers import (
    LayerRegistry,
    SatellitePlaceholderLayer,
    GeologicalOverlayLayer,
)


def test_earth_time_uses_megadatetime():
    et = EarthTime.from_mega(MegaDateTime(10191, 4, 30, 12, 0, 0))
    assert et.mega.year == 10191
    et.advance(3600)
    assert et.mega.hour == 13
    assert "10191" in et.display()


def test_geologic_snapshot_keeps_context():
    et = EarthTime.geologic_snapshot(100_000_000, label="Cretaceous demo")
    assert et.geologic.years_before_present == 100_000_000
    assert "Cretaceous" in et.display()


def test_satellite_placeholder_builds_frame():
    layer = SatellitePlaceholderLayer()
    layer.load()
    layer.set_enabled(True)
    frame = layer.update(EarthTime.now_utc())
    assert frame is not None
    assert frame.kind == "lonlat_points"
    assert "lonlat" in frame.arrays
    assert isinstance(frame.arrays["lonlat"], np.ndarray)


def test_registry_skips_disabled_layers():
    reg = LayerRegistry()
    sat = SatellitePlaceholderLayer()
    geo = GeologicalOverlayLayer()
    reg.register(sat)
    reg.register(geo)
    reg.load_all()
    sat.set_enabled(False)
    geo.set_enabled(True)
    frames = reg.enabled_frames(EarthTime.now_utc())
    assert len(frames) == 1
    assert frames[0].metadata["role"] == "geology"
