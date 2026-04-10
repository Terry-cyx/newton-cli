"""Resolve a Newton asset path at prep time.

Usage:
    python prep_asset.py download_asset <name> [subpath...]
        -> prints the absolute path returned by newton.utils.download_asset(name),
           optionally joined with subpath components.

    python prep_asset.py get_asset <name>
        -> prints the absolute path returned by newton.examples.get_asset(name).

Used from run.ps1 scripts to fill in asset paths before writing the recipe.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: prep_asset.py (download_asset|get_asset) <name> [subpath...]",
              file=sys.stderr)
        return 2

    mode = sys.argv[1]
    name = sys.argv[2]
    subpath = sys.argv[3:]

    if mode == "download_asset":
        import newton.utils  # noqa: PLC0415

        base = Path(newton.utils.download_asset(name))
    elif mode == "get_asset":
        import newton.examples  # noqa: PLC0415

        base = Path(newton.examples.get_asset(name))
    else:
        print(f"unknown mode: {mode}", file=sys.stderr)
        return 2

    resolved = base.joinpath(*subpath) if subpath else base
    # Print only the path — no banner, no newline noise.
    sys.stdout.write(str(resolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
