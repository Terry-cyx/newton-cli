"""Generate a small pyramid recipe (1 pyramid, 3 rows = 6 boxes).

The bundled example defaults to 20 pyramids x 20 rows = 4200 boxes which
is overkill for a test. We use the smallest meaningful pyramid and still
verify the "top cube doesn't topple" predicate from test_final.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent

CUBE_HALF = 0.4
CUBE_SPACING = 2.1 * CUBE_HALF
PYRAMID_SIZE = 3
NUM_PYRAMIDS = 1


def main() -> None:
    ops: list[dict] = [
        {"op": "add_shape_plane", "args": {
            "body": -1,
            "xform": {"p": [0.0, 0.0, 0.0], "q": [0.0, 0.0, 0.0, 1.0]},
            "width": 0.0,
            "length": 0.0,
        }},
    ]

    body_idx = 0
    top_indices: list[int] = []
    for level in range(PYRAMID_SIZE):
        num_cubes_in_row = PYRAMID_SIZE - level
        row_width = (num_cubes_in_row - 1) * CUBE_SPACING
        z_pos = level * CUBE_SPACING + CUBE_HALF
        for i in range(num_cubes_in_row):
            x_pos = -row_width / 2 + i * CUBE_SPACING
            ops.append({"op": "add_body", "args": {
                "xform": {"p": [x_pos, 0.0, z_pos], "q": [0.0, 0.0, 0.0, 1.0]},
            }})
            ops.append({"op": "add_shape_box", "args": {
                "body": body_idx, "hx": CUBE_HALF, "hy": CUBE_HALF, "hz": CUBE_HALF,
            }})
            if level == PYRAMID_SIZE - 1:
                top_indices.append(body_idx)
            body_idx += 1

    recipe = {"schema": "newton-cli/recipe/v1", "ops": ops}
    (HERE / "recipe.json").write_text(json.dumps(recipe, indent=2))
    (HERE / "top_body_indices.json").write_text(json.dumps(top_indices))
    print(f"wrote recipe.json with {body_idx} bodies ({PYRAMID_SIZE}-row pyramid)")
    print(f"top body indices: {top_indices}")


if __name__ == "__main__":
    main()
