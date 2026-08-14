"""
EarthViewer configuration — paths, defaults, and free-texture metadata.

No paid APIs. Textures are expected locally under ``data/textures/``
(NASA Blue Marble and related public-domain imagery are suitable).
"""

from __future__ import annotations

from pathlib import Path

# Package layout roots
EARTHVIEWER_ROOT = Path(__file__).resolve().parent
DATA_DIR = EARTHVIEWER_ROOT / "data"
TEXTURE_DIR = DATA_DIR / "textures"
SATELLITE_DIR = DATA_DIR / "satellite"

# Mesh quality (higher = smoother, more GPU cost). Keep modest for a laptop.
SPHERE_THETA_RESOLUTION = 90
SPHERE_PHI_RESOLUTION = 90
EARTH_RADIUS = 1.0

# Interaction / animation defaults
DEFAULT_ROTATION_DEG_PER_SEC = 12.0
MAX_ROTATION_DEG_PER_SEC = 60.0
# Clouds drift relative to the surface (deg/s). Positive = same sense as Earth spin.
CLOUD_DRIFT_DEG_PER_SEC = 4.0
TIMER_INTERVAL_MS = 33  # ~30 FPS update cadence for orientation only

# Window
WINDOW_SIZE = (1100, 750)
BACKGROUND_COLOR = "#02040a"
WINDOW_TITLE = "EarthViewer — MegaDateTime"

# Texture filenames (drop free public-domain maps into data/textures/)
DAY_TEXTURE_NAME = "earth_day.jpg"
NIGHT_TEXTURE_NAME = "earth_night.jpg"
CLOUDS_TEXTURE_NAME = "earth_clouds.jpg"

# Optional NASA public-domain sources (Visible Earth / EO Images). Used only if
# the user runs ``python -m EarthViewer.fetch_textures`` — never required at import.
FREE_TEXTURE_URLS = {
    DAY_TEXTURE_NAME: (
        "https://eoimages.gsfc.nasa.gov/images/imagerecords/"
        "57000/57752/land_shallow_topo_2048.jpg"
    ),
    NIGHT_TEXTURE_NAME: (
        "https://eoimages.gsfc.nasa.gov/images/imagerecords/"
        "79000/79765/dnb_land_ocean_ice.2012.3600x1800.jpg"
    ),
    # Blue Marble cloud composite (same catalog family as the old .png that 404'd).
    # https://visibleearth.nasa.gov/images/57747/blue-marble-clouds
    CLOUDS_TEXTURE_NAME: (
        "https://eoimages.gsfc.nasa.gov/images/imagerecords/"
        "57000/57747/cloud_combined_2048.jpg"
    ),
}


def ensure_data_dirs() -> None:
    """Create data directories if they do not exist."""
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    SATELLITE_DIR.mkdir(parents=True, exist_ok=True)


def texture_path(name: str) -> Path:
    return TEXTURE_DIR / name
