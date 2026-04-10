"""Wave F.1 — softbody_hanging reproduced via newton-cli.

Brings:
  - add_soft_grid recipe op (pure method dispatch)
  - post_finalize model attribute mutations (soft_contact_ke/kd/mu)
  - Particle state serialization (particle_q / particle_qd in .npz)
  - SolverVBD for volumetric soft bodies

Pass bar: the example's own test_final predicate (particles inside a
reasonable volume after simulation).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import newton
import newton.examples
import numpy as np
import warp as wp

from newton_cli.recipes import build_model_from_recipe
from newton_cli.state_io import load_state_npz_into
from tests._cli import run_cli

DIM_X, DIM_Y, DIM_Z = 12, 4, 4
CELL_SIZE = 0.1
SPACING = 0.6
DAMPING_VALUES = [1e-1, 1e-2, 1e-3, 1e-4]


def _build_recipe() -> dict:
    ops: list[dict] = [{"op": "add_ground_plane"}]
    for i, k_damp in enumerate(DAMPING_VALUES):
        y_offset = i * SPACING
        ops.append({
            "op": "add_soft_grid",
            "args": {
                "pos": [0.0, 1.0 + y_offset, 1.0],
                "rot": [0.0, 0.0, 0.0, 1.0],
                "vel": [0.0, 0.0, 0.0],
                "dim_x": DIM_X, "dim_y": DIM_Y, "dim_z": DIM_Z,
                "cell_x": CELL_SIZE, "cell_y": CELL_SIZE, "cell_z": CELL_SIZE,
                "density": 1.0e3,
                "k_mu": 1.0e5,
                "k_lambda": 1.0e5,
                "k_damp": k_damp,
                "fix_left": True,
            },
        })
    ops.append({"op": "color"})
    return {
        "schema": "newton-cli/recipe/v1",
        "ops": ops,
        "post_finalize": {
            "soft_contact_ke": 1.0e2,
            "soft_contact_kd": 0.0,
            "soft_contact_mu": 1.0,
        },
    }


class TestSoftbodyHanging(unittest.TestCase):
    def test_softbody_hanging_via_cli_passes_native_validation(self):
        recipe = _build_recipe()
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "softbody_recipe.json"
            model_path = tdp / "softbody.model.json"
            state_path = tdp / "softbody_final.npz"
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
                "--solver", "SolverVBD",
                "--solver-arg", "iterations=10",
                "--solver-arg", "particle_enable_self_contact=false",
                "--solver-arg", "particle_enable_tile_solve=false",
                "--num-frames", "100",
                "--fps", "60",
                "--substeps", "10",
                "--device", "cuda:0",
                "--out", str(state_path),
                "--json",
                check=True,
            )

            model = build_model_from_recipe(model_path, device="cuda:0")
            state = model.state()
            load_state_npz_into(state, state_path)

            # Example's own test_final predicate verbatim.
            p_lower = wp.vec3(-1.0, -0.5, 0.0)
            p_upper = wp.vec3(3.0, 4.0, 3.0)
            newton.examples.test_particle_state(
                state,
                "particles are within a reasonable volume",
                lambda q, _qd: newton.math.vec_inside_limits(q, p_lower, p_upper),
            )


if __name__ == "__main__":
    unittest.main()
