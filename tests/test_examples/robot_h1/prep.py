"""Generate robot_h1 recipe with downloaded USD path."""

from __future__ import annotations

import json
from pathlib import Path

import newton.utils

HERE = Path(__file__).parent
WORLD_COUNT = 2


def main() -> None:
    asset_dir = Path(newton.utils.download_asset("unitree_h1"))
    usd_path = str(asset_dir / "usd_structured" / "h1.usda")

    h1_sub = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "register_mujoco_custom_attributes"},
            {"op": "set_default_joint_cfg", "args": {
                "limit_ke": 1.0e3, "limit_kd": 1.0e1, "friction": 1e-5,
            }},
            {"op": "set_default_shape_cfg", "args": {
                "ke": 2.0e3, "kd": 1.0e2, "kf": 1.0e3, "mu": 0.75,
            }},
            {"op": "add_usd", "args": {
                "source": usd_path,
                "ignore_paths": ["/GroundPlane"],
                "enable_self_collisions": False,
            }},
            {"op": "set_builder_array", "args": {"name": "joint_target_ke", "fill": 150.0}},
            {"op": "set_builder_array", "args": {"name": "joint_target_kd", "fill": 5.0}},
            {"op": "set_builder_array", "args": {"name": "joint_target_mode", "fill": 1}},
        ],
    }
    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {"count": WORLD_COUNT, "recipe": h1_sub}},
            {"op": "set_default_shape_cfg", "args": {"ke": 1.0e3, "kd": 1.0e2}},
            {"op": "add_ground_plane"},
        ],
    }

    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe, indent=2))
    print(f"wrote {out}")
    print(f"usd: {usd_path}")


if __name__ == "__main__":
    main()
