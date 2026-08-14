"""
Optional helper: download free NASA public-domain Earth textures.

No API key. Safe to skip — EarthViewer falls back to procedural textures.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import Request, urlopen

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from EarthViewer import config


def fetch(url: str, dest: Path, timeout: float = 60.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(
        url,
        headers={"User-Agent": "MegaDateTime-EarthViewer/0.1 (educational; local cache)"},
    )
    print(f"Downloading {dest.name} ...")
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — curated NASA URLs only
        dest.write_bytes(resp.read())
    print(f"  saved {dest} ({dest.stat().st_size:,} bytes)")


def main() -> None:
    config.ensure_data_dirs()
    for name, url in config.FREE_TEXTURE_URLS.items():
        dest = config.texture_path(name)
        if dest.is_file() and dest.stat().st_size > 10_000:
            print(f"Skip (exists): {dest.name}")
            continue
        try:
            fetch(url, dest)
        except Exception as exc:
            print(f"Failed {name}: {exc}")
            print("  EarthViewer can still run with procedural placeholders.")


if __name__ == "__main__":
    main()
