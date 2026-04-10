"""Generate cloth_bending recipe by extracting mesh vertices+indices from the
`curvedSurface.usd` asset and baking them directly into the recipe JSON.

The upstream example does:
    usd_stage = Usd.Stage.Open(newton.examples.get_asset("curvedSurface.usd"))
    mesh = newton.usd.get_mesh(usd_stage.GetPrimAtPath("/root/cloth"))
    builder.add_cloth_mesh(vertices=mesh.vertices, indices=mesh.indices, ...)

We move the USD load into prep so the recipe is self-contained JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import newton.examples
import newton.usd
from pxr import Usd

HERE = Path(__file__).parent


def main() -> None:
    usd_path = str(newton.examples.get_asset("curvedSurface.usd"))
    stage = Usd.Stage.Open(usd_path)
    prim = stage.GetPrimAtPath("/root/cloth")
    mesh = newton.usd.get_mesh(prim)

    # Extract raw geometry and convert to plain Python lists for JSON.
    vertices = [[float(v[0]), float(v[1]), float(v[2])] for v in mesh.vertices]
    indices = [int(i) for i in mesh.indices]
    print(f"curvedSurface.usd /root/cloth: {len(vertices)} verts, {len(indices) // 3} tris")

    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "set_default_shape_cfg", "args": {
                "ke": 100.0, "kd": 1.0, "mu": 1.5,
            }},
            {"op": "add_cloth_mesh", "args": {
                "pos": [0.0, 0.0, 10.0],
                "rot": {"axis": [1.0, 0.0, 0.0], "angle": 0.5235987755982988},
                "scale": 1.0,
                "vertices": vertices,
                "indices": indices,
                "vel": [0.0, 0.0, 0.0],
                "density": 0.02,
                "tri_ke": 50.0,
                "tri_ka": 50.0,
                "tri_kd": 0.1,
                "edge_ke": 10.0,
                "edge_kd": 1.0,
            }},
            {"op": "color", "args": {"include_bending": True}},
            {"op": "add_ground_plane"},
        ],
        "post_finalize": {
            "soft_contact_ke": 100.0,
            "soft_contact_kd": 1.0,
            "soft_contact_mu": 1.5,
        },
    }

    (HERE / "recipe.json").write_text(json.dumps(recipe))
    print(f"wrote recipe.json (cloth_bending)")


if __name__ == "__main__":
    main()
