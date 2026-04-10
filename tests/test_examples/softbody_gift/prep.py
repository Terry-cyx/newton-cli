"""Generate softbody_gift recipe with pre-computed tet + cloth geometry.

The upstream example generates cloth strap loops procedurally in Python. We
run the same Python at prep time and bake the resulting vertex/index arrays
into the recipe JSON so the CLI build step is self-contained.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
BASE_HEIGHT = 20.0
SPACING = 1.01

PYRAMID_PARTICLES = [
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0],
    [0.0, 1.0, 0.0], [1.0, 1.0, 0.0], [2.0, 1.0, 0.0],
    [0.0, 2.0, 0.0], [1.0, 2.0, 0.0], [2.0, 2.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [2.0, 0.0, 1.0],
    [0.0, 1.0, 1.0], [1.0, 1.0, 1.0], [2.0, 1.0, 1.0],
    [0.0, 2.0, 1.0], [1.0, 2.0, 1.0], [2.0, 2.0, 1.0],
]

PYRAMID_TET_INDICES_FLAT = [
    0, 1, 3, 9,    1, 4, 3, 13,   1, 3, 9, 13,   3, 9, 13, 12,
    1, 9, 10, 13,  1, 2, 4, 10,   2, 5, 4, 14,   2, 4, 10, 14,
    4, 10, 14, 13, 2, 10, 11, 14, 3, 4, 6, 12,   4, 7, 6, 16,
    4, 6, 12, 16,  6, 12, 16, 15, 4, 12, 13, 16, 4, 5, 7, 13,
    5, 8, 7, 17,   5, 7, 13, 17,  7, 13, 17, 16, 5, 13, 14, 17,
]


def cloth_loop_around_box(hx: float, hz: float, width: float,
                          center_y: float = 0.0, nu: int = 120, nv: int = 6):
    verts = []
    faces = []
    P = 4.0 * (hx + hz)
    for i in range(nu):
        s = (i / nu) * P
        if s < 2 * hx:
            x, z = -hx + s, -hz
        elif s < 2 * hx + 2 * hz:
            x, z = hx, -hz + (s - 2 * hx)
        elif s < 4 * hx + 2 * hz:
            x, z = hx - (s - (2 * hx + 2 * hz)), hz
        else:
            x, z = -hx, hz - (s - (4 * hx + 2 * hz))
        for j in range(nv):
            v = (j / (nv - 1) - 0.5) * width
            verts.append([x, center_y + v, z])

    def idx(i, j):
        return (i % nu) * nv + j

    for i in range(nu):
        for j in range(nv - 1):
            faces.append([idx(i, j), idx(i + 1, j), idx(i, j + 1)])
            faces.append([idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)])
    return verts, faces


def main() -> None:
    strap1_verts, strap1_faces = cloth_loop_around_box(hx=1.01, hz=2.02, width=0.6)
    strap2_verts, strap2_faces = cloth_loop_around_box(hx=1.015, hz=2.025, width=0.6)
    strap1_idx_flat = [i for tri in strap1_faces for i in tri]
    strap2_idx_flat = [i for tri in strap2_faces for i in tri]

    ops: list[dict] = [{"op": "add_ground_plane"}]
    for i in range(4):
        ops.append({"op": "add_soft_mesh", "args": {
            "pos": [0.0, 0.0, BASE_HEIGHT + i * SPACING],
            "rot": [0.0, 0.0, 0.0, 1.0],
            "scale": 1.0,
            "vel": [0.0, 0.0, 0.0],
            "vertices": PYRAMID_PARTICLES,
            "indices": PYRAMID_TET_INDICES_FLAT,
            "density": 100.0,
            "k_mu": 100000.0,
            "k_lambda": 100000.0,
            "k_damp": 0.00001,
        }})
    # First cloth strap
    ops.append({"op": "add_cloth_mesh", "args": {
        "pos": [1.0, 1.0, BASE_HEIGHT + 1.5 * SPACING + 0.5],
        "rot": [0.0, 0.0, 0.0, 1.0],
        "scale": 1.0,
        "vel": [0.0, 0.0, 0.0],
        "vertices": strap1_verts,
        "indices": strap1_idx_flat,
        "density": 0.02,
        "tri_ke": 100000.0, "tri_ka": 100000.0, "tri_kd": 0.00001,
        "edge_ke": 0.01, "edge_kd": 0.01,
    }})
    # Second cloth strap (rotated 90° around Z)
    ops.append({"op": "add_cloth_mesh", "args": {
        "pos": [1.0, 1.0, BASE_HEIGHT + 1.5 * SPACING + 0.5],
        "rot": {"axis": [0.0, 0.0, 1.0], "angle": -math.pi / 2.0},
        "scale": 1.0,
        "vel": [0.0, 0.0, 0.0],
        "vertices": strap2_verts,
        "indices": strap2_idx_flat,
        "density": 0.02,
        "tri_ke": 100000.0, "tri_ka": 100000.0, "tri_kd": 0.00001,
        "edge_ke": 0.01, "edge_kd": 0.01,
    }})
    ops.append({"op": "color"})

    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": ops,
        "post_finalize": {
            "soft_contact_ke": 100000.0,
            "soft_contact_kd": 0.00001,
            "soft_contact_mu": 1.0,
        },
    }
    (HERE / "recipe.json").write_text(json.dumps(recipe))
    print(f"wrote recipe.json (4 soft pyramids + 2 cloth straps)")


if __name__ == "__main__":
    main()
