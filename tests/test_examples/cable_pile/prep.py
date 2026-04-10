"""Generate cable_pile recipe by baking the 40-cable layout into JSON.

Mirrors example_cable_pile.py: 4 layers x 10 lanes of wavy rods stacked on
the ground plane, alternating X/Y orientation per layer. We import Newton's
own helper functions at prep time so the geometry is identical.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import warp as wp

import newton
from newton.utils import (
    create_parallel_transport_cable_quaternions,
    create_straight_cable_points,
)

HERE = Path(__file__).parent

NUM_ELEMENTS = 40
SEGMENT_LENGTH = 0.05
CABLE_RADIUS = 0.012
LAYERS = 4
LANES_PER_LAYER = 10
LANE_SPACING = max(8.0 * CABLE_RADIUS, 0.15)
LAYER_GAP = CABLE_RADIUS * 6.0
CABLE_LENGTH = NUM_ELEMENTS * SEGMENT_LENGTH

WAV = 0.5
TWIST = 0.0
CYCLES = 2.0
WAVINESS_SCALE = 0.05


def vec3_to_list(v):
    return [float(v[0]), float(v[1]), float(v[2])]


def quat_to_list(q):
    return [float(q[0]), float(q[1]), float(q[2]), float(q[3])]


def build_one_cable(layer: int, lane: int):
    orient = "x" if (layer % 2 == 0) else "y"
    z0 = 0.3 + layer * LAYER_GAP
    offset = (lane - (LANES_PER_LAYER - 1) * 0.5) * LANE_SPACING
    if orient == "x":
        start = wp.vec3(0.0, offset, z0)
        dir_vec = wp.vec3(1.0, 0.0, 0.0)
        ortho_vec = wp.vec3(0.0, 1.0, 0.0)
    else:
        start = wp.vec3(offset, 0.0, z0)
        dir_vec = wp.vec3(0.0, 1.0, 0.0)
        ortho_vec = wp.vec3(1.0, 0.0, 0.0)

    start0 = start - 0.5 * CABLE_LENGTH * dir_vec
    pts = create_straight_cable_points(
        start=start0,
        direction=dir_vec,
        length=CABLE_LENGTH,
        num_segments=NUM_ELEMENTS,
    )

    if WAV > 0.0:
        amp = WAV * CABLE_LENGTH * WAVINESS_SCALE
        for i in range(len(pts)):
            t = i / NUM_ELEMENTS
            phase = 2.0 * math.pi * CYCLES * t
            pts[i] = pts[i] + ortho_vec * (amp * math.sin(phase))

    quats = create_parallel_transport_cable_quaternions(pts, twist_total=TWIST)

    return (
        [vec3_to_list(p) for p in pts],
        [quat_to_list(q) for q in quats],
    )


def main():
    ops = [
        {"op": "set_builder_attr", "args": {"name": "rigid_gap", "value": 0.05}},
        {"op": "set_default_shape_cfg", "args": {
            "ke": 1.0e6,
            "kd": 1.0e-1,
            "mu": 5.0,
        }},
        {"op": "add_ground_plane", "args": {}},
    ]

    cable_cfg = {
        "$shape_cfg": {
            "ke": 1.0e6,
            "kd": 1.0e-1,
            "mu": 5.0,
        }
    }

    total_cables = 0
    for layer in range(LAYERS):
        for lane in range(LANES_PER_LAYER):
            pts, quats = build_one_cable(layer, lane)
            ops.append({
                "op": "add_rod",
                "args": {
                    "positions": pts,
                    "quaternions": quats,
                    "radius": CABLE_RADIUS,
                    "cfg": cable_cfg,
                    "bend_stiffness": 1.0e1,
                    "bend_damping": 5.0e-1,
                    "stretch_stiffness": 1.0e6,
                    "stretch_damping": 1.0e-4,
                    "label": f"cable_l{layer}_{lane}",
                },
            })
            total_cables += 1

    # VBD coloring (must come after all bodies are added, before finalize).
    ops.append({"op": "color", "args": {}})

    recipe = {"schema": "newton-cli/recipe/v1", "ops": ops}
    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe))
    print(f"wrote {out}: {total_cables} cables, {len(ops)} ops, {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()
