# Round 3 — A 路线收尾，把声明式 CLI 推到极致

Status: **25 / 65 examples** green via pure declarative `recipe.json` + CLI.
Round 3 added 6 new examples (19 → 25).

## Round 3 newly green (6 examples)

| # | Example | Category | What it stressed |
|---|---|---|---|
| 20 | `mpm_multi_material` | mpm | Per-particle MPM material attributes (sand/snow/mud) via masked `model.mpm.<attr>[indices].fill_(value)` |
| 21 | `mpm_viscous` | mpm | Funnel mesh + cone-filtered particle list, full-array `mpm_attrs`, `model.set_gravity()` post-finalize |
| 22 | `mpm_grain_rendering` | mpm | Single-particle-cluster MPM (rendering grain layer is cosmetic — physics part is the same as mpm_granular) |
| 23 | `cable_pile` | cable | 1600 bodies via 40 prep-time `add_rod` calls; VBD coloring; `set_builder_attr` for `rigid_gap` |
| 24 | `nut_bolt_hydro` | contacts | IsaacGymEnvs git asset clone + trimesh OBJ load + `Mesh.build_sdf` + hydroelastic contacts + MuJoCo solver |
| 25 | `nut_bolt_sdf` | contacts | Same as hydro but `is_hydroelastic=False` (regular SDF contacts) |

## New CLI surface added this round

### `recipes.py` — interpreter extensions

- **`post_finalize.mpm_attrs`** — list of structured entries that fire
  after `builder.finalize()` to write per-particle MPM material attrs.
  Each entry: `{"attr": <name>, "range"|"indices": ..., "value": <scalar|vec3>}`.
  Range form `{"range": [lo, hi]}` is the typical case (one
  `add_particle_grid` op produces a contiguous range). Full-array form (no
  selector) fills the whole `model.mpm.<attr>` array.
  Used by mpm_multi_material (per-cluster fills) and mpm_viscous (whole-array fills).

- **`post_finalize.model_calls`** — list of `{"method": <name>, "args": [...], "kwargs": {...}}`
  that invoke methods on the finalized `Model`. Args/kwargs go through the
  normal vec3/quat/transform coercion. Currently used for `model.set_gravity((0,0,-10))`
  in mpm_viscous; pattern generalises to any post-finalize model mutation
  that's a method call rather than a setattr.

- **`set_builder_attr`** — special op `{"op": "set_builder_attr", "args": {"name": "...", "value": ...}}`.
  Generic scalar attribute setter on the builder itself. Used by cable_pile
  for `builder.rigid_gap = 0.05`. Distinct from `set_default_shape_cfg` /
  `set_default_joint_cfg` because those write into a sub-config object.

- **list-of-vec3 / list-of-quat coercion** in `_coerce_value`. Builder
  methods like `add_rod(positions=..., quaternions=...)` require Warp types
  for each list element, not raw `[x,y,z]`. The coercer now detects when
  every list element looks like a vec3 (or quat) and converts uniformly.
  Unblocked cable_pile and is harmless for `add_rod_graph` (which already
  worked with raw lists; passing wp.vec3 is also accepted).

- **`$mesh.build_sdf`** tag-handler extension — `{"$mesh": {vertices, indices,
  build_sdf: {max_resolution, narrow_band_range, margin, scale}, ...}}`
  calls `mesh.build_sdf(**kwargs)` after construction. Lets recipes carry
  contact-quality SDF settings without inventing a separate post-add op.
  Also accepts `is_solid` and `compute_inertia` flags.

### Sim runner

No changes — `_instantiate_solver`, `project_outside`, and `eval_fk(..., model)`
from rounds 1–2 already covered MPM, MuJoCo, VBD, and SDF-mesh contact paths.

### Test infrastructure

No changes; per-example folders use the same `recipe.json` (or `prep.py` →
`recipe.json`) + `run.ps1` + `outputs/{model.json, final.npz, render.png, ...}`
pattern as Round 2.

## Deferred to B route (cloth_style3d)

`cloth_style3d` is the one remaining "tractable" example I deliberately did
NOT push through Round 3. It hit three intersecting blockers:

1. **`style3d.add_cloth_mesh(builder, ...)` is a module-level function**, not
   a `ModelBuilder` method. Recipe op-dispatch goes through `getattr(builder, op)`
   so module functions need a new "module_call" op.
2. **`solver._precompute(builder)` requires the live builder reference**,
   not just the finalized model. The CLI's sim runner takes a model file,
   re-executes the recipe to rebuild, then drops the builder. To support
   this, `build_model_from_recipe` would need to optionally return the
   builder, AND the sim runner would need a "post-construct, pre-step"
   hook that knows the solver-specific precompute protocol.
3. **`download_asset("style3d")` + `newton.usd.get_mesh(prim, load_uvs=True,
   preserve_facevarying_uvs=True, return_uv_indices=True)`** — the asset
   download is fine (Newton already has the helper), but the UV index
   pipeline produces TWO arrays (vertices/indices for triangles, separate
   UV vert array + UV index array for facevarying). Baking both into a
   recipe is doable but the JSON gets large and there's no `$cloth_mesh`
   tag analogue yet.

Each of (1)/(2)/(3) is solvable individually but solving all three for
**one** example is bad ROI compared to the B-route alternative — once
`run-script` exists, cloth_style3d becomes a 30-line Python script.

## Round 3 numbers

- Round 2: 19 / 65 examples ✅
- Round 3: **25 / 65 examples ✅** (+ 6)
- Tracker breakdown of remaining 40:
  - ~7 with empty `test_final` (no validation, can't claim "passing")
  - ~6 differentiable simulation (`diffsim_*`) — by definition Python-in-the-loop
  - ~3 trained-policy loops (`robot_policy`, `mpm_anymal`, `robot_anymal_c_walk`)
  - ~4 selection examples with custom kernels + torch
  - ~18 with custom `@wp.kernel` per-step (cloths, cables, sensors, contacts, conveyor, etc.)
  - 1 cloth_style3d (the deferred one above)
  - 1 nut_bolt with rotation tracking — passes physical sanity, not exact test_final

This is the natural ceiling of the **declarative** route. The B route
(`run-script`) is the only way to push past 25.

## What B route needs to ship next

1. `newton-cli run-script <path> [--out artifacts.json] [--timeout S]`
   — subprocess wrapper with structured exit envelope.
2. Test harness pattern: per-example `script.py` + `run.ps1` that invokes
   `newton-cli run-script script.py`, captures the produced state .npz,
   and validates against the example's own `test_final()` predicate.
3. Decide on a "minimal Newton boilerplate" reference script template so
   the per-example scripts only express what's unique (custom kernel,
   policy load, etc.).
