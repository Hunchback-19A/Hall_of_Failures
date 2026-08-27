"""Start Axon without a console window.

Double-click this file, or make a Windows shortcut to it and set the
shortcut's icon to Icon.ico. Pin that shortcut to the taskbar so Axon
shows as itself instead of Python.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from axon.editor import main

if __name__ == "__main__":
    raise SystemExit(main())
