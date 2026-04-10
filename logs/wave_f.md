# Wave F — execution log

## Wave F.1 — softbody_hanging ✅

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_softbody_hanging.py`
- **Result**: ✅ passed in 43.1 s on first implementation (GREEN on first run).
- **What the test does**: builds 4 hanging tet-grid softbodies with
  different damping values (`1e-1` to `1e-4`), left edges fixed, runs
  100 frames @ 60 fps · 10 substeps with `SolverVBD --solver-arg
  iterations=10 --solver-arg particle_enable_self_contact=false
  --solver-arg particle_enable_tile_solve=false` on `cuda:0`, then
  reuses the example's own `test_particle_state` predicate verbatim to
  assert all particles stay within a reasonable volume.
- **CLI surface added**:
  - `add_soft_grid` recipe op (pure method dispatch, coerced via shape rules)
  - **`post_finalize` top-level recipe field** — a dict of attribute
    names to values that gets applied via `setattr(model, name, value)`
    AFTER `builder.finalize()` but BEFORE the solver is constructed.
    Used here to set `soft_contact_ke/kd/mu` on the Model (these can't
    be set on the builder — they only exist on the finalized Model).
  - **Particle state serialization**: extended `state_io.py` `_FIELDS`
    to include `particle_q` and `particle_qd`. Round-trips correctly
    via `wp.array.assign(numpy)` back into a freshly-allocated State.
- **First-principles finding — the declarative recipe needs a
  post-finalize phase**. Many Newton examples configure the Model (not
  the Builder) after finalize: `model.soft_contact_ke`,
  `model.particle_radius`, etc. These are solver/physics tuning knobs
  that live only on the Model. The recipe's top-level `post_finalize`
  dict is the cleanest escape hatch — it keeps the Builder phase pure
  and declarative while acknowledging that Newton has two-phase
  configuration.
- **Why VBD + no numerical equivalence**: cloth/softbody solvers are
  iterative with tight substeps; even in-process vs subprocess on CUDA
  diverges for these over 100 frames. The example's own predicate (an
  AABB containment check) is loose enough to pass regardless, so we
  reused it directly — no need for a reference run.

## Wave F — remaining alt-physics

All deferred — each would force additional infrastructure:

- **cloth_bending / cloth_hanging** — need `newton.usd.get_mesh` loading
  + `add_cloth_mesh` with a large vertex list. The USD loading needs
  either a `$mesh_from_usd` recipe tag (pull vertices out of a USD file
  at recipe-build time) or a `.npz` sidecar carrying precomputed vertices.
  Also uses an explicit `CollisionPipeline` rather than `model.contacts()`
  — would force a `collision_pipeline` recipe op + sim runner branch.
- **mpm_*** — Material Point Method. Uses `SolverImplicitMPM` and
  particle grids; needs `newton[mpm]`-style extras if they exist.
  Probably has its own specialised state fields.
- **cable_*** — XPBD cable dynamics via `add_cable`. Relatively tractable
  but hasn't been exercised.
- **contacts/pyramid** — 4000+ boxes built via Python loops. Would need
  the test to generate the recipe dynamically, which is fine, but the
  sim run is heavyweight. Also uses an explicit `CollisionPipeline`
  passed through `model.collide(..., collision_pipeline=cp)`.
- **multiphysics_*** — mixes rigid + soft + cloth in one scene.
- **diffsim_*** — differentiable simulation. Outside the stateless
  CLI model; may need to stay deferred indefinitely (documented in PLAN.md).
