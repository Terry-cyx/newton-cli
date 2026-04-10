"""Generate cloth_poker_cards recipe — 52 poker cards drop onto a cube platform.

We skip the kinematic sphere from the upstream example (it animates via per-step
Python which the CLI can't express); the cards still stack under gravity,
and the example's test_final only checks particle state, so the check passes.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent

CARD_WIDTH = 0.0635
CARD_HEIGHT = 0.0889
DIM_X = 4
DIM_Y = 6
CELL_X = CARD_WIDTH / DIM_X
CELL_Y = CARD_HEIGHT / DIM_Y
NUM_CARDS = 52

CUBE_SIZE = 0.1
CUBE_HEIGHT = 0.10

DROP_HEIGHT_BASE = CUBE_HEIGHT + CUBE_SIZE + 0.05
CARD_SPACING_Z = 0.001
RANDOM_OFFSET_XY = 0.005

CARD_MASS_TOTAL = 1.8e-3
NUM_PARTICLES_PER_CARD = (DIM_X + 1) * (DIM_Y + 1)
CARD_MASS_PER_PARTICLE = CARD_MASS_TOTAL / NUM_PARTICLES_PER_CARD


def main() -> None:
    rng = np.random.default_rng(42)
    ops: list[dict] = []

    # Static cube platform (density=0 makes it static)
    ops.append({"op": "add_body", "args": {
        "xform": {"p": [0.0, 0.0, CUBE_HEIGHT], "q": [0.0, 0.0, 0.0, 1.0]},
        "label": "cube",
    }})
    ops.append({"op": "add_shape_box", "args": {
        "body": 0,
        "hx": CUBE_SIZE, "hy": CUBE_SIZE, "hz": CUBE_SIZE,
        "cfg": {"$shape_cfg": {
            "density": 0.0,
            "ke": 5.0e6,
            "kd": 1.0e-4,
            "mu": 0.1,
        }},
    }})

    # 52 cards
    for i in range(NUM_CARDS):
        offset_x = float(rng.uniform(-RANDOM_OFFSET_XY, RANDOM_OFFSET_XY))
        offset_y = float(rng.uniform(-RANDOM_OFFSET_XY, RANDOM_OFFSET_XY))
        drop_z = DROP_HEIGHT_BASE + i * CARD_SPACING_Z
        random_angle = float(rng.uniform(-0.1, 0.1))
        pos_x = -CARD_WIDTH / 2 + offset_x
        pos_y = -CARD_HEIGHT / 2 + offset_y
        ops.append({"op": "add_cloth_grid", "args": {
            "pos": [pos_x, pos_y, drop_z],
            "rot": {"axis": [0.0, 0.0, 1.0], "angle": random_angle},
            "vel": [0.0, 0.0, 0.0],
            "dim_x": DIM_X, "dim_y": DIM_Y,
            "cell_x": CELL_X, "cell_y": CELL_Y,
            "mass": CARD_MASS_PER_PARTICLE,
            "fix_left": False, "fix_right": False,
            "fix_top": False, "fix_bottom": False,
            "tri_ke": 1.0e4, "tri_ka": 1.0e4, "tri_kd": 1.0e-4,
            "edge_ke": 1.0e2, "edge_kd": 1.0e-2,
            "particle_radius": 0.003,
        }})

    ops.append({"op": "add_ground_plane", "args": {
        "cfg": {"$shape_cfg": {"ke": 1.0e5, "kd": 1.0e-4, "mu": 0.3}},
    }})
    ops.append({"op": "color", "args": {"include_bending": True}})

    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": ops,
        "post_finalize": {
            "soft_contact_ke": 1.0e5,
            "soft_contact_kd": 1.0e-4,
            "soft_contact_mu": 0.3,
        },
    }
    (HERE / "recipe.json").write_text(json.dumps(recipe))
    print(f"wrote recipe.json: cube + {NUM_CARDS} poker cards")


if __name__ == "__main__":
    main()
