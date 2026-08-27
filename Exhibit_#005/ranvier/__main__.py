"""python -m ranvier <file.cog>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compiler import Compiler
from .interpreter import Interpreter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ranvier",
        description="Ranvier (.cog) — named for the node of Ranvier. Never compile a destiny when you only measured a state.",
    )
    parser.add_argument("source", help="Path to a .cog program")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only; do not run the interpreter",
    )
    parser.add_argument(
        "--models",
        default=None,
        help="Optional path to the models/ directory",
    )
    args = parser.parse_args(argv)

    path = Path(args.source)
    if not path.exists():
        print(f"Ranvier: file not found: {path}", file=sys.stderr)
        return 2

    compiled = Compiler(models_dir=args.models).compile_file(path)
    if compiled.errors:
        print(compiled.report())
        return 1
    if args.check:
        print(compiled.report())
        for note in compiled.notes:
            print(f"  {note}")
        return 0
    print(Interpreter(compiled).run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
