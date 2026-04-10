"""Generate a basic_heightfield recipe with a 50x50 sin/cos elevation grid.

Output:
    tests/test_examples/basic_heightfield/recipe.json

Called from run.ps1 before `newton-cli model build`.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
NROW, NCOL = 50, 50
HX, HY = 5.0, 5.0
DROP_Z = 1.0
SPHERE_POSITIONS = [
    (-2.0, -2.0),
    (0.0, 0.0),
    (2.0, 2.0),
    (-1.0, 1.5),
    (1.5, -1.0),
]


def _elevation() -> list[list[float]]:
    x = np.linspace(-HX, HX, NCOL)
    y = np.linspace(-HY, HY, NROW)
    xx, yy = np.meshgrid(x, y)
    elevation = np.sin(xx * 1.0) * np.cos(yy * 1.0) * 0.5
    return elevation.astype(float).tolist()


def main() -> None:
    ops: list[dict] = [
        {
            "op": "add_shape_heightfield",
            "args": {
                "heightfield": {
                    "$heightfield": {
                        "data": _elevation(),
                        "nrow": NROW,
                        "ncol": NCOL,
                        "hx": HX,
                        "hy": HY,
                    }
                }
            },
        }
    ]
    for i, (x_pos, y_pos) in enumerate(SPHERE_POSITIONS):
        ops.append({
            "op": "add_body",
            "args": {"xform": {"p": [x_pos, y_pos, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]}},
        })
        ops.append({
            "op": "add_shape_sphere",
            "args": {"body": i, "radius": 0.3},
        })

    recipe = {"schema": "newton-cli/recipe/v1", "ops": ops}
    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe))
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
