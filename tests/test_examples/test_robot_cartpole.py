"""Wave D.2 — robot_cartpole reproduced via newton-cli.

Brings:
  - add_usd recipe op (pure method dispatch via newton[importers])
  - newton[sim] extra (for SolverMuJoCo)
  - register_mujoco_custom_attributes special op (wraps
    SolverMuJoCo.register_custom_attributes(builder))

Like Wave B.3 basic_urdf, we use NUMERICAL EQUIVALENCE against an
in-process reference as the pass bar, because the example's test_final
uses exact-equality predicates (e.g. `q[2] == 0.0`) that depend on
contact-free MuJoCo integrator behavior. If our CLI matches the
in-process reference byte-for-byte, those predicates either both pass or
both fail — either way the CLI is faithful.
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
USD_PATH = newton.examples.get_asset("cartpole.usda")


def _build_recipe() -> dict:
    cartpole_sub = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "register_mujoco_custom_attributes"},
            {"op": "set_default_shape_cfg", "args": {"density": 100.0}},
            {"op": "set_default_joint_cfg", "args": {"armature": 0.1}},
            {"op": "add_usd", "args": {
                "source": str(USD_PATH),
                "enable_self_collisions": False,
                "collapse_fixed_joints": True,
            }},
            {"op": "apply_body_inertia_diagonal", "args": {"value": 0.1}},
            {"op": "set_builder_array", "args": {
                "name": "joint_q",
                "slice": [-3, None],
                "values": [0.0, 0.3, 0.0],
            }},
        ],
    }
    return {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {
                "count": WORLD_COUNT,
                "recipe": cartpole_sub,
                "spacing": [1.0, 2.0, 0.0],
            }},
        ],
    }


def _build_reference_in_process(device: str) -> tuple[np.ndarray, np.ndarray]:
    with wp.ScopedDevice(device):
        cartpole = newton.ModelBuilder()
        newton.solvers.SolverMuJoCo.register_custom_attributes(cartpole)
        cartpole.default_shape_cfg.density = 100.0
        cartpole.default_joint_cfg.armature = 0.1
        cartpole.add_usd(
            str(USD_PATH),
            enable_self_collisions=False,
            collapse_fixed_joints=True,
        )
        body_armature = 0.1
        for body in range(cartpole.body_count):
            inertia_np = np.asarray(cartpole.body_inertia[body], dtype=np.float32).reshape(3, 3)
            inertia_np += np.eye(3, dtype=np.float32) * body_armature
            cartpole.body_inertia[body] = wp.mat33(inertia_np)
        cartpole.joint_q[-3:] = [0.0, 0.3, 0.0]

        builder = newton.ModelBuilder()
        builder.replicate(cartpole, WORLD_COUNT, spacing=(1.0, 2.0, 0.0))
        model = builder.finalize()

        state = run_simulation(
            model,
            solver_name="SolverMuJoCo",
            num_frames=100,
            fps=60.0,
            substeps=10,
        )
        return state.body_q.numpy().copy(), state.body_qd.numpy().copy()


class TestRobotCartpole(unittest.TestCase):
    def test_cartpole_via_cli_matches_in_process_reference(self):
        recipe = _build_recipe()
        # MuJoCo solver requires CUDA, run on cuda:0
        device = "cuda:0"
        ref_body_q, ref_body_qd = _build_reference_in_process(device=device)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "cartpole_recipe.json"
            model_path = tdp / "cartpole.model.json"
            state_path = tdp / "cartpole_final.npz"
            recipe_path.write_text(json.dumps(recipe))

            run_cli(
                "model", "build",
                "--recipe", str(recipe_path),
                "--out", str(model_path),
                "--device", device,
                "--json",
                check=True,
            )
            run_cli(
                "sim", "run",
                "--model", str(model_path),
                "--solver", "SolverMuJoCo",
                "--num-frames", "100",
                "--fps", "60",
                "--substeps", "10",
                "--device", device,
                "--out", str(state_path),
                "--json",
                check=True,
            )

            with np.load(state_path) as data:
                cli_body_q = data["body_q"].copy()
                cli_body_qd = data["body_qd"].copy()

        # Sanity: not exploded / not NaN
        self.assertTrue(np.all(np.isfinite(cli_body_q)))
        self.assertTrue(np.all(np.isfinite(cli_body_qd)))

        np.testing.assert_allclose(cli_body_q, ref_body_q, atol=1e-4,
            err_msg="CLI body_q diverges from in-process reference")
        np.testing.assert_allclose(cli_body_qd, ref_body_qd, atol=1e-4,
            err_msg="CLI body_qd diverges from in-process reference")


if __name__ == "__main__":
    unittest.main()
