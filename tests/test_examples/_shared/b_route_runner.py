"""Generic B-route runner for any Newton example.

Usage (via newton-cli run-script):

    newton-cli run-script _shared/b_route_runner.py \
        --forward <example_name> \
        --forward <num_frames> \
        --artifact-dir outputs

It rewrites sys.argv to:
    newton.examples <example_name> --viewer null --test --num-frames <N>

then calls newton.examples.main(). Newton's --test flag invokes
Example.test_final() automatically at the end of the headless run, so a
zero exit code means the example passed its own validation.

After the run we capture the example object via a tiny monkey-patch on
newton.examples.run and dump body/joint/particle state arrays into the
CLI-injected artifact directory for downstream visualization.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("usage: b_route_runner.py <example_name> [num_frames]", file=sys.stderr)
    sys.exit(2)

example_name = sys.argv[1]
num_frames = sys.argv[2] if len(sys.argv) >= 3 else "30"

sys.argv = [
    "newton.examples",
    example_name,
    "--viewer", "null",
    "--test",
    "--num-frames", str(num_frames),
]

import numpy as np  # noqa: E402
import newton.examples  # noqa: E402

captured: dict = {}
_orig_run = newton.examples.run


def _capturing_run(example, args):
    captured["example"] = example
    captured["args"] = args
    return _orig_run(example, args)


newton.examples.run = _capturing_run

newton.examples.main()  # raises SystemExit on test failure

# --- post: dump final state for downstream tools / human inspection -----
example = captured.get("example")
if example is None:
    print("WARN: newton.examples.run was never called; nothing to save", file=sys.stderr)
    sys.exit(0)

artifact_dir = Path(os.environ.get("NEWTON_CLI_ARTIFACT_DIR", "."))
artifact_dir.mkdir(parents=True, exist_ok=True)

state = (
    getattr(example, "state_0", None)
    or getattr(example, "state", None)
    or getattr(example, "state_in", None)
)
saved: dict = {}
if state is not None:
    for name in (
        "body_q", "body_qd",
        "joint_q", "joint_qd",
        "particle_q", "particle_qd",
    ):
        arr = getattr(state, name, None)
        if arr is None:
            continue
        try:
            saved[name] = arr.numpy()
        except Exception:
            pass

if saved:
    np.savez(artifact_dir / "final.npz", **saved)
    print(f"OK — saved {len(saved)} state arrays to {artifact_dir / 'final.npz'}")
else:
    print(f"OK — example {example_name!r} ran but no state arrays were captured")
