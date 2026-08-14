# EarthViewer

Lightweight, extensible **3D rotating Earth** viewer built with **PyVista/VTK**.
Part of the MegaDateTime scientific visualization foundation.

First milestone: *a rotating Earth rendered locally with PyVista, ready for future satellite and geological-time data.*

Project-wide install, package API, and **GitHub release notes** live in the repo root: [`README.md`](../README.md) and [`CHANGELOG.md`](../CHANGELOG.md).

## Architecture

```text
EarthViewer/
├── main.py                 # GUI + app controller (overlay toggle, widgets)
├── config.py               # paths, defaults, free texture URLs
├── fetch_textures.py       # optional NASA public-domain download
├── renderer/
│   ├── earth.py            # sphere geometry + scene (no per-frame rebuild)
│   ├── camera.py           # view / interaction helpers
│   ├── layers.py           # DataLayer interface + placeholders
│   └── textures.py         # file or procedural textures
├── data/
│   ├── textures/           # day / night / clouds images
│   └── satellite/          # future local satellite products
└── time/
    └── earth_time.py       # EarthTime ↔ MegaDateTime (not in the renderer)
```

### Separation of concerns

| Piece | Responsibility |
| --- | --- |
| **EarthModel / EarthScene** | Geometry + actors. Rotate by changing orientation only. |
| **DataLayer** | Interchangeable data sources (textures, satellite, weather, geology…). |
| **EarthTime** | Simulation clock using `MegaDateTime` + geologic context hooks. |
| **main.EarthViewerApp** | Wires UI ↔ scene ↔ time. |

Graphics stay swappable: layer code never talks to VTK directly except through `EarthScene.apply_layer_frame`. A future C++ module can replace mesh/array producers while keeping the same interfaces.

```text
          ┌────────────┐
          │ EarthTime  │  (MegaDateTime / geologic YBP)
          └─────┬──────┘
                │
     ┌──────────▼──────────┐
     │    DataLayer(s)     │  load() I/O  →  build_frame() arrays
     └──────────┬──────────┘
                │ LayerFrame (numpy arrays / texture paths)
     ┌──────────▼──────────┐
     │     EarthScene      │  actors updated; meshes reused
     └──────────┬──────────┘
                │
          ┌─────▼─────┐
          │  PyVista  │  (replaceable backend later)
          └───────────┘
```

## Install

Run these commands from the **repository root** (`MegaDateTime/`), not from inside `EarthViewer/`:

```text
MegaDateTime/          ← run pip here (has pyproject.toml)
└── EarthViewer/
```

```bash
cd C:\Users\elain\Desktop\MegaDateTime
pip install -e ".[viewer]"
```

Or only the viewer deps from the root:

```bash
pip install -r EarthViewer/requirements.txt
pip install -e .
```

If you see `does not appear to be a Python project`, you are in the wrong folder — `EarthViewer/` has no `pyproject.toml` by design.

Optional realistic textures (no API key):

```bash
python -m EarthViewer.fetch_textures
```

**Credit:** Earth maps from **NASA** (Visible Earth / Earth Observatory) — free of typical licensing fees; credit NASA as the imagery owner. Do not use NASA logos or imply endorsement. Details and other data sources: root [`README.md`](../README.md#credits--data-sources).

Maps downloaded by the helper:

- Day — land / shallow topo  
- Night — city lights (Black Marble–style)  
- Clouds — Blue Marble cloud composite (`cloud_combined_2048.jpg`)

If you skip this, procedural placeholders are used automatically (no NASA credit needed for those).

## Run

```bash
python -m EarthViewer.main
```

### Camera

| Input | Action |
| --- | --- |
| Drag | Orbit |
| Scroll | Zoom |
| Shift+drag | Pan |

### Widgets (always available)

| Control | Role |
| --- | --- |
| Green / red square | Earth spin on / pause |
| Cyan squares | Layer toggles (day / night / clouds / satellite) |
| Bottom-right slider | Spin speed (deg/s) — bar stays when captions hide |
| Axes gizmo | Lower-right orientation widget |
| Sim time HUD | Upper-left; always visible |

### Overlay captions

**Left-click** once (no drag) hides help text; click again to show it.

| Hidden when toggled off | Stays visible |
| --- | --- |
| Camera / axis help (upper-right) | Sim time |
| Layer and spin captions | Checkbox squares |
| Slider title and value label | Slider bar |
| | Axes gizmo |
| | N / S / E / W globe markers |

Clicks on the left button column or the bottom-right slider/axes band do not toggle captions, so those controls keep working. Dragging still orbits the camera.

Textures are oriented north-up for NASA equirectangular maps (Blue Marble / Visible Earth).
Clouds use a separate longitude with a small drift (`CLOUD_DRIFT_DEG_PER_SEC`) so they move across the surface instead of being glued to the ground texture.

## Extending

**New data source** — subclass `DataLayer`, implement `load` + `build_frame`, register in `build_default_registry()`.

**Deep time** — use `EarthTime.geologic_snapshot(100_000_000)` and later key plate meshes off `geologic.years_before_present` without touching the renderer.

**Faster path** — keep heavy array work in `build_frame` (or a future C++ extension); only push `LayerFrame` into `EarthScene`.

## Next milestone (suggested)

1. Load a free plate-reconstruction / continent outline layer keyed by `EarthTime` geologic YBP.
2. Stream or cache one free satellite product into `data/satellite/` behind `SatellitePlaceholderLayer`.
3. Add a thin `RenderBackend` protocol so PyVista can be swapped for a GPU-accelerated viewer later.
