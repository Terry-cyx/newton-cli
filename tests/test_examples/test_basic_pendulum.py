"""Wave A.1 — basic_pendulum reproduced via newton-cli.

The test:
  1. Writes a recipe JSON that mirrors example_basic_pendulum.py.
  2. Runs `newton-cli model build` to materialize the recipe into a model file.
  3. Runs `newton-cli sim run` to step the simulation 100 frames @ 100 fps,
     10 substeps, on CPU, with SolverXPBD (matching the example).
  4. Loads the resulting State and runs the example's OWN test_final()
     predicates via newton.examples.test_body_state.

If those predicates pass, the CLI has successfully reproduced the example.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import newton
import newton.examples

from newton_cli.recipes import build_model_from_recipe
from newton_cli.state_io import load_state_npz_into
from tests._cli import run_cli

PENDULUM_RECIPE = {
    "schema": "newton-cli/recipe/v1",
    "ops": [
        {"op": "add_link"},
        {"op": "add_shape_box", "args": {"body": 0, "hx": 1.0, "hy": 0.1, "hz": 0.1}},
        {"op": "add_link"},
        {"op": "add_shape_box", "args": {"body": 1, "hx": 1.0, "hy": 0.1, "hz": 0.1}},
        {
            "op": "add_joint_revolute",
            "args": {
                "parent": -1,
                "child": 0,
                "axis": [0.0, 1.0, 0.0],
                "parent_xform": {
                    "p": [0.0, 0.0, 5.0],
                    "q": {"axis": [0.0, 0.0, 1.0], "angle": -1.5707963267948966},
                },
                "child_xform": {
                    "p": [-1.0, 0.0, 0.0],
                    "q": [0.0, 0.0, 0.0, 1.0],
                },
            },
        },
        {
            "op": "add_joint_revolute",
            "args": {
                "parent": 0,
                "child": 1,
                "axis": [0.0, 1.0, 0.0],
                "parent_xform": {"p": [1.0, 0.0, 0.0], "q": [0.0, 0.0, 0.0, 1.0]},
                "child_xform": {"p": [-1.0, 0.0, 0.0], "q": [0.0, 0.0, 0.0, 1.0]},
            },
        },
        {"op": "add_articulation", "args": {"joints": [0, 1], "label": "pendulum"}},
        {"op": "add_ground_plane"},
    ],
}


class TestBasicPendulum(unittest.TestCase):
    def test_pendulum_via_cli_passes_native_validation(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "pendulum_recipe.json"
            model_path = tdp / "pendulum.model.json"
            state_path = tdp / "pendulum_final.npz"
            recipe_path.write_text(json.dumps(PENDULUM_RECIPE))

            # Step 1: build the model from the recipe.
            run_cli(
                "model", "build",
                "--recipe", str(recipe_path),
                "--out", str(model_path),
                "--json",
                check=True,
            )
            self.assertTrue(model_path.exists(), "model file should be written")

            # Step 2: run the simulation.
            run_cli(
                "sim", "run",
                "--model", str(model_path),
                "--solver", "SolverXPBD",
                "--num-frames", "100",
                "--fps", "100",
                "--substeps", "10",
                "--device", "cpu",
                "--out", str(state_path),
                "--json",
                check=True,
            )
            self.assertTrue(state_path.exists(), "state file should be written")

            # Step 3: rebuild the in-process model from the recipe and load the
            # final state into it. The recipe IS the model — re-executing it
            # gives us the same Model the CLI produced.
            model = build_model_from_recipe(model_path, device="cpu")
            state = model.state()
            load_state_npz_into(state, state_path)

            # Step 4: run the EXAMPLE'S OWN test_final predicates verbatim.
            newton.examples.test_body_state(
                model,
                state,
                "pendulum links in correct area",
                lambda q, qd: abs(q[0]) < 1e-5 and abs(q[1]) < 1.0 and q[2] < 5.0 and q[2] > 0.0,
                [0, 1],
            )

            def check_velocities(_q, qd):
                check = abs(qd[0]) < 1e-4 and abs(qd[6]) < 1e-4
                check = check and abs(qd[1]) < 10.0 and abs(qd[2]) < 5.0 and abs(qd[3]) < 10.0 and abs(qd[4]) < 10.0
                return check

            newton.examples.test_body_state(
                model,
                state,
                "pendulum links have reasonable velocities",
                check_velocities,
                [0, 1],
            )


if __name__ == "__main__":
    unittest.main()
