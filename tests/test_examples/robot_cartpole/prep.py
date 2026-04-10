"""Generate robot_cartpole recipe with resolved cartpole.usda path."""

from __future__ import annotations

import json
from pathlib import Path

import newton.examples

HERE = Path(__file__).parent
WORLD_COUNT = 4


def main() -> None:
    usd_path = str(newton.examples.get_asset("cartpole.usda"))

    cartpole_sub = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "register_mujoco_custom_attributes"},
            {"op": "set_default_shape_cfg", "args": {"density": 100.0}},
            {"op": "set_default_joint_cfg", "args": {"armature": 0.1}},
            {"op": "add_usd", "args": {
                "source": usd_path,
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
    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {
                "count": WORLD_COUNT,
                "recipe": cartpole_sub,
                "spacing": [1.0, 2.0, 0.0],
            }},
        ],
    }

    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe, indent=2))
    print(f"wrote {out}")
    print(f"usd: {usd_path}")


if __name__ == "__main__":
    main()
