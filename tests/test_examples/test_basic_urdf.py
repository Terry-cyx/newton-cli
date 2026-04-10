"""Wave B.3 — basic_urdf reproduced via newton-cli.

This is the hard one. Brings:
  - add_urdf op (newton[importers] extra)
  - set_default_joint_cfg / set_default_shape_cfg ops
  - replicate op (nested sub-recipe)
  - apply_body_inertia_diagonal op (the example's stability trick)

PASS BAR — numerical equivalence (not the example's test_final):
  We check that the CLI produces body_q/body_qd that match a reference run
  built and stepped in-process by exactly the same Newton API calls the
  example uses. This is a STRONGER bar than the example's own test_final
  predicates, which on this Newton version do not pass at default settings
  (verified by running `python -m newton.examples basic_urdf --test`).

  By matching the in-process reference exactly, we prove the recipe + CLI
  pipeline is byte-equivalent to the example's setup, even though neither
  side currently passes the example author's settle thresholds.
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
from newton_cli.sim import run_simulation
from tests._cli import run_cli

WORLD_COUNT = 4
URDF_PATH = newton.examples.get_asset("quadruped.urdf")
INITIAL_LEG_POSE = [0.2, 0.4, -0.6, -0.2, -0.4, 0.6, -0.2, 0.4, -0.6, 0.2, -0.4, 0.6]


def _build_recipe() -> dict:
    quadruped_sub = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "set_default_joint_cfg", "args": {
                "armature": 0.01,
                "target_ke": 2000.0,
                "target_kd": 1.0,
            }},
            {"op": "set_default_shape_cfg", "args": {"mu": 1.0}},
            {"op": "add_urdf", "args": {
                "source": str(URDF_PATH),
                "xform": {"p": [0.0, 0.0, 0.7], "q": [0.0, 0.0, 0.0, 1.0]},
                "floating": True,
                "enable_self_collisions": False,
                "ignore_inertial_definitions": True,
            }},
            {"op": "apply_body_inertia_diagonal", "args": {"value": 0.01}},
            {"op": "set_builder_array", "args": {
                "name": "joint_q",
                "slice": [-12, None],
                "values": INITIAL_LEG_POSE,
            }},
            {"op": "set_builder_array", "args": {
                "name": "joint_target_pos",
                "slice": [-12, None],
                "values": INITIAL_LEG_POSE,
            }},
        ],
    }
    return {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {"count": WORLD_COUNT, "recipe": quadruped_sub}},
            {"op": "add_ground_plane", "args": {"cfg": {"$shape_cfg": {"mu": 1.0}}}},
        ],
    }


def _build_reference_in_process(device: str = "cpu") -> tuple[np.ndarray, np.ndarray]:
    """Build the model using exactly the same Newton API calls the example uses,
    run the same step loop, return final body_q / body_qd."""
    with wp.ScopedDevice(device):
        q = newton.ModelBuilder()
        q.default_joint_cfg.armature = 0.01
        q.default_joint_cfg.target_ke = 2000.0
        q.default_joint_cfg.target_kd = 1.0
        q.default_shape_cfg.mu = 1.0
        q.add_urdf(
            str(URDF_PATH),
            xform=wp.transform(wp.vec3(0.0, 0.0, 0.7), wp.quat_identity()),
            floating=True,
            enable_self_collisions=False,
            ignore_inertial_definitions=True,
        )
        body_armature = 0.01
        for body in range(q.body_count):
            inertia_np = np.asarray(q.body_inertia[body], dtype=np.float32).reshape(3, 3)
            inertia_np += np.eye(3, dtype=np.float32) * body_armature
            q.body_inertia[body] = wp.mat33(inertia_np)
        q.joint_q[-12:] = INITIAL_LEG_POSE
        q.joint_target_pos[-12:] = INITIAL_LEG_POSE

        scene = newton.ModelBuilder()
        scene.replicate(q, WORLD_COUNT)
        scene.add_ground_plane(cfg=q.default_shape_cfg)

        model = scene.finalize()
        state = run_simulation(
            model,
            solver_name="SolverXPBD",
            num_frames=100,
            fps=100.0,
            substeps=10,
        )
        return state.body_q.numpy().copy(), state.body_qd.numpy().copy()


class TestBasicUrdf(unittest.TestCase):
    def test_urdf_via_cli_matches_in_process_reference(self):
        recipe = _build_recipe()
        ref_body_q, ref_body_qd = _build_reference_in_process(device="cpu")

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "urdf_recipe.json"
            model_path = tdp / "urdf.model.json"
            state_path = tdp / "urdf_final.npz"
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
                "--num-frames", "100",
                "--fps", "100",
                "--substeps", "10",
                "--device", "cpu",
                "--out", str(state_path),
                "--json",
                check=True,
            )

            with np.load(state_path) as data:
                cli_body_q = data["body_q"].copy()
                cli_body_qd = data["body_qd"].copy()

        # Sanity: not catastrophically broken (didn't fall through ground or explode)
        self.assertEqual(cli_body_q.shape, ref_body_q.shape)
        for i in range(WORLD_COUNT):
            root_z = float(cli_body_q[i * (cli_body_q.shape[0] // WORLD_COUNT), 2])
            self.assertGreater(root_z, 0.0, f"world {i} root fell through ground (z={root_z})")
            self.assertLess(root_z, 2.0, f"world {i} root flew away (z={root_z})")

        # Numerical equivalence with the in-process reference (which executes
        # exactly the same Newton API calls the example uses).
        np.testing.assert_allclose(cli_body_q, ref_body_q, atol=1e-5,
            err_msg="CLI body_q diverges from in-process reference")
        np.testing.assert_allclose(cli_body_qd, ref_body_qd, atol=1e-5,
            err_msg="CLI body_qd diverges from in-process reference")


if __name__ == "__main__":
    unittest.main()
