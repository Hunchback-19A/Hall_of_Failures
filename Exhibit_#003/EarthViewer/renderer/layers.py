"""
Data layers — interchangeable overlays separate from Earth geometry.

Concrete layers may load imagery, scalars, or future geological meshes.
A future C++ accelerator can replace ``load`` / ``build_dataset`` while
keeping this interface stable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from EarthViewer.time.earth_time import EarthTime


@dataclass
class LayerFrame:
    """
    Processed payload ready for the renderer (not the raw network response).

    Keeping arrays here makes it easier to swap a C++ producer later.
    """

    kind: str
    arrays: Dict[str, np.ndarray] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    texture_path: Optional[Path] = None


class DataLayer(ABC):
    """Generic, swappable data source for EarthViewer."""

    name: str = "layer"
    enabled: bool = True

    @abstractmethod
    def load(self) -> None:
        """Fetch / read source data (I/O). Safe to call once at startup."""

    @abstractmethod
    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        """
        Convert source data for the given simulation time.

        Must not touch the VTK/PyVista scene. Return ``None`` if inactive
        or not yet available.
        """

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def update(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        if not self.enabled:
            return None
        return self.build_frame(earth_time)


class LayerRegistry:
    """Simple registry so sources stay interchangeable."""

    def __init__(self) -> None:
        self._layers: Dict[str, DataLayer] = {}

    def register(self, layer: DataLayer) -> None:
        self._layers[layer.name] = layer

    def get(self, name: str) -> DataLayer:
        return self._layers[name]

    def all(self) -> Iterable[DataLayer]:
        return self._layers.values()

    def load_all(self) -> None:
        for layer in self._layers.values():
            layer.load()

    def enabled_frames(self, earth_time: "EarthTime") -> List[LayerFrame]:
        frames: List[LayerFrame] = []
        for layer in self._layers.values():
            frame = layer.update(earth_time)
            if frame is not None:
                frames.append(frame)
        return frames


# --- Example / placeholder layers -------------------------------------------


class DayTextureLayer(DataLayer):
    """Base daytime Earth texture (geometry stays in the Earth mesh)."""

    name = "earth_texture"

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path
        self._ready = False

    def load(self) -> None:
        self._ready = self.path is not None and self.path.is_file()

    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        if not self._ready or self.path is None:
            return None
        return LayerFrame(kind="texture", texture_path=self.path, metadata={"role": "day"})


class NightLightsLayer(DataLayer):
    name = "night_lights"

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path
        self.enabled = False  # optional; off by default
        self._ready = False

    def load(self) -> None:
        self._ready = self.path is not None and self.path.is_file()

    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        if not self._ready or self.path is None:
            return None
        return LayerFrame(
            kind="texture",
            texture_path=self.path,
            metadata={"role": "night"},
        )


class CloudLayer(DataLayer):
    name = "clouds"

    def __init__(self, path: Optional[Path] = None, altitude: float = 1.01) -> None:
        self.path = path
        self.altitude = altitude
        self.enabled = False
        self._ready = False

    def load(self) -> None:
        self._ready = self.path is not None and self.path.is_file()

    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        if not self._ready or self.path is None:
            return None
        return LayerFrame(
            kind="shell_texture",
            texture_path=self.path,
            metadata={"role": "clouds", "radius": self.altitude},
        )


class SatellitePlaceholderLayer(DataLayer):
    """
    Placeholder for future satellite imagery / swath overlays.

    Does not hardcode an API. A real source would implement ``load`` against
    local files under ``data/satellite/`` or any free public dataset.
    """

    name = "satellite"

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir
        self.enabled = False
        self._points: Optional[np.ndarray] = None

    def load(self) -> None:
        # Synthetic demo markers so the toggle is visible without an API.
        # Replace with real arrays from a free satellite product later.
        rng = np.random.default_rng(42)
        lon = rng.uniform(-180, 180, size=24)
        lat = rng.uniform(-60, 60, size=24)
        self._points = np.column_stack([lon, lat])

    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        if self._points is None:
            return None
        return LayerFrame(
            kind="lonlat_points",
            arrays={"lonlat": self._points.copy()},
            metadata={
                "role": "satellite_placeholder",
                "label": "Satellite placeholder (no live API)",
                "sim_time": str(earth_time.mega),
            },
        )


class WeatherPlaceholderLayer(DataLayer):
    name = "weather"

    def __init__(self) -> None:
        self.enabled = False

    def load(self) -> None:
        return None

    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        # Reserved for future free weather grids (e.g. local NetCDF).
        return LayerFrame(
            kind="scalar_grid",
            arrays={},
            metadata={"role": "weather", "status": "not_connected"},
        )


class GeologicalOverlayLayer(DataLayer):
    """Future tectonic / plate-reconstruction overlay keyed by EarthTime."""

    name = "geology"

    def __init__(self) -> None:
        self.enabled = False

    def load(self) -> None:
        return None

    def build_frame(self, earth_time: "EarthTime") -> Optional[LayerFrame]:
        return LayerFrame(
            kind="geology",
            arrays={},
            metadata={
                "role": "geology",
                "years_before_present": earth_time.geologic.years_before_present,
                "label": earth_time.geologic.label,
                "status": "interface_only",
            },
        )
