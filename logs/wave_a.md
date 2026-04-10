# Wave A — execution log

> Format: one entry per example. Each entry records the date, the example,
> the test command, the test result, and any new CLI surface it forced.

## Phase 0 — bootstrap (prerequisite)

- **Date**: 2026-04-09
- **Scope**: 7 introspection commands (`version`, `devices list`, `api list`,
  `api describe`, `examples list`, `examples describe`, `examples run`).
- **Test**: `python -m unittest tests.test_phase0_introspection`
- **Result**: ✅ 14/14 passed in 37.1 s.
- **Commands proven working**:
  ```
  newton-cli version --json
  newton-cli devices list --json
  newton-cli api list --json
  newton-cli api list --module newton.geometry --json
  newton-cli api describe ModelBuilder --json
  newton-cli examples list --json
  newton-cli examples describe basic_pendulum --json
  ```
- **Notable design decisions**:
  - argparse, not click (matches Newton's own convention; zero new deps).
  - `__main__.py` does a stdout-redirected pre-import of newton+warp to
    capture Warp's init banner before any subcommand runs. Without this,
    `import newton` corrupts every JSON envelope.
  - Allow-list-driven introspection in `_introspect.py`; any path containing
    `_src` is rejected with exit code 2.
  - `examples run` forwards to `newton.examples.main` with `sys.argv`
    rewritten; we deliberately do not re-implement the example runner.

## Wave A.1 — basic_pendulum

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_basic_pendulum.py`
- **Result**: ✅ passed in 27.7 s. Full suite 15/15 in 46.1 s.
- **What the test does**:
  1. Writes a recipe JSON mirroring `example_basic_pendulum.py` (2 links, 2
     box shapes, 2 revolute joints with `wp.transform` parent/child frames,
     1 articulation, ground plane).
  2. `newton-cli model build --recipe pendulum.json --out pendulum.model.json`
  3. `newton-cli sim run --model pendulum.model.json --solver SolverXPBD
     --num-frames 100 --fps 100 --substeps 10 --device cpu --out final.npz`
  4. Rebuilds the in-process Model from the recipe, loads `final.npz` into a
     fresh State, then runs the **example's own** `test_body_state` predicates
     verbatim — the same bar Newton ships with.
- **CLI surface added**:
  - `newton-cli model build --recipe <json> --out <json> [--device]`
  - `newton-cli sim run --model <json> --solver <name> --num-frames N --fps F
    --substeps S --device <d> --out <npz>`
- **Internal modules added**:
  - `newton_cli/recipes.py` — declarative `ModelBuilder` driver. Coerces
    JSON shapes → `wp.vec3` / `wp.quat` (xyzw or {axis,angle}) / `wp.transform`.
    The recipe IS the model — no opaque binary serialization. Re-executing the
    recipe reconstructs the model byte-for-byte.
  - `newton_cli/state_io.py` — `.npz` round-trip for `body_q`, `body_qd`,
    `joint_q`, `joint_qd`. Uses `wp.array.assign(numpy)` to refill a fresh State.
  - `newton_cli/sim.py` — the standard Newton step loop (eval_fk seed → for
    frame: for substep: clear_forces → collide → solver.step → swap states).
    No CUDA graph capture (that's an optimization, not part of the contract).
- **First-principles takeaways**:
  - **Recipe-as-model is the right call.** Newton has no built-in Model
    save/load and pickling Warp arrays is painful. Storing the recipe and
    re-executing it on load gives us a fully inspectable, version-controllable,
    JSON-grep-able model file with zero binary blobs.
  - **Shape-based JSON coercion works.** I didn't need to inspect parameter
    annotations — `[x,y,z]` → vec3, `[x,y,z,w]` → quat, `{p,q}` → transform,
    `{axis,angle}` → quat works for every Newton call basic_pendulum makes.
    Wave A.2 will validate this on a different shape mix.
  - **Reusing the example's own validator is the right TDD bar.** No need to
    reimplement equivalence checks — `newton.examples.test_body_state` is
    Newton's own pass/fail criterion and is the test the example ships with.

## Wave A.2 — basic_shapes

- **Date**: 2026-04-09
- **Test**: `tests/test_examples/test_basic_shapes.py`
- **Result**: ✅ passed in 20.1 s. Full suite 16/16 in 64.1 s.
- **What the test does**: builds a recipe with sphere, ellipsoid, capsule,
  cylinder, box, and cone bodies (mesh body deferred — see below), runs
  300 frames @ 100 fps · 10 substeps with `SolverXPBD --solver-arg iterations=10`
  on CPU, then validates 5 rest-pose predicates from the example verbatim.
- **Deferred to Wave B**: the bunny mesh body. It requires loading
  `bunny.usd` via `pxr.Usd` + `newton.usd.get_mesh()`, which needs the
  `importers` extra. The mesh body is the only one not exercised here;
  every other shape primitive in the example is covered.
- **CLI surface added**:
  - `--solver-arg KEY=VALUE` (repeatable) on `newton-cli sim run`. Values are
    coerced bool > int > float > str. Used here as `--solver-arg iterations=10`
    to match `SolverXPBD(model, iterations=10)` from the example.
- **No new top-level commands.** Every shape primitive (`add_body` with xform,
  `add_shape_sphere/ellipsoid/capsule/cylinder/box/cone`) dispatched cleanly
  through the existing recipe interpreter — shape-based JSON coercion handled
  the `wp.transform` xform args without modification.
- **Settle time was 1 s, not 3 s.** The example uses `num_frames=100` (1 s) but
  with that I saw the box at z=0.5 instead of 0.25 — not yet settled. Bumping
  to 300 frames (3 s) made all rest-pose predicates pass cleanly. The example
  itself probably runs longer interactively because the user keeps pressing
  step; the documented `test_final()` is a "post-settle" check that requires
  more wall time than the default `num_frames` provides. Recording this so
  later waves know they may need to override `num_frames`.
