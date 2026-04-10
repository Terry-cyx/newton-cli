"""Entry point.

We must capture Warp's init banner BEFORE anything else imports newton/warp,
because `import newton` transitively imports warp and triggers wp.init() which
prints to stdout. Our JSON envelope contract requires a clean stdout.
"""

from __future__ import annotations

import io
import sys

_warp_banner = ""


def _silent_preinit() -> None:
    """Trigger newton + warp imports while capturing stdout."""
    global _warp_banner
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        import newton  # noqa: F401, PLC0415
        import warp as wp  # noqa: PLC0415

        wp.get_devices()  # force wp.init() if it hasn't fired yet
    finally:
        sys.stdout = old
        _warp_banner = buf.getvalue()


_silent_preinit()

from newton_cli.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
