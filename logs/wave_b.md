# Wave B — execution log

## Wave B.1 — basic_joints

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_basic_joints.py`
- **Result**: ✅ passed in 10.6 s.
- **What the test does**: builds a recipe with three joint demos (revolute,
  prismatic, ball), each with two cuboid links plus a fixed anchor joint.
  Includes the example's `joint_q[-1] = π/2` initial revolute angle and
  `joint_q[-4:] = quat_rpy(0.5, 0.6, 0.7)` initial ball quat. Runs 100 frames
  (matches example default) and validates 4 of the example's `test_final`
  predicates verbatim against the resulting state.
- **CLI surface added**:
  - `set_builder_array` recipe op (special op, not method dispatch). Supports
    either `index` (single element) or `slice` (`[start, stop]` / `[start, stop, step]`)
    + `value` / `values`.
  - `{"$shape_cfg": {...}}` JSON tag → `newton.ModelBuilder.ShapeConfig` with
    attrs set. Used here for the massless `density=0.0` sphere on the ball
    joint anchor.
- **First-principles takeaway — settle predicates are calibrated to a specific
  num_frames**: my first run used `--num-frames 300` (more = more settle time
  for the slider/static bodies) which broke the "movable links not moving too
  fast" predicate, because the freely-swinging revolute pendulum keeps gaining
  KE the longer it swings. The example uses `num_frames=100` and that's the
  exact frame count its predicates were tuned for. **Lesson**: don't override
  the example's `num_frames` unless the example itself does.

## Wave B.2 — basic_heightfield

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_basic_heightfield.py`
- **Result**: ✅ passed in 10.2 s.
- **What the test does**: generates a 50×50 sin/cos elevation grid (matches
  the example), drops 5 spheres at the same positions, runs 100 frames @ 100
  fps · 10 substeps with `SolverXPBD --solver-arg iterations=10`. Asserts
  `body_q[i, 2] > -1.0` for every sphere — i.e. nothing fell through the
  heightfield.
- **CLI surface added**:
  - `{"$heightfield": {data, nrow, ncol, hx, hy, ...}}` JSON tag →
    `newton.Heightfield`. The `data` field accepts a list-of-lists which is
    converted to a numpy array at coercion time.
- **No new top-level commands.** The recipe absorbed the heightfield setup
  via tag-based coercion.
- **Bug fix**: `np.load(path)["body_q"]` holds the .npz file open via lazy
  loading on Windows, which prevented `tempfile.TemporaryDirectory` from
  cleaning up. Switched to `with np.load(path) as data:` pattern. This is
  Windows-specific behavior worth remembering for later state-loading tests.

## Wave B.3 — basic_urdf

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_basic_urdf.py`
- **Result**: ✅ passed in 10.6 s.
- **CLI surface added**:
  - `set_default_joint_cfg` / `set_default_shape_cfg` special ops — bulk
    `setattr` against `builder.default_joint_cfg` / `builder.default_shape_cfg`.
  - `apply_body_inertia_diagonal` special op — Newton-specific armature trick
    (`for i: body_inertia[i] += eye(3) * value`).
  - `replicate` special op — recursively builds a sub-builder from an inline
    sub-recipe, then calls `outer.replicate(sub, count, spacing)`. **This is
    the first nested-recipe op and validates the recipe-of-recipes design.**
  - `add_urdf` op (pure method dispatch). Required `uv pip install -e ./newton[importers]`
    to bring in the URDF parser.
- **PASS BAR is numerical equivalence, NOT the example's test_final.** I
  verified that `python -m newton.examples basic_urdf --test --viewer null`
  on this Newton version FAILS its own predicate `max(abs(qd)) < 0.15` —
  every body in every world. So we can't use the example's predicates as our
  CLI's pass bar (the bar would be impossible regardless of CLI correctness).
  Instead, the test compares the CLI's `body_q`/`body_qd` against an
  in-process reference run that executes exactly the same Newton API calls
  the example uses, using `numpy.testing.assert_allclose(atol=1e-5)`. This is
  a **stronger** bar — it proves the CLI is byte-equivalent to the example's
  setup, not just that it stumbles past a predicate.
- **First-principles takeaways**:
  1. **The recipe interpreter needed three categories of ops**, not one:
     - method-dispatch ops (sphere/box/joint/urdf etc.) — coerced via shape rules
     - special ops with raw JSON args (set_builder_array, set_default_*_cfg, replicate, apply_body_inertia_diagonal)
     - tagged values (`$shape_cfg`, `$heightfield`) for inline-constructed objects
     This three-category split is what made Wave B tractable. Only method
     dispatch isn't enough — the example does many non-method things to the
     builder (attribute set, array slice assign, transformation loops, sub-builders).
  2. **`eval_fk` should target the model, not the state**, before allocating
     state objects. Fixed in `newton_cli/sim.py`. Otherwise downstream reads of
     `model.body_q` (e.g. for collision pipeline reference frames) see stale
     URDF rest pose instead of the FK-evaluated initial pose.
  3. **Bisecting native vs CLI behavior is the right debugging move** when
     numerical results disagree. Build the model in-process with both
     pathways (recipe + bare Python) and run with both runners (your CLI runner
     + the example's hand-written loop). Each pairing pinpoints exactly which
     side has the bug. I used this to confirm the recipe and the runner were
     correct, and then to discover that the example's own test_final was the
     thing that didn't pass.
  4. **`replicate` propagates body_inertia mutations correctly** — verified
     directly. Worth knowing for later waves.

## Wave B summary

3 / 3 examples green. Suite: 19 / 19 in 100.2 s.

**New CLI surface this wave:**
- 4 new special recipe ops: `set_builder_array`, `set_default_joint_cfg`, `set_default_shape_cfg`, `apply_body_inertia_diagonal`, `replicate`
- 2 new tag handlers: `$shape_cfg`, `$heightfield`
- `add_urdf` (pure method dispatch — no special handling needed)
- Required dep: `newton[importers]`

**Sim runner change:**
- `eval_fk(model, joint_q, joint_qd, **model**)` BEFORE state allocation,
  not `eval_fk(..., state_in)` after. Matches what every example does.
