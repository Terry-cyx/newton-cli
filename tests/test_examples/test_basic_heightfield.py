"""Wave B.2 — basic_heightfield reproduced via newton-cli.

Brings new recipe surface:
  - {"$heightfield": {data, nrow, ncol, hx, hy}} tag for inline Heightfield.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from newton_cli.recipes import build_model_from_recipe
from newton_cli.state_io import load_state_npz_into
from tests._cli import run_cli

NROW, NCOL = 50, 50
HX, HY = 5.0, 5.0


def _make_elevation() -> list[list[float]]:
    x = np.linspace(-HX, HX, NCOL)
    y = np.linspace(-HY, HY, NROW)
    xx, yy = np.meshgrid(x, y)
    elevation = np.sin(xx * 1.0) * np.cos(yy * 1.0) * 0.5
    return elevation.astype(float).tolist()


SPHERE_POSITIONS = [
    (-2.0, -2.0),
    (0.0, 0.0),
    (2.0, 2.0),
    (-1.0, 1.5),
    (1.5, -1.0),
]
DROP_Z = 1.0


def _build_recipe() -> dict:
    ops: list[dict] = [
        {
            "op": "add_shape_heightfield",
            "args": {
                "heightfield": {
                    "$heightfield": {
                        "data": _make_elevation(),
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
        body_idx = i  # bodies are added in order, no body before this loop
        ops.append({
            "op": "add_body",
            "args": {
                "xform": {"p": [x_pos, y_pos, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            },
        })
        ops.append({
            "op": "add_shape_sphere",
            "args": {"body": body_idx, "radius": 0.3},
        })
    return {"schema": "newton-cli/recipe/v1", "ops": ops}


class TestBasicHeightfield(unittest.TestCase):
    def test_heightfield_via_cli_passes_native_validation(self):
        recipe = _build_recipe()
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "hfield_recipe.json"
            model_path = tdp / "hfield.model.json"
            state_path = tdp / "hfield_final.npz"
            recipe_path.write_text(json.dumps(recipe))

            run_cli(
                "model", "build",
                "--recipe", str(recipe_path),
                "--out", str(model_path),
                "--json",
                check=True,
            )

            run_cli(
                "sim", "run",
                "--model", str(model_path),
                "--solver", "SolverXPBD",
                "--solver-arg", "iterations=10",
                "--num-frames", "100",
                "--fps", "100",
                "--substeps", "10",
                "--device", "cpu",
                "--out", str(state_path),
                "--json",
                check=True,
            )

            # The example's test_final reads body_q[i, 2] from the State and
            # asserts z > -1.0 for every sphere. Reproduce that on the loaded state.
            with np.load(state_path) as data:
                body_q = data["body_q"]
                for i in range(len(SPHERE_POSITIONS)):
                    z = float(body_q[i, 2])
                    self.assertGreater(
                        z, -1.0,
                        f"sphere body {i} fell through heightfield: z={z:.4f}",
                    )


if __name__ == "__main__":
    unittest.main()
