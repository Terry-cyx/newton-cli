# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Build `newton-cli` — an agent-native CLI wrapper around NVIDIA's [Newton](https://github.com/newton-physics/newton) physics engine — so an LLM agent can drive Newton without writing Python.

**Defining principle: Newton's `examples/` directory is the spec.** The CLI is "complete" when every example under `../newton/newton/examples/` can be reproduced by a sequence of `newton-cli` invocations that pass the example's own `test_final()` validation. We do not enumerate Newton's API surface top-down; we grow the CLI bottom-up from real example demand. If a CLI command isn't needed to run an example, it doesn't get built (yet).

## Repository layout (standard src layout)

This project lives at `E:/newton-cli/newton_cli/`. The vendored Newton source is a **sibling** at `E:/newton-cli/newton/`. The two-folder split keeps upstream untouched.

```
E:/newton-cli/
├── newton/                     # vendored upstream Newton (read-only)
└── newton_cli/                 # THIS project
    ├── .venv/                  # local virtualenv (uv)
    ├── pyproject.toml          # depends on newton via path "../newton"
    ├── README.md
    ├── CLAUDE.md               # this file
    ├── PLAN.md                 # wave-by-wave execution plan
    ├── src/
    │   └── newton_cli/         # the Python package
    │       ├── __init__.py
    │       ├── __main__.py     # lazy-inits Warp under stdout redirect
    │       ├── cli.py          # argparse dispatcher
    │       ├── io.py           # emit / fail envelope helpers
    │       ├── _introspect.py  # allow-list API walker
    │       ├── _warp.py        # silent Warp init
    │       ├── recipes.py      # JSON recipe → ModelBuilder
    │       ├── sim.py          # step loop
    │       └── state_io.py     # .npz round-trip
    ├── tests/
    │   ├── _cli.py             # subprocess runner helper
    │   ├── test_phase0_introspection.py
    │   └── test_examples/      # one test file per Newton example
    ├── logs/                   # wave logs + session summaries
    └── prompts/                # prompt fragments (bootstrap etc.)
```

- `../newton/` — vendored upstream Newton repo (NVIDIA, Apache-2.0). **Read-only.** Newton's own dev guide is `../newton/AGENTS.md` and applies only when editing files inside `../newton/`.
- `src/newton_cli/` — the Python package (src layout). Installed into the venv via `uv pip install -e .`.
- `tests/` — TDD harness. One test class per Newton example. Each test runs a sequence of `newton-cli` commands via subprocess and asserts the final `State` either matches an in-process reference or passes the example's own `test_final()` predicates.
- `prompts/` — prompt fragments (historical: CLI-Anything bootstrap that we ultimately didn't use).
- `PLAN.md` — wave-by-wave execution plan. Update as examples turn green.

## Workflow: test-driven, examples-as-spec

1. **Pick an example** from the next wave in `PLAN.md` (start with `basic_pendulum`).
2. **Read its source** under `../newton/newton/examples/<category>/example_<name>.py` to understand what `ModelBuilder` calls, solver, and step loop it uses.
3. **Write a failing test** in `tests/test_examples/test_<name>.py` that:
   - invokes `newton-cli` subcommands to reproduce the example,
   - loads the resulting `State`,
   - asserts equivalence (within tolerance) with the reference example's `test_final()` checks.
4. **Implement just enough** CLI surface to make that one test pass. New commands must be justified by an example.
5. **Mark the example green** in `PLAN.md` and move on.

The first wave defines almost the entire core; later waves mostly add adapters (URDF importer, MuJoCo solver, sensors, etc.). Resist the urge to add commands "for completeness."

## Key facts about upstream Newton

- Public API only: `newton`, `newton.geometry`, `newton.solvers`, `newton.sim` (re-exported into `newton`), `newton.ik`, `newton.sensors`, `newton.usd`, `newton.viewer`, `newton.utils`, `newton.math`. **Never import from `newton._src`.**
- Built on [Warp](https://github.com/NVIDIA/warp). Public APIs frequently take `wp.array[wp.vec3]`-style inputs that **do not JSON-serialize**. The CLI's strategy: any array-typed parameter is exposed as a file path (`.npy`) and loaded into a Warp array on the active device at runtime.
- `.numpy()` on a Warp array already syncs — never call `wp.synchronize()` right before it.
- Examples run via `python -m newton.examples <name>` (entry: `../newton/newton/examples/__init__.py::main`). Each example is an `Example` class with `step()` and `test_final()`. There is a shared argparse — `newton.examples.create_parser()` — with `--device`, `--num-frames`, `--viewer`, `--headless`, etc. **Reuse it; do not re-parse those flags.**
- Optional dep groups in `../newton/pyproject.toml`: `sim`, `importers`, `remesh`, `examples`, `dev`, `torch-cu12`. Detect missing groups and exit with code `4` and a `uv sync --extra <group>` hint.

## Conventions for `newton-cli`

- **`--json` everywhere.** Default human-readable; agents pass `--json` and parse `{"schema":"newton-cli/v1","data":...}`.
- **Deterministic exit codes.** `0` ok · `2` user/arg error · `3` Newton runtime error · `4` missing optional dep.
- **Artifacts over in-process state.** `Model` round-trips through its recipe JSON (recipe IS the model). `State` round-trips through `.npz`. Each invocation is reproducible from inputs alone.
- **Mirror Newton's prefix-first naming.** `model add-shape-sphere`, not `model add-sphere-shape`.
- **Headless by default.** GUI viewer (`pyglet`/`imgui_bundle`) only loaded under `viewer` subcommand (not yet implemented).
- **Don't reinvent example runner.** For "run a built-in scene" use cases, shell into `newton.examples.main` and forward args via `create_parser()`.
- **Prefix-first solver lookup.** Resolve solver classes from `newton.solvers` by name at runtime; never hardcode the list.

## Common commands (run from `newton_cli/`)

```bash
# One-time setup
uv venv --python 3.13
uv pip install -e .
uv pip install -e ../newton[importers,sim]
uv pip install GitPython                              # for download_asset

# Smoke tests
uv run python -m newton_cli version --json
uv run python -m newton_cli devices list --json
uv run python -m newton_cli api list --json
uv run python -m newton_cli examples list --json

# Run the CLI test suite
uv run python -m unittest discover tests
uv run python -m unittest tests.test_examples.test_basic_pendulum   # one example
```

Newton's own test suite (unrelated, run from `../newton/`):
```bash
cd ../newton && uv run --extra dev -m newton.tests
```

## See also

- `PLAN.md` — wave-by-wave TDD execution plan, with the example checklist.
- `logs/SESSION_SUMMARY.md` — current session status, decisions, next steps.
- `logs/wave_{a,b,c,d,e,f}.md` — per-wave execution logs.
- `../newton/AGENTS.md` — upstream Newton's dev rules (only relevant when editing `../newton/` itself).
