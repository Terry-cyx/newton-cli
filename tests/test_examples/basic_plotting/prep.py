"""Generate basic_plotting recipe with nv_humanoid.xml MJCF path resolved."""

from __future__ import annotations

import json
from pathlib import Path

import newton.examples

HERE = Path(__file__).parent
WORLD_COUNT = 4


def main() -> None:
    mjcf_path = str(newton.examples.get_asset("nv_humanoid.xml"))

    humanoid_sub = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "register_mujoco_custom_attributes"},
            {"op": "add_mjcf", "args": {
                "source": mjcf_path,
                "ignore_names": ["floor", "ground"],
                "xform": {"p": [0.0, 0.0, 1.5], "q": [0.0, 0.0, 0.0, 1.0]},
            }},
        ],
    }
    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "replicate", "args": {"count": WORLD_COUNT, "recipe": humanoid_sub}},
            {"op": "add_ground_plane"},
        ],
    }
    (HERE / "recipe.json").write_text(json.dumps(recipe, indent=2))
    print(f"wrote recipe.json")
    print(f"mjcf: {mjcf_path}")


if __name__ == "__main__":
    main()
