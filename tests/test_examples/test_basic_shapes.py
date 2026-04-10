"""Wave A.2 — basic_shapes reproduced via newton-cli.

This example exercises every primitive shape (sphere, ellipsoid, capsule,
cylinder, box, cone) plus a USD-loaded mesh (the bunny). The mesh body is
DEFERRED to Wave B (importers) because it requires `pxr.Usd` and the
`importers` extra; this test exercises everything else and validates the
example's exact rest-pose predicates against the 5 testable bodies.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import newton
import newton.examples
import newton.math
import warp as wp

from newton_cli.recipes import build_model_from_recipe
from newton_cli.state_io import load_state_npz_into
from tests._cli import run_cli

DROP_Z = 2.0

# Body order matches example_basic_shapes.py minus the bunny mesh.
SHAPES_RECIPE = {
    "schema": "newton-cli/recipe/v1",
    "ops": [
        {"op": "add_ground_plane"},
        # 0 sphere
        {"op": "add_body", "args": {
            "xform": {"p": [0.0, -2.0, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            "label": "sphere",
        }},
        {"op": "add_shape_sphere", "args": {"body": 0, "radius": 0.5}},
        # 1 ellipsoid
        {"op": "add_body", "args": {
            "xform": {"p": [0.0, -6.0, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            "label": "ellipsoid",
        }},
        {"op": "add_shape_ellipsoid", "args": {"body": 1, "rx": 0.5, "ry": 0.5, "rz": 0.25}},
        # 2 capsule
        {"op": "add_body", "args": {
            "xform": {"p": [0.0, 0.0, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            "label": "capsule",
        }},
        {"op": "add_shape_capsule", "args": {"body": 2, "radius": 0.3, "half_height": 0.7}},
        # 3 cylinder
        {"op": "add_body", "args": {
            "xform": {"p": [0.0, -4.0, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            "label": "cylinder",
        }},
        {"op": "add_shape_cylinder", "args": {"body": 3, "radius": 0.4, "half_height": 0.6}},
        # 4 box
        {"op": "add_body", "args": {
            "xform": {"p": [0.0, 2.0, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            "label": "box",
        }},
        {"op": "add_shape_box", "args": {"body": 4, "hx": 0.5, "hy": 0.35, "hz": 0.25}},
        # 5 cone (no collision in standard pipeline; not validated, but kept for parity)
        {"op": "add_body", "args": {
            "xform": {"p": [0.0, 6.0, DROP_Z], "q": [0.0, 0.0, 0.0, 1.0]},
            "label": "cone",
        }},
        {"op": "add_shape_cone", "args": {"body": 5, "radius": 0.45, "half_height": 0.6}},
    ],
}


class TestBasicShapes(unittest.TestCase):
    def test_shapes_via_cli_passes_native_validation(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            recipe_path = tdp / "shapes_recipe.json"
            model_path = tdp / "shapes.model.json"
            state_path = tdp / "shapes_final.npz"
            recipe_path.write_text(json.dumps(SHAPES_RECIPE))

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
                "--num-frames", "300",
                "--fps", "100",
                "--substeps", "10",
                "--device", "cpu",
                "--out", str(state_path),
                "--json",
                check=True,
            )

            model = build_model_from_recipe(model_path, device="cpu")
            state = model.state()
            load_state_npz_into(state, state_path)

            # ----- example predicates, copied verbatim, body indices unchanged -----
            sphere_q = wp.transform(wp.vec3(0.0, -2.0, 0.5), wp.quat_identity())
            newton.examples.test_body_state(
                model, state, "sphere at rest pose",
                lambda q, qd: newton.math.vec_allclose(q, sphere_q, atol=2e-4),
                [0],
            )

            ellipsoid_q = wp.transform(wp.vec3(0.0, -6.0, 0.25), wp.quat_identity())
            newton.examples.test_body_state(
                model, state, "ellipsoid at rest pose",
                lambda q, qd: newton.math.vec_allclose(q, ellipsoid_q, atol=2e-2),
                [1],
            )

            capsule_q = wp.transform(wp.vec3(0.0, 0.0, 1.0), wp.quat_identity())
            newton.examples.test_body_state(
                model, state, "capsule at rest pose",
                lambda q, qd: newton.math.vec_allclose(q, capsule_q, atol=2e-4),
                [2],
            )

            cylinder_q = wp.transform(wp.vec3(0.0, -4.0, 0.6), wp.quat_identity())
            newton.examples.test_body_state(
                model, state, "cylinder at rest pose",
                lambda q, qd: abs(q[0] - cylinder_q[0]) < 0.01
                and abs(q[1] - cylinder_q[1]) < 0.01
                and abs(q[2] - cylinder_q[2]) < 1e-4
                and abs(q[3] - cylinder_q[3]) < 1e-4
                and abs(q[4] - cylinder_q[4]) < 1e-4
                and abs(q[5] - cylinder_q[5]) < 1e-4
                and abs(q[6] - cylinder_q[6]) < 1e-4,
                [3],
            )

            box_q = wp.transform(wp.vec3(0.0, 2.0, 0.25), wp.quat_identity())
            newton.examples.test_body_state(
                model, state, "box at rest pose",
                lambda q, qd: newton.math.vec_allclose(q, box_q, atol=0.1),
                [4],
            )


if __name__ == "__main__":
    unittest.main()
