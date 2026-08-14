"""
Texture loading utilities.

Uses local files when present; otherwise builds a lightweight procedural
fallback so the viewer runs offline without paid assets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np


def _procedural_day_map(width: int = 1024, height: int = 512) -> np.ndarray:
    """Simple blue-ocean / green-land stylized equirectangular RGB image."""
    lon = np.linspace(-180, 180, width, endpoint=False)
    lat = np.linspace(90, -90, height)
    lon_g, lat_g = np.meshgrid(lon, lat)

    # Soft “continents” via overlapping sinusoids — not geographic truth,
    # only a readable placeholder until a real texture is dropped in.
    land = (
        0.55 * np.sin(np.radians(lon_g * 2.0)) * np.cos(np.radians(lat_g * 1.3))
        + 0.35 * np.sin(np.radians(lon_g * 0.7 + 40))
        + 0.25 * np.cos(np.radians(lat_g * 3.0))
    )
    is_land = land > 0.15
    polar = np.abs(lat_g) > 70

    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :] = (20, 60, 140)  # ocean
    rgb[is_land] = (40, 120, 55)
    rgb[polar] = (230, 235, 240)
    return rgb


def _procedural_clouds(width: int = 1024, height: int = 512) -> np.ndarray:
    rng = np.random.default_rng(7)
    noise = rng.random((height, width))
    alpha = (np.clip(noise - 0.55, 0, 1) / 0.45 * 180).astype(np.uint8)
    rgb = np.full((height, width, 3), 255, dtype=np.uint8)
    return np.dstack([rgb, alpha])


def _procedural_night(width: int = 1024, height: int = 512) -> np.ndarray:
    rng = np.random.default_rng(3)
    base = np.zeros((height, width, 3), dtype=np.uint8)
    # Sparse city lights
    n = 800
    ys = rng.integers(0, height, size=n)
    xs = rng.integers(0, width, size=n)
    base[ys, xs] = (255, 220, 140)
    return base


def _clouds_to_rgba(rgb: np.ndarray) -> np.ndarray:
    """
    Convert a NASA-style cloud map (bright clouds on dark sky) to RGBA.

    Luminance becomes alpha so clear sky stays transparent on the cloud shell.
    """
    if rgb.ndim == 2:
        gray = rgb.astype(np.uint8)
    else:
        # Rec. 601 luma
        gray = (
            0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        ).astype(np.uint8)
    white = np.full((*gray.shape, 3), 255, dtype=np.uint8)
    return np.dstack([white, gray])


def load_texture_array(path: Optional[Path], role: str = "day") -> Tuple[np.ndarray, str]:
    """
    Load an equirectangular RGB(A) image (NASA row-0 = North).

    Returns ``(array, source_label)`` where *source_label* is ``file`` or
    ``procedural``.
    """
    if path is not None and path.is_file():
        try:
            from PIL import Image

            img = Image.open(path)
            if role == "clouds":
                rgb = np.asarray(img.convert("RGB"))
                array = _clouds_to_rgba(rgb)
            else:
                array = np.asarray(img.convert("RGB"))
            return np.ascontiguousarray(array), "file"
        except Exception:
            pass

    if role == "clouds":
        array = _procedural_clouds()
    elif role == "night":
        array = _procedural_night()
    else:
        array = _procedural_day_map()
    return np.ascontiguousarray(array), "procedural"


def numpy_to_pyvista_texture(array: np.ndarray):
    """Wrap a numpy image as a ``pyvista.Texture``."""
    import pyvista as pv

    if array.ndim == 2:
        array = np.dstack([array, array, array])
    return pv.numpy_to_texture(np.ascontiguousarray(array))
