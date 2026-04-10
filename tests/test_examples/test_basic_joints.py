"""Wave B.1 — basic_joints reproduced via newton-cli.

Brings new recipe surface:
  - {"$shape_cfg": {"density": 0.0}} tag for inline ShapeConfig kwargs
  - set_builder_array op for joint_q[-1] = pi/2 and joint_q[-4:] = quat_rpy(...)
"""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import newton
import newton.examples
import warp as wp

from newton_cli.recipes import build_model_from_recipe
from newton_cli.state_io import load_state_npz_into
from tests._cli import run_cli

CUBOID_HX = 0.1
CUBOID_HY = 0.1
CUBOID_HZ = 0.75
UPPER_HZ = 0.25 * CUBOID_HZ
DROP_Z = 2.0
ROWS = [-3.0, 0.0, 3.0]

# Pre-compute the rpy quaternion that the example uses for the ball joint init.
_ball_quat = wp.quat_rpy(0.5, 0.6, 0.7)
BALL_QUAT_XYZW = [float(_ball_quat[0]), float(_ball_quat[1]), float(_ball_quat[2]), float(_ball_quat[3])]


def _xform(p, axis=None, angle=0.0):
    q = {"axis": list(axis), "angle": angle} if axis else [0.0, 0.0, 0.0, 1.0]
    return {"p": list(p), "q": q}


JOINTS_RECIPE = {
    "schema": "newton-cli/recipe/v1",
    "ops": [
        {"op": "add_ground_plane"},

        # ===== REVOLUTE row (y=-3) =====
        # body 0: a_rev (upper)
        {"op": "add_link", "args": {"xform": _xform([0.0, ROWS[0], DROP_Z + UPPER_HZ])}},
        # body 1: b_rev (lower)
        {"op": "add_link", "args": {
            "xform": _xform([0.0, ROWS[0], DROP_Z - CUBOID_HZ], axis=[1.0, 0.0, 0.0], angle=0.15),
            "label": "b_rev",
        }},
        {"op": "add_shape_box", "args": {"body": 0, "hx": CUBOID_HX, "hy": CUBOID_HY, "hz": UPPER_HZ}},
        {"op": "add_shape_box", "args": {"body": 1, "hx": CUBOID_HX, "hy": CUBOID_HY, "hz": CUBOID_HZ}},
        # joint 0: fixed anchor for revolute
        {"op": "add_joint_fixed", "args": {
            "parent": -1, "child": 0,
            "parent_xform": _xform([0.0, ROWS[0], DROP_Z + UPPER_HZ]),
            "child_xform": _xform([0.0, 0.0, 0.0]),
            "label": "fixed_revolute_anchor",
        }},
        # joint 1: revolute a→b
        {"op": "add_joint_revolute", "args": {
            "parent": 0, "child": 1,
            "axis": [1.0, 0.0, 0.0],
            "parent_xform": _xform([0.0, 0.0, -UPPER_HZ]),
            "child_xform": _xform([0.0, 0.0, +CUBOID_HZ]),
            "label": "revolute_a_b",
        }},
        {"op": "add_articulation", "args": {"joints": [0, 1], "label": "revolute_articulation"}},
        # joint_q[-1] = pi/2  (initial revolute angle)
        {"op": "set_builder_array", "args": {"name": "joint_q", "index": -1, "value": math.pi * 0.5}},

        # ===== PRISMATIC row (y=0) =====
        # body 2: a_pri (upper)
        {"op": "add_link", "args": {"xform": _xform([0.0, ROWS[1], DROP_Z + UPPER_HZ])}},
        # body 3: b_pri (lower)
        {"op": "add_link", "args": {
            "xform": _xform([0.0, ROWS[1], DROP_Z - CUBOID_HZ], axis=[0.0, 1.0, 0.0], angle=0.12),
            "label": "b_prismatic",
        }},
        {"op": "add_shape_box", "args": {"body": 2, "hx": CUBOID_HX, "hy": CUBOID_HY, "hz": UPPER_HZ}},
        {"op": "add_shape_box", "args": {"body": 3, "hx": CUBOID_HX, "hy": CUBOID_HY, "hz": CUBOID_HZ}},
        # joint 2: fixed anchor for prismatic
        {"op": "add_joint_fixed", "args": {
            "parent": -1, "child": 2,
            "parent_xform": _xform([0.0, ROWS[1], DROP_Z + UPPER_HZ]),
            "child_xform": _xform([0.0, 0.0, 0.0]),
            "label": "fixed_prismatic_anchor",
        }},
        # joint 3: prismatic
        {"op": "add_joint_prismatic", "args": {
            "parent": 2, "child": 3,
            "axis": [0.0, 0.0, 1.0],
            "parent_xform": _xform([0.0, 0.0, -UPPER_HZ]),
            "child_xform": _xform([0.0, 0.0, +CUBOID_HZ]),
            "limit_lower": -0.3,
            "limit_upper": 0.3,
            "label": "prismatic_a_b",
        }},
        {"op": "add_articulation", "args": {"joints": [2, 3], "label": "prismatic_articulation"}},

        # ===== BALL row (y=+3) =====
        # body 4: a_ball (anchor)
        {"op": "add_link", "args": {"xform": _xform([0.0, ROWS[2], DROP_Z + 0.3 + CUBOID_HZ - 1.0])}},
        # body 5: b_ball
        {"op": "add_link", "args": {
            "xform": _xform([0.0, ROWS[2], DROP_Z + 0.3 - 1.0], axis=[1.0, 1.0, 0.0], angle=0.1),
            "label": "b_ball",
        }},
        # massless sphere on a_ball
        {"op": "add_shape_sphere", "args": {
            "body": 4,
            "radius": 0.3,
            "cfg": {"$shape_cfg": {"density": 0.0}},
        }},
        {"op": "add_shape_box", "args": {"body": 5, "hx": CUBOID_HX, "hy": CUBOID_HY, "hz": CUBOID_HZ}},
        # joint 4: fixed anchor for ball
        {"op": "add_joint_fixed", "args": {
            "parent": -1, "child": 4,
            "parent_xform": _xform([0.0, ROWS[2], DROP_Z + 0.3 + CUBOID_HZ - 1.0]),
            "child_xform": _xform([0.0, 0.0, 0.0]),
            "label": "fixed_ball_anchor",
        }},
        # joint 5: ball
        {"op": "add_joint_ball", "args": {
            "parent": 4, "child": 5,
            "parent_xform": _xform([0.0, 0.0, 0.0]),
            "child_xform": _xform([0.0, 0.0, +CUBOID_HZ]),
            "label": "ball_a_b",
        }},
        {"op": "add_articulation", "args": {"joints": [4, 5], "label": "ball_articulation"}},
        # joint_q[-4:] = quat_rpy(0.5, 0.6, 0.7)
        {"op": "set_builder_array", "args": {
            "name": "joint_q",
            "slice": [-4, None],
            "values": BALL_QUAT_XYZW,
        }},

        {"op": "color"},
    ],
}


