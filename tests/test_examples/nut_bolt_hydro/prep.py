"""Generate nut_bolt_hydro recipe by downloading IsaacGymEnvs assets and
baking the bolt + nut mesh vertices/indices into recipe.json.

The expensive bit (mesh.build_sdf) happens at *recipe execution* time inside
the $mesh tag handler — at prep time we only download + recenter + dump.

To keep the test fast we use ONE assembly and a coarser SDF resolution
than the example default (64 vs 256).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

import newton.examples

HERE = Path(__file__).parent

ASSEMBLY_STR = "m20_loose"
ISAACGYM_ENVS_REPO_URL = "https://github.com/isaac-sim/IsaacGymEnvs.git"
ISAACGYM_NUT_BOLT_FOLDER = "assets/factory/mesh/factory_nut_bolt"

SDF_MAX_RESOLUTION = 64
SDF_NARROW_BAND_RANGE = [-0.005, 0.005]
SDF_MARGIN = 0.005

GROUND_OFFSET = -0.01


def load_and_recenter(mesh_file: str):
    md = trimesh.load(mesh_file, force="mesh")
    verts = np.asarray(md.vertices, dtype=np.float32)
    inds = np.asarray(md.faces.flatten(), dtype=np.int32)
    lo = verts.min(axis=0)
    hi = verts.max(axis=0)
    center = (lo + hi) / 2.0
    verts -= center
    return verts, inds, center.astype(np.float32)


def main():
    print("Downloading IsaacGymEnvs nut/bolt assets...")
    asset_path = newton.examples.download_external_git_folder(
        ISAACGYM_ENVS_REPO_URL, ISAACGYM_NUT_BOLT_FOLDER
    )
    print(f"  -> {asset_path}")

    bolt_obj = str(asset_path / f"factory_bolt_{ASSEMBLY_STR}.obj")
    nut_obj = str(asset_path / f"factory_nut_{ASSEMBLY_STR}_subdiv_3x.obj")

    bolt_v, bolt_i, bolt_c = load_and_recenter(bolt_obj)
    nut_v, nut_i, nut_c = load_and_recenter(nut_obj)
    print(f"bolt: {bolt_v.shape[0]} verts, {bolt_i.shape[0]//3} tris, center={bolt_c}")
    print(f"nut:  {nut_v.shape[0]} verts, {nut_i.shape[0]//3} tris, center={nut_c}")

    # Body transforms with center offsets pre-applied (no rotation -> just add).
    bolt_pos = [float(bolt_c[0]) + 0.0, float(bolt_c[1]) + 0.0, float(bolt_c[2]) + 0.0]
    # Nut at z = 0.041 with a small Z-axis rotation (pi/8) for thread alignment.
    import math

    nut_yaw = math.pi / 8
    half = nut_yaw * 0.5
    nut_q = [0.0, 0.0, math.sin(half), math.cos(half)]
    # quat_rotate of nut center under nut_q (Z-axis rotation):
    cz = math.cos(nut_yaw)
    sz = math.sin(nut_yaw)
    cx, cy, c2 = float(nut_c[0]), float(nut_c[1]), float(nut_c[2])
    rotated_center = [cx * cz - cy * sz, cx * sz + cy * cz, c2]
    nut_pos = [rotated_center[0], rotated_center[1], 0.041 + rotated_center[2]]

    shape_cfg_common = {
        "$shape_cfg": {
            "margin": 0.0,
            "mu": 0.01,
            "ke": 1.0e7,
            "kd": 1.0e4,
            "gap": 0.005,
            "density": 8000.0,
            "mu_torsional": 0.0,
            "mu_rolling": 0.0,
            "is_hydroelastic": True,
        }
    }

    bolt_mesh_tag = {"$mesh": {
        "vertices": bolt_v.tolist(),
        "indices": bolt_i.tolist(),
        "build_sdf": {
            "max_resolution": SDF_MAX_RESOLUTION,
            "narrow_band_range": SDF_NARROW_BAND_RANGE,
            "margin": SDF_MARGIN,
        },
    }}
    nut_mesh_tag = {"$mesh": {
        "vertices": nut_v.tolist(),
        "indices": nut_i.tolist(),
        "build_sdf": {
            "max_resolution": SDF_MAX_RESOLUTION,
            "narrow_band_range": SDF_NARROW_BAND_RANGE,
            "margin": SDF_MARGIN,
        },
    }}

    ops = [
        {"op": "set_default_shape_cfg", "args": {"gap": 0.001}},
        {"op": "add_shape_plane", "args": {
            "plane": [0.0, 0.0, 1.0, -GROUND_OFFSET],
            "width": 0.0,
            "length": 0.0,
            "body": -1,
            "label": "ground_plane",
        }},
        # Bolt body (index 0) + its shape
        {"op": "add_body", "args": {
            "label": "bolt_0",
            "xform": {"p": bolt_pos, "q": [0.0, 0.0, 0.0, 1.0]},
        }},
        {"op": "add_shape_mesh", "args": {
            "body": 0,
            "mesh": bolt_mesh_tag,
            "scale": [1.0, 1.0, 1.0],
            "cfg": shape_cfg_common,
        }},
        # Nut body (index 1) + its shape
        {"op": "add_body", "args": {
            "label": "nut_0",
            "xform": {"p": nut_pos, "q": nut_q},
        }},
        {"op": "add_shape_mesh", "args": {
            "body": 1,
            "mesh": nut_mesh_tag,
            "scale": [1.0, 1.0, 1.0],
            "cfg": shape_cfg_common,
        }},
    ]

    recipe = {"schema": "newton-cli/recipe/v1", "ops": ops}
    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe))
    print(f"wrote {out}: {len(ops)} ops, {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()
