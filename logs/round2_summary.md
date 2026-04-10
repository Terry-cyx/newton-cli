# Round 2 — expanding example coverage from 9 → 19

Current: **19 / 65 examples** driven end-to-end through `newton-cli` with
recipe + sim run + viewer render. 23 / 23 unit tests green.

## Newly green this round (10 examples)

| # | Example | Category | Notes |
|---|---|---|---|
| 10 | `robot_h1` | robot | Unitree H1 humanoid, clone of g1 pattern |
| 11 | `pyramid` | contacts | 6-cube pyramid (scaled down from default 4200) |
| 12 | `cloth_hanging` | cloth | 64×32 cloth grid hanging under gravity |
| 13 | `basic_plotting` | basic | 4 NVIDIA humanoids via MJCF + MuJoCo |
| 14 | `softbody_dropping_to_cloth` | multiphysics | Tet block dropping onto 40×40 cloth |
| 15 | `cloth_bending` | cloth | Curved cloth from `curvedSurface.usd` — prep extracts mesh |
| 16 | `softbody_gift` | multiphysics | 4 pyramids wrapped in 2 cloth straps, all procedural |
| 17 | `cloth_poker_cards` | cloth | 52 poker cards on a cube platform (skipped kinematic sphere) |
| 18 | `cable_y_junction` | cable | Y-shaped rod graph, tip pinned |
| 19 | `mpm_granular` | mpm | Granular material via `SolverImplicitMPM` |

## New CLI surface added this round

### Recipe ops (special)
- **`pin_body`** — zeros a body's mass + inertia so it stays fixed.
  Used by `cable_y_junction`.
- **`register_solver_custom_attributes`** — generic version of the
  existing `register_mujoco_custom_attributes`. Takes `{"solver": "<classname>"}`
  and calls that solver's `register_custom_attributes(builder)`.
  Used by MPM.

### Tag handlers
- **`$mesh_from_usd`** — load a `newton.Mesh` from a USD stage + prim path.
  Available but most USD-mesh examples extract vertices+indices at prep
  time instead, which keeps the recipe self-contained. Reserved for cases
  where re-loading the USD at recipe-execution time is preferable.
- **`$mesh`** — inline `{vertices, indices}` → `newton.Mesh`. Not yet
  used by any test — prep-time baking of vertices into `add_cloth_mesh`
  args has been simpler.

### Sim runner extensions
- **MPM projection pass** — after each `solver.step()`, if the solver
  has a `project_outside` method, call it. This is what MPM needs to
  push particles out of colliders.
- **Auto-Config construction** — if the solver's `__init__` requires a
  `config` positional arg (e.g. `SolverImplicitMPM(model, config=...)`),
  build a `solver_cls.Config()` from `--solver-arg` key=value pairs and
  pass it as the config. Other solvers continue to use `**solver_kwargs`.

### Viewer render
- **`show_particles = True`** set on `ViewerGL` before rendering, so MPM
  and other particle-based scenes render their particles, not just
  colliders. Without this, mpm_granular looked like just a floating cube.

### PowerShell ps1 reliability
- **`$ErrorActionPreference = "Continue"`** instead of `"Stop"` in the
  ps1 scripts for examples that emit benign stderr warnings during
  model build (e.g. "non-manifold edge" in `softbody_gift`). The
  `$LASTEXITCODE -ne 0` checks still catch real failures; Continue just
  stops PowerShell from mistaking Python warnings for command errors.

## Deferred this round (15 examples)

Each defer has a clear reason:

| Example | Blocker |
|---|---|
| `cable_pile` | 40 cables × 40 segments = imperative geometry generation using `create_straight_cable_points` helpers. Doable via prep but ~1600 bodies makes it slow. |
| `cable_bundle_hysteresis`, `cable_twist` | Custom `@wp.kernel` for forces. |
| `basic_conveyor` | Custom per-substep `@wp.kernel` drives a kinematic belt. |
| `cloth_franka`, `cloth_h1`, `cloth_rollers`, `cloth_twist` | Custom kernels. |
| `cloth_style3d` | Needs `style3d.add_cloth_mesh` module-level function + remote asset + UV mesh data. |
| `contacts_rj45_plug`, `brick_stacking` | Custom kernels. |
| `diffsim_*` (6) | Differentiable simulation — outside stateless CLI model. |
| `ik_cube_stacking`, `ik_custom` | Custom IK kernels. |
| `ik_franka`, `ik_h1` | Empty `test_final`. |
| `mpm_anymal` | Torch policy. |
| `mpm_beam_twist`, `mpm_snow_ball`, `mpm_twoway_coupling` | Custom kernels. |
| `mpm_multi_material`, `mpm_viscous`, `mpm_grain_rendering` | Need per-particle `model.mpm.<attr>[indices].fill_(...)` post-finalize mutations + funnel mesh generator. |
| `nut_bolt_hydro`, `nut_bolt_sdf` | Clone `IsaacGymEnvs` repo for mesh assets + `mesh.build_sdf(...)`. |
| `recording`, `replay_viewer`, `basic_viewer` | Empty `test_final` (Wave C, already deferred). |
| `robot_allegro_hand`, `robot_panda_hydro` | Custom kernels (grasping control). |
| `robot_anymal_c_walk`, `robot_policy`, `mpm_anymal` | Trained torch policies. |
| `robot_ur10` | Empty `test_final`. |
| `selection_*` (4) | Trained torch policies + custom kernels. |
| `sensor_contact` | Per-step sensor updates + `plates_touched` state tracking. |
| `sensor_imu`, `sensor_tiled_camera` | Custom kernels. |
| `softbody_franka` | Custom kernels. |

## Running totals

- ✅ **19 / 65 examples** green via CLI
- 🚫 **~40 deferred** with documented blockers
- 🎯 **~6 achievable remaining** with moderate infrastructure investment
  (per-particle MPM fills, funnel mesh generator, SDF build)

## What the remaining 6 would need

1. **MPM variants (4 examples)** — a `set_mpm_attr` special op that
   accepts `{attr, indices, value}` and does
   `model.mpm.<attr>[indices].fill_(value)` post-finalize. Plus a
   `funnel_mesh` or generic parametric mesh op. Plus post_finalize
   support for calling methods like `set_gravity(tuple)`.

2. **nut_bolt_hydro/sdf (2 examples)** — a new asset loader in prep that
   can clone external git repos, plus exposing `Mesh.build_sdf(...)`.
