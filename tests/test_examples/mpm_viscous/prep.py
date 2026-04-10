"""Generate mpm_viscous recipe with pre-computed funnel mesh + cone-filtered particles.

Mirrors example_mpm_viscous.py: a thick-walled funnel mesh collider holding a
viscous-fluid particle blob that flows through the bottom aperture under
gravity. We bake the funnel geometry and the cone-filtered particle positions
into the recipe so the CLI build step stays self-contained.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# scene parameters (mirror example defaults except a coarser voxel for speed)
# ---------------------------------------------------------------------------
FUNNEL_APERTURE = 0.02
FUNNEL_TOP_RADIUS = 0.05
FUNNEL_HEIGHT = 0.2
FUNNEL_OFFSET_Z = 0.2
FUNNEL_THICKNESS = 0.005
FUNNEL_SEGMENTS = 64
FUNNEL_FRICTION = 0.0
GROUND_FRICTION = 0.5

DENSITY = 1000.0
VISCOSITY = 50.0
TENSILE_YIELD_RATIO = 1.0
FRICTION = 0.0

# Coarser than the example's 0.005 — the test only needs to verify that
# particles fall + drain, and the example's default takes too long to
# CPU-build the particle list.
VOXEL_SIZE = 0.01
GRAVITY = [0.0, 0.0, -10.0]


def create_funnel_mesh(aperture_radius, top_radius, height, z_offset, thickness, num_segments):
    theta = np.linspace(0.0, 2.0 * np.pi, num_segments, endpoint=False)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    n = num_segments

    def ring(radius, z):
        return np.column_stack([radius * cos_t, radius * sin_t, np.full(n, z)])

    vertices = np.vstack(
        [
            ring(aperture_radius, z_offset),
            ring(top_radius, z_offset + height),
            ring(top_radius + thickness, z_offset + height),
            ring(aperture_radius + thickness, z_offset),
        ]
    ).astype(np.float32)

    indices = []
    for i in range(n):
        j = (i + 1) % n
        r0_i, r0_j = i, j
        r1_i, r1_j = i + n, j + n
        r2_i, r2_j = i + 2 * n, j + 2 * n
        r3_i, r3_j = i + 3 * n, j + 3 * n

        indices.extend([r0_i, r1_i, r0_j])
        indices.extend([r0_j, r1_i, r1_j])
        indices.extend([r3_i, r3_j, r2_i])
        indices.extend([r2_i, r3_j, r2_j])
        indices.extend([r1_i, r2_i, r1_j])
        indices.extend([r1_j, r2_i, r2_j])
        indices.extend([r3_i, r0_i, r3_j])
        indices.extend([r3_j, r0_i, r0_j])

    return vertices, np.array(indices, dtype=np.int32)


def emit_particles(voxel_size, density,
                   aperture_radius, top_radius, height, z_offset):
    particles_per_cell = 3.0
    particle_lo = np.array([-top_radius, -top_radius, z_offset])
    particle_hi = np.array([top_radius, top_radius, z_offset + height])
    particle_res = np.array(
        np.ceil(particles_per_cell * (particle_hi - particle_lo) / voxel_size),
        dtype=int,
    )
    cell_size = (particle_hi - particle_lo) / particle_res
    cell_volume = float(np.prod(cell_size))
    radius = float(np.max(cell_size) * 0.5)
    mass = cell_volume * density

    dim_x = particle_res[0] + 1
    dim_y = particle_res[1] + 1
    dim_z = particle_res[2] + 1

    px = np.arange(dim_x) * cell_size[0]
    py = np.arange(dim_y) * cell_size[1]
    pz = np.arange(dim_z) * cell_size[2]
    points = np.stack(np.meshgrid(px, py, pz)).reshape(3, -1).T

    jitter = 2.0 * float(np.max(cell_size))
    rng = np.random.default_rng(422)
    points += (rng.random(points.shape) - 0.5) * jitter
    points += particle_lo

    margin = voxel_size
    z_frac = np.clip((points[:, 2] - z_offset) / height, 0.0, 1.0)
    r_max = aperture_radius + z_frac * (top_radius - aperture_radius) - margin
    r_xy = np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)
    inside = (
        (r_xy < r_max)
        & (points[:, 2] > z_offset + margin)
        & (points[:, 2] < z_offset + height - margin)
    )
    return points[inside].astype(np.float32), mass, radius


def main():
    verts, inds = create_funnel_mesh(
        aperture_radius=FUNNEL_APERTURE / 2.0,
        top_radius=FUNNEL_TOP_RADIUS,
        height=FUNNEL_HEIGHT,
        z_offset=FUNNEL_OFFSET_Z,
        thickness=FUNNEL_THICKNESS,
        num_segments=FUNNEL_SEGMENTS,
    )
    points, mass, radius = emit_particles(
        voxel_size=VOXEL_SIZE,
        density=DENSITY,
        aperture_radius=FUNNEL_APERTURE / 2.0,
        top_radius=FUNNEL_TOP_RADIUS,
        height=FUNNEL_HEIGHT,
        z_offset=FUNNEL_OFFSET_Z,
    )
    n_particles = int(points.shape[0])

    print(f"funnel: {verts.shape[0]} verts, {inds.shape[0] // 3} tris")
    print(f"particles: {n_particles}, mass={mass:.3e}, radius={radius:.4f}")

    recipe = {
        "schema": "newton-cli/recipe/v1",
        "ops": [
            {"op": "register_solver_custom_attributes",
             "args": {"solver": "SolverImplicitMPM"}},
            {"op": "add_shape_mesh", "args": {
                "body": -1,
                "cfg": {"$shape_cfg": {"mu": FUNNEL_FRICTION}},
                "mesh": {"$mesh": {
                    "vertices": verts.tolist(),
                    "indices": inds.tolist(),
                }},
            }},
            {"op": "add_particles", "args": {
                "pos": points.tolist(),
                "vel": np.zeros_like(points).tolist(),
                "mass": [mass] * n_particles,
                "radius": [radius] * n_particles,
            }},
            {"op": "add_ground_plane", "args": {
                "cfg": {"$shape_cfg": {"mu": GROUND_FRICTION}},
            }},
        ],
        "post_finalize": {
            "model_calls": [
                {"method": "set_gravity", "args": [GRAVITY]},
            ],
            "mpm_attrs": [
                {"attr": "viscosity", "value": VISCOSITY},
                {"attr": "tensile_yield_ratio", "value": TENSILE_YIELD_RATIO},
                {"attr": "friction", "value": FRICTION},
            ],
        },
    }
    out = HERE / "recipe.json"
    out.write_text(json.dumps(recipe, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
