"""B-route demo: drive `basic_conveyor` end-to-end and dump its final state.

This is the canonical "run-script" pattern for Newton examples that need
per-step Python (custom @wp.kernel here drives the kinematic belt motion).

The agent's responsibility is to:
  1. Pick the example name.
  2. Decide how many frames + headless flag.
  3. After the run, dump whatever state arrays it wants into the artifact dir.

Newton's own --test flag automatically calls Example.test_final() at the
end of the headless run, so success = exit 0 and no exception.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 1. Run the example via Newton's own runner.
sys.argv = [
    "newton.examples",
    "basic_conveyor",
    "--viewer", "null",
    "--test",
    "--num-frames", "30",
]

import numpy as np  # noqa: E402
import newton.examples  # noqa: E402

# 2. Patch newton.examples.run so we can grab the example object after it
#    finishes (without modifying upstream Newton). The hook captures the
#    `example` arg and forwards to the original implementation.
captured: dict = {}
_orig_run = newton.examples.run


def _capturing_run(example, args):
    captured["example"] = example
    captured["args"] = args
    return _orig_run(example, args)


newton.examples.run = _capturing_run

# 3. Run.
newton.examples.main()

# 4. Save final state into the CLI-injected artifact directory.
example = captured["example"]
artifact_dir = Path(os.environ["NEWTON_CLI_ARTIFACT_DIR"])
artifact_dir.mkdir(parents=True, exist_ok=True)

state = getattr(example, "state_0", None) or getattr(example, "state", None)
saved = {}
for name in ("body_q", "body_qd", "joint_q", "joint_qd", "particle_q", "particle_qd"):
    arr = getattr(state, name, None)
    if arr is None:
        continue
    try:
        saved[name] = arr.numpy()
    except Exception:
        pass

np.savez(artifact_dir / "final.npz", **saved)
print(f"OK — saved {len(saved)} arrays to {artifact_dir / 'final.npz'}")
