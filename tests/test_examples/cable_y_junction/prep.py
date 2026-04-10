"""Generate cable_y_junction recipe.

Builds a Y-shaped graph of 3 branches meeting at a junction, each branch
with 20 rod segments. The tip of the first branch is pinned in place.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).parent

NUM_SEG = 20
SEG_LEN = 0.03
CABLE_RADIUS = 0.01
Z0 = 1.25


def y_dirs_xy() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0],
        [-0.5, math.sqrt(3.0) * 0.5, 0.0],
        [-0.5, -math.sqrt(3.0) * 0.5, 0.0],
    ]


def main() -> None:
    junction = [0.0, 0.0, Z0]
    node_positions: list[list[float]] = [junction]
    edges: list[list[int]] = []
    for d in y_dirs_xy():
        prev = 0
        for i in range(1, NUM_SEG + 1):
            p = [junction[0] + d[0] * i * SEG_LEN,
                 junction[1] + d[1] * i * SEG_LEN,
                 junction[2] + d[2] * i * SEG_LEN]
            node_positions.append(p)
            cur = len(node_positions) - 1
            edges.append([prev, cur])
            prev = cur

    # Index of the body at the tip of the first branch.
    # add_rod_graph creates one body per edge; edges are added in branch order.
    # Tip of first branch = edge index NUM_SEG - 1 (within that branch, first).
    pinned_edge = NUM_SEG - 1

    ops: list[dict] = [
        {"op": "set_default_shape_cfg", "args": {"ke": 1.0e4, "kd": 1.0e-1, "mu": 1.0}},
        {"op": "add_rod_graph", "args": {
            "node_positions": node_positions,
            "edges": edges,
            "radius": CABLE_RADIUS,
            "stretch_stiffness": 1.0e9,
            "stretch_damping": 0.0,
            "bend_stiffness": 1.0e0,
            "bend_damping": 1.0e-1,
            "label": "y_graph",
            "wrap_in_articulation": True,
        }},
        {"op": "pin_body", "args": {"body": pinned_edge}},
        {"op": "add_ground_plane"},
        {"op": "color", "args": {"balance_colors": False}},
    ]
    recipe = {"schema": "newton-cli/recipe/v1", "ops": ops}
    (HERE / "recipe.json").write_text(json.dumps(recipe))
    print(f"wrote recipe.json: Y-junction, {len(node_positions)} nodes, {len(edges)} edges")


if __name__ == "__main__":
    main()
