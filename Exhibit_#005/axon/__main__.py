"""python -m axon [file.cog]"""

from __future__ import annotations

import sys

from .editor import main


if __name__ == "__main__":
    sys.exit(main())
