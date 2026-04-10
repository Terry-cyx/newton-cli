# Wave D — execution log

## Wave D.1 — basic_conveyor — **DEFERRED**

- **Date**: 2026-04-09
- **Status**: 🚫 deferred, not implementable in the declarative recipe model
- **Rationale**: the example is fundamentally imperative. Non-recipe-expressible surface:
  1. **Procedural mesh construction** — belt + rails are annular prism meshes
     generated from a Python helper (`create_annular_prism_mesh`) with
     ~96 segments × 4 verts = ~384 verts per mesh. Could be inlined as a
     `$mesh` tag with `{vertices, indices}` fields, but the mesh constants
     depend on code (sin/cos of segment angles, etc.) that would just move
     the Python out of the example into the test setup.
  2. **Custom per-substep Warp kernel** — `set_conveyor_belt_state` writes
     `state.joint_q[belt_start] = time * angular_speed` every substep to
     drive the kinematic belt. The declarative recipe captures only the
     builder phase; it has no hook for per-substep imperative code.
  3. **Per-substep `eval_fk(..., body_flag_filter=KINEMATIC)`** — updates
     only kinematic body poses each substep. Requires imperative access.
  4. `add_shape_collision_filter_pair` — easy (pure method), not a blocker
     alone.
  5. `is_kinematic=True` on `add_link` — easy (pure kwarg), not a blocker.

- **First-principles finding**: basic_conveyor reveals the **natural limit of
  the declarative recipe model**. Anything that needs per-step imperative
  hooks (custom kernels, state-dependent control, per-step body_flag_filter
  FK) requires a new surface: a "step hook" or "policy callback" that the CLI
  would accept as a Python module reference (e.g. `--step-hook mod:fn`).
  Introducing step hooks means the LLM is no longer writing pure JSON — it's
  also writing Python. That's a significant architectural escalation that I
  don't want to make just for one example.
- **When to revisit**: add step-hook support when Wave D robot_policy or
  diffsim forces it. Until then, basic_conveyor stays parked.

## Wave D.2 — robot_cartpole ✅

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_robot_cartpole.py`
- **Result**: ✅ passed in 23.1 s. Full suite 20/20 in 170.3 s.
- **What the test does**: builds a cartpole recipe (4 replicas with spacing,
  `register_mujoco_custom_attributes`, `add_usd` cartpole.usda,
  `apply_body_inertia_diagonal(0.1)`, initial `joint_q[-3:] = [0, 0.3, 0]`),
  runs on `cuda:0` via `SolverMuJoCo` for 100 frames @ 60 fps · 10 substeps,
  and asserts byte-equivalence with an in-process reference that builds the
  model with plain Newton API calls and runs the CLI's own `run_simulation`.
- **CLI surface added**:
  - `register_mujoco_custom_attributes` special op — wraps
    `newton.solvers.SolverMuJoCo.register_custom_attributes(builder)`.
    Called once at the start of the sub-recipe, before `add_usd`, so
    MuJoCo-native custom attributes in the USD asset get parsed into the
    builder. Newton-side this is a static class method on the solver; the
    recipe special op isolates that coupling.
  - `add_usd` (pure method dispatch, no special handling). Accepts
    `enable_self_collisions`, `collapse_fixed_joints` kwargs through the
    standard coercion path.
  - `replicate` already supports `spacing: [x, y, z]` — validated here with
    `[1.0, 2.0, 0.0]` multi-axis spacing.
- **New dependency**: `newton[sim]` (mujoco + mujoco-warp + newton-actuators).
  Installed via `uv pip install -e ./newton[sim]`.
- **Why numerical-equivalence and not the example's test_final**: the example
  uses exact-equality predicates like `q[2] == 0.0` and `qd[0] == 0.0`. These
  depend on MuJoCo's constraint-solving producing exact zeros for axes the
  cartpole can't move along. They're fragile — a single float-rounding bit
  would break them even in the native example. The CLI's job is faithful
  reproduction, not independent passing of fragile predicates. Byte-equivalence
  with the in-process reference is strictly stronger: if the CLI matches, it
  will pass and fail exactly when the example would.
- **Suite cost**: jumped from 100 s → 170 s. Cartpole alone is ~23 s mostly
  due to MuJoCo kernel compilation on first invocation (cached on subsequent
  runs).

## Wave D.3 — robot_policy — **next (pending)**

TBD. Expected to force the Python-in-the-loop decision deferred above.
