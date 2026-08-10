# megadatetime

Educational Python toolkit for **extended calendar math**, **free public Earth-time data**, and an optional **3D Earth viewer**.

It does **not** replace the standard library `datetime` module. Use that for production clocks; use this package to experiment with large year ranges, published time sources, and visualization.

| Module | What it does |
| --- | --- |
| `MegaDateTime` | Proleptic Gregorian dates with years `1 … 262_000_000` |
| `SatelliteTime` | Current UTC from [TimeAPI.io](https://timeapi.io/) → `MegaDateTime` |
| `EarthRotation` | Earth orientation parameters from free [IERS](https://www.iers.org/) rapid data |
| `EarthViewer` | Optional PyVista rotating-Earth app (`EarthViewer/`) |

License: MIT (see `LICENSE` in the repository).

Current version: **0.2.0**

**GitHub release notes:** open [`CHANGELOG.md`](CHANGELOG.md) and copy that version’s **Release notes (copy this)** box.

**Files to put in a zip:** open [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

---

## Requirements

- Python **3.9+**
- Optional: `certifi` for HTTPS CA bundles on some Windows setups (`pip install -e ".[network]"`)
- Optional: PyVista stack for the viewer (`pip install -e ".[viewer]"`)

## Install

From the **repository root** (the folder that contains `pyproject.toml`):

```bash
pip install -e ".[dev]"
```

Viewer extras:

```bash
pip install -e ".[viewer]"
```

## Quick start

### MegaDateTime

```python
from datetime import timedelta
from megadatetime import MegaDateTime, MAXYEAR

date = MegaDateTime(10191, 4, 30)
print(date)                       # 10191-04-30 00:00:00
print(date.weekday())             # Monday=0 … Sunday=6
print(date.strftime("%Y-%m-%d"))

parsed = MegaDateTime.strptime("10191-04-30", "%Y-%m-%d")
later = date + timedelta(days=7)
delta = later - date

MegaDateTime(MAXYEAR + 1, 1, 1)   # ValueError: year … out of range
```

Calendar rules match Python’s `datetime`: proleptic Gregorian leap years (`/4`, not `/100`, unless `/400`).

**API surface:** construct with year/month/day (+ optional time fields); `strftime` / `strptime`; `weekday`; `isoformat`; `replace`; comparisons; `+` / `-` with `datetime.timedelta`; difference of two instances → `timedelta`.

### SatelliteTime

Fetches **present UTC** from TimeAPI.io. No API key. On failure raises `SatelliteTimeError` — it does **not** fall back to the system clock.

```python
from megadatetime import SatelliteTime

print(SatelliteTime.now())   # MegaDateTime in UTC
print(SatelliteTime.raw())   # last JSON payload (dict)
```

### EarthRotation

Downloads IERS `finals2000A.daily.csv` and returns the best current row as `EarthRotationState` (observation date, UT1−UTC in seconds, polar motion x/y in arcseconds, LOD in ms when present). On failure raises `EarthRotationError`.

```python
from megadatetime import EarthRotation

state = EarthRotation.now()
print(state)
print(EarthRotation.raw()[:200])   # raw CSV text
```

### EarthViewer (optional)

```bash
pip install -e ".[viewer]"
python -m EarthViewer.fetch_textures   # optional NASA / public-domain maps
python -m EarthViewer.main
```

**Controls (short):** drag to orbit, scroll to zoom, shift+drag to pan; green/red square = Earth spin; cyan squares = layers; bottom-right slider = spin speed. **Left-click** (no drag) hides/shows help captions; **sim time**, checkbox squares, slider bar, and axes gizmo stay visible.

Full architecture and extension notes: [`EarthViewer/README.md`](EarthViewer/README.md).

## Tests

Network calls are mocked via fixtures under `tests/fixtures/`:

```bash
pytest
```

## Layout

```text
MegaDateTime/
├── megadatetime/           # installable package
│   ├── mega_datetime.py
│   ├── satellite_time.py
│   ├── earth_rotation.py
│   └── _http.py
├── EarthViewer/            # optional PyVista app
├── tests/
├── CHANGELOG.md
├── RELEASE_CHECKLIST.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## Credits / data sources

This project’s code is MIT-licensed. Third-party data and imagery are credited below; they are **not** covered by the MIT license for the code itself.

| Source | Used for | Credit / notes |
| --- | --- | --- |
| [TimeAPI.io](https://timeapi.io/) | `SatelliteTime` (current UTC) | Free public API; no API key. Mentioned as the time source. |
| [IERS](https://www.iers.org/) Data Center | `EarthRotation` (`finals2000A.daily.csv`) | Earth orientation parameters. Credit: IERS. |
| [NASA](https://www.nasa.gov/) Visible Earth / Earth Observatory | Optional EarthViewer textures (day, night, clouds) | Imagery free of licensing fees for typical use; **credit NASA** as the imagery owner. Prefer linking [Visible Earth](https://visibleearth.nasa.gov/) / [Earth Observatory](https://earthobservatory.nasa.gov/). Do **not** use NASA logos or imply NASA endorsement. |

Procedural placeholder textures (when NASA maps are not downloaded) need no third-party credit.

## Releases

| File | Role |
| --- | --- |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | Checklist of files to include in a zip |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history + GitHub Release note text |
| `LICENSE` | MIT license (already in your repo) |
| `pyproject.toml` | Package version (`0.2.0`) |

## Design boundaries

- **MegaDateTime** — calendar representation and arithmetic only  
- **SatelliteTime** — one free “what time is it now?” source  
- **EarthRotation** — one free IERS Earth-orientation product  
- **EarthViewer** — local visualization foundation; time stays in `EarthTime` / `MegaDateTime`, not inside mesh code  

Keep additions modular. This remains a hobby / educational prototype, not a full astronomy library.