class TestBasicJoints(unittest.TestCase):
    def test_joints_via_cli_passes_native_validation(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "joints_recipe.json"
            model_path = tdp / "joints.model.json"
            state_path = tdp / "joints_final.npz"
            recipe_path.write_text(json.dumps(JOINTS_RECIPE))

            run_cli(
                "model", "build",
                "--recipe", str(recipe_path),
                "--out", str(model_path),
                "--json",
                check=True,
            )

            # Default solver, default iterations. The example uses XPBD with no
            # special args. Run for 300 frames so the static bodies fully settle.
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

            model = build_model_from_recipe(model_path, device="cpu")
            state = model.state()
            load_state_into = load_state_npz_into  # alias for clarity
            load_state_into(state, state_path)

            # ----- example test_final predicates verbatim -----
            newton.examples.test_body_state(
                model, state,
                "static bodies are not moving",
                lambda q, qd: max(abs(qd)) == 0.0,
                indices=[2, 4],
            )
            newton.examples.test_body_state(
                model, state,
                "fixed link body has come to a rest",
                lambda q, qd: max(abs(qd)) < 1e-2,
                indices=[0],
            )
            newton.examples.test_body_state(
                model, state,
                "slider link body has come to a rest",
                lambda q, qd: max(abs(qd)) < 1e-5,
                indices=[3],
            )
            newton.examples.test_body_state(
                model, state,
                "movable links are not moving too fast",
                lambda q, qd: max(abs(qd)) < 3.0,
                indices=[1, 5],
            )


if __name__ == "__main__":
    unittest.main()
