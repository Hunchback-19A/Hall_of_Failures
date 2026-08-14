# Changelog — version history & GitHub release notes

This file is for **what changed in each version** and the text you paste into a GitHub Release description.

**Looking for which files to put in a zip?**  
→ Use [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) instead.

When you publish notes on GitHub: find the version below and copy its **Release notes (copy this)** block into the release description.

---

## How to publish notes (short)

1. Pick a version below (example: **0.2.0**).
2. Tag it as `v0.2.0` (or create the release on the GitHub website).
3. Paste that version’s **Release notes (copy this)** into the release body.
4. For a hand-made zip of source files, follow [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). GitHub’s automatic “Source code (zip)” is fine if the tagged commit already has those files.

Keep the version number in sync with `pyproject.toml` and `megadatetime/__init__.py`.

---

## Unreleased (not tagged yet)

Work done after the last tagged release. **Do not** paste this into a GitHub Release until you cut a new version (for example `0.2.1` or `0.3.0`).

**Already done, waiting for a future tag**

- EarthViewer: left-click (no drag) shows/hides help captions  
  (sim time, checkbox squares, slider bar, and axes stay on screen)
- EarthViewer: spin-speed slider made smaller and placed so the label is not cut off

**Ideas for later**

- Geologic / plate outline layer
- Real free satellite data in the viewer
- Optional graphics backend swap (beyond PyVista)

---

## Version 0.2.0 — current release

**Tag name:** `v0.2.0`  
**Suggested release title:** `v0.2.0 — SatelliteTime, EarthRotation, EarthViewer`  
**Date:** 2026-08-10

### What this release includes (plain English)

- Calendar type **MegaDateTime** (from 0.1.0) is still here
- **SatelliteTime** — “what time is it now?” from free TimeAPI.io
- **EarthRotation** — Earth’s rotation parameters from free IERS data
- **EarthViewer** — optional 3D rotating Earth window (PyVista)
- Tests that do not need a live network
- Install options: `pip install -e ".[dev]"`, `".[network]"`, `".[viewer]"`

### Release notes (copy this)

```text
MegaDateTime 0.2.0

What you get
- MegaDateTime: extended Gregorian calendar (years 1 … 262,000,000)
- SatelliteTime: current UTC from TimeAPI.io (no API key)
- EarthRotation: free IERS Earth-orientation data (UT1-UTC, polar motion, LOD)
- EarthViewer: optional PyVista 3D rotating Earth (day/night/clouds, spin controls)
- Offline tests with fixtures (no live API calls required for pytest)

Install
  pip install -e ".[dev]"
  pip install -e ".[viewer]"   # only if you want the 3D viewer

License: MIT
```

---

## Version 0.1.0 — first release

**Tag name:** `v0.1.0`  
**Suggested release title:** `v0.1.0 — MegaDateTime core`  
**Date:** 2026-08-09

### What this release includes (plain English)

- First usable **MegaDateTime** type only
- Same calendar rules as Python’s `datetime`, but with a much larger year range
- Basic tests and package install via `pyproject.toml`
- Satellite / Earth-rotation features were **not** finished yet (those arrived in 0.2.0)

### Release notes (copy this)

```text
MegaDateTime 0.1.0

What you get
- MegaDateTime: proleptic Gregorian calendar with years 1 … 262,000,000
- Familiar helpers: strftime / strptime, weekday, comparisons, timedelta math
- Clear errors when a date is out of range
- Installable package + unit tests for the calendar core

Install
  pip install -e ".[dev]"

License: MIT
```

---

## Cheat sheet

| If you want to… | Use… |
| --- | --- |
| Know **which files to zip** | [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) |
| Know **what to paste** into GitHub notes | The **Release notes (copy this)** box for that version |
| Know the **tag name** | `v` + version, e.g. `v0.2.0` |
| Know the **release title** | The “Suggested release title” line under that version |
| See work **not released yet** | The **Unreleased** section at the top |
| Confirm the code version | `pyproject.toml` → `version = "…"` |
