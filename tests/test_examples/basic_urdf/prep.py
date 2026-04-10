"""Generate basic_urdf recipe with resolved URDF path.

The quadruped.urdf is a Newton example asset; we resolve its absolute path
via newton.examples.get_asset() and bake it into the recipe.
"""

from __future__ import annotations

import json
from pathlib import Path

import newton.examples

HERE = Path(__file__).parent
WORLD_COUNT = 4
INITIAL_LEG_POSE = [0.2, 0.4, -0.6, -0.2, -0.4, 0.6, -0.2, 0.4, -0.6, 0.2, -0.4, 0.6]


def main() -> None:
    urdf_path = str(newton.examples.get_asset("quadruped.urdf"))

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
                "source": urdf_path,
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
    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {"count": WORLD_COUNT, "recipe": quadruped_sub}},
            {"op": "add_ground_plane", "args": {
                "cfg": {"$shape_cfg": {"mu": 1.0}},
            }},
        ],
    }

    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe, indent=2))
    print(f"wrote {out}")
    print(f"urdf: {urdf_path}")


if __name__ == "__main__":
    main()
