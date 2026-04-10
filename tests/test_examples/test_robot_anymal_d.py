"""Wave E.1 — robot_anymal_d reproduced via newton-cli.

Exercises:
  - download_asset("anybotics_anymal_d") (caches to user home on first run)
  - add_usd with non-default kwargs (collapse_fixed_joints=False, hide_collision_shapes)
  - set_default_shape_cfg with multiple fields (ke/kd/kf/mu)
  - set_builder_array with "fill" mode for per-dof joint target config
  - newton[sim] SolverMuJoCo with non-trivial solver kwargs

Pass bar: numerical equivalence with in-process reference.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import newton
import newton.examples
import newton.utils
import numpy as np
import warp as wp

from newton_cli.sim import run_simulation
from tests._cli import run_cli

WORLD_COUNT = 2  # example default is 8; 2 is fast enough and still exercises replicate
DEVICE = "cuda:0"  # MuJoCo requires CUDA


def _resolve_asset() -> str:
    path = newton.utils.download_asset("anybotics_anymal_d")
    return str(Path(path) / "usd" / "anymal_d.usda")


def _build_recipe(asset_file: str) -> dict:
    anymal_sub = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "register_mujoco_custom_attributes"},
            {"op": "set_default_joint_cfg", "args": {
                "limit_ke": 1.0e3,
                "limit_kd": 1.0e1,
                "friction": 1e-5,
            }},
            {"op": "set_default_shape_cfg", "args": {
                "ke": 2.0e3, "kd": 1.0e2, "kf": 1.0e3, "mu": 0.75,
            }},
            {"op": "add_usd", "args": {
                "source": asset_file,
                "collapse_fixed_joints": False,
                "enable_self_collisions": False,
                "hide_collision_shapes": True,
            }},
            # Initial root pose: x=y=0, z=0.62, identity quat
            {"op": "set_builder_array", "args": {
                "name": "joint_q",
                "slice": [0, 3],
                "values": [0.0, 0.0, 0.62],
            }},
            {"op": "set_builder_array", "args": {
                "name": "joint_q",
                "slice": [3, 7],
                "values": [0.0, 0.0, 0.0, 1.0],
            }},
            # Per-dof joint target config: target_ke=150, target_kd=5, mode=POSITION (=1)
            {"op": "set_builder_array", "args": {"name": "joint_target_ke", "fill": 150.0}},
            {"op": "set_builder_array", "args": {"name": "joint_target_kd", "fill": 5.0}},
            {"op": "set_builder_array", "args": {"name": "joint_target_mode", "fill": 1}},
        ],
    }
    return {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {"count": WORLD_COUNT, "recipe": anymal_sub}},
            {"op": "set_default_shape_cfg", "args": {"ke": 1.0e3, "kd": 1.0e2}},
            {"op": "add_ground_plane"},
        ],
    }


def _build_reference_in_process(asset_file: str) -> tuple[np.ndarray, np.ndarray]:
    from newton import JointTargetMode

    with wp.ScopedDevice(DEVICE):
        sub = newton.ModelBuilder()
        newton.solvers.SolverMuJoCo.register_custom_attributes(sub)
        sub.default_joint_cfg.limit_ke = 1.0e3
        sub.default_joint_cfg.limit_kd = 1.0e1
        sub.default_joint_cfg.friction = 1e-5
        sub.default_shape_cfg.ke = 2.0e3
        sub.default_shape_cfg.kd = 1.0e2
        sub.default_shape_cfg.kf = 1.0e3
        sub.default_shape_cfg.mu = 0.75
        sub.add_usd(
            asset_file,
            collapse_fixed_joints=False,
            enable_self_collisions=False,
            hide_collision_shapes=True,
        )
        sub.joint_q[0:3] = [0.0, 0.0, 0.62]
        sub.joint_q[3:7] = [0.0, 0.0, 0.0, 1.0]
        for i in range(len(sub.joint_target_ke)):
            sub.joint_target_ke[i] = 150.0
            sub.joint_target_kd[i] = 5.0
            sub.joint_target_mode[i] = int(JointTargetMode.POSITION)

        builder = newton.ModelBuilder()
        builder.replicate(sub, WORLD_COUNT)
        builder.default_shape_cfg.ke = 1.0e3
        builder.default_shape_cfg.kd = 1.0e2
        builder.add_ground_plane()

        model = builder.finalize()
        state = run_simulation(
            model,
            solver_name="SolverMuJoCo",
            num_frames=50,  # keep test fast; anymal_d on CUDA nominally uses 500
            fps=50.0,
            substeps=4,
        )
        return state.body_q.numpy().copy(), state.body_qd.numpy().copy()


class TestRobotAnymalD(unittest.TestCase):
    def test_anymal_d_via_cli_matches_in_process_reference(self):
        asset_file = _resolve_asset()
        recipe = _build_recipe(asset_file)
        ref_body_q, ref_body_qd = _build_reference_in_process(asset_file)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "anymal_recipe.json"
            model_path = tdp / "anymal.model.json"
            state_path = tdp / "anymal_final.npz"
            recipe_path.write_text(json.dumps(recipe))

            run_cli(
                "model", "build",
                "--recipe", str(recipe_path),
                "--out", str(model_path),
                "--device", DEVICE,
                "--json",
                check=True,
            )
            run_cli(
                "sim", "run",
                "--model", str(model_path),
                "--solver", "SolverMuJoCo",
                "--num-frames", "50",
                "--fps", "50",
                "--substeps", "4",
                "--device", DEVICE,
                "--out", str(state_path),
                "--json",
                check=True,
            )

            with np.load(state_path) as data:
                cli_body_q = data["body_q"].copy()
                cli_body_qd = data["body_qd"].copy()

        self.assertTrue(np.all(np.isfinite(cli_body_q)))
        self.assertTrue(np.all(np.isfinite(cli_body_qd)))

        # MuJoCo on CUDA is not bit-deterministic across subprocess boundaries
        # (kernel launch ordering + JIT cache variance). Allow a small slack
        # on velocities; positions should still match within 1e-4.
        np.testing.assert_allclose(cli_body_q, ref_body_q, atol=1e-4,
            err_msg="CLI body_q diverges from in-process reference")
        np.testing.assert_allclose(cli_body_qd, ref_body_qd, atol=1e-3,
            err_msg="CLI body_qd diverges from in-process reference")

        # Sanity: robot didn't fall through floor
        for i in range(cli_body_q.shape[0]):
            self.assertGreater(float(cli_body_q[i, 2]), -0.5,
                f"body {i} fell through ground (z={cli_body_q[i, 2]})")


if __name__ == "__main__":
    unittest.main()
