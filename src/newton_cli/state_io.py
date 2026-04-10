"""State serialization via NumPy .npz.

A serialized State is just a small bag of arrays:
  - body_q   (N, 7)  per-body pose [px, py, pz, qx, qy, qz, qw]
  - body_qd  (N, 6)  per-body spatial velocity
  - joint_q  (M,)    generalized coordinates
  - joint_qd (M,)    generalized velocities

Optional fields are omitted gracefully if the State doesn't carry them
(e.g. soft-body / particle examples will extend this in later waves).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import warp as wp

import newton

_FIELDS = (
    "body_q", "body_qd", "joint_q", "joint_qd",
    "particle_q", "particle_qd",
)


def save_state_npz(state: newton.State, path: str | Path) -> None:
    payload: dict[str, np.ndarray] = {}
    for field in _FIELDS:
        arr = getattr(state, field, None)
        if arr is None:
            continue
        if isinstance(arr, wp.array):
            payload[field] = arr.numpy()
        else:
            payload[field] = np.asarray(arr)
    np.savez(Path(path), **payload)


def load_state_npz_into(state: newton.State, path: str | Path) -> None:
    """Copy arrays from an .npz back into a freshly-allocated State."""
    data = np.load(Path(path))
    for field in _FIELDS:
        if field not in data.files:
            continue
        target = getattr(state, field, None)
        if target is None:
            continue
        if isinstance(target, wp.array):
            target.assign(data[field])
        else:
            setattr(state, field, data[field])
