# Generate `newton_cli` — Phase 0 scaffold only

You are generating the **bootstrap scaffold** for an agent-native CLI wrapping
NVIDIA Newton, a GPU-accelerated physics engine built on Warp. This is the first
of many passes — generate ONLY what is listed under "In scope for this pass".
Everything else will be added test-first by humans in subsequent passes.

## Project context

- Newton source is vendored at `./newton/` and is **read-only**. Do not modify it.
- Generate all new code under `./newton_cli/` at the repo root.
- Target consumers: LLM agents (Claude Code, Cursor, custom agents), not humans.
- The long-term acceptance test is "every example under
  `./newton/newton/examples/` can be reproduced by a sequence of `newton-cli`
  invocations." You are NOT building that today. You are building the
  introspection + plumbing layer that lets humans grow the rest test-first.

## Hard constraints (do not violate any of these)

### API boundary

Only wrap symbols re-exported by these public modules:

```
newton
newton.geometry
newton.solvers
newton.sim
newton.ik
newton.sensors
newton.usd
newton.viewer
newton.utils
newton.math
newton.examples
```

**FORBIDDEN**: any import from `newton._src.*`. If a symbol is not reachable from
the modules above via `dir()`, do not wrap it. Discover symbols by importing each
module and walking `dir()` filtering names starting with `_`. Use
`inspect.signature` and `__doc__` as ground truth — do not parse source files.

### Type handling

When mapping a Python signature to CLI flags:

| Python type                              | CLI representation                              |
|------------------------------------------|-------------------------------------------------|
| `int` / `float` / `str` / `bool` / `Enum`| `--flag <value>`                                |
| `pathlib.Path`                           | `--flag <path>`                                 |
| `list[int\|float\|str]`                  | `--flag a,b,c` (comma split) or repeated flag   |
| `wp.array[...]` / `wp.vec*` / `wp.mat*`  | `--flag <path>` (load `.npy` at runtime, convert to `wp.array` on the active device) |
| `newton.Model` / `State` / `Control`     | `--model` / `--state` / `--control <path>` (round-trip via `newton.usd` if available, else pickle) |
| callbacks / lambdas / generic objects    | **SKIP** the method, do not generate a command  |

Rules:
- **Never** JSON-serialize a `wp.array` directly.
- **Never** call `wp.synchronize()` or `wp.synchronize_device()` immediately
  before `.numpy()` — `.numpy()` already syncs.

### Output contract (every command)

- Default stdout: human-readable text or table.
- With `--json`: `{"schema":"newton-cli/v1","data":...}` on stdout.
- On error: `{"schema":"newton-cli/v1","error":{"code","message","hint"}}` on
  stderr, non-zero exit.
- Exit codes:
  - `0` success
  - `2` user / argument error
  - `3` Newton or Warp runtime error
  - `4` missing optional dependency (print a `uv sync --extra <group>` hint)

### Testing

- Use stdlib **`unittest`** (Newton's convention), not pytest.
- Mark CUDA-required tests with a decorator that probes `wp.get_devices()` at
  runtime so CPU-only machines still pass the suite.

## In scope for this pass

Generate **only** these subcommands:

1. `newton-cli version` — Newton version, Warp version, Python version, CLI version.
2. `newton-cli devices list` — wrap `wp.get_devices()`. Reports CUDA/CPU.
3. `newton-cli api list [--module <name>]` — walks the allow-listed modules and
   emits a flat catalog of public symbols (`name`, `module`, `kind`, one-line
   doc summary). With no `--module`, lists all.
4. `newton-cli api describe <dotted.symbol>` — `inspect.signature` + `__doc__`
   for one symbol. Resolve dotted names like `solvers.SolverMuJoCo`.
5. `newton-cli examples list` — wrap `newton.examples.get_examples()`.
6. `newton-cli examples describe <name>` — pull the example class docstring AND
   the flags exposed by `newton.examples.create_parser()` (name, type, default,
   help) as JSON.
7. `newton-cli examples run <name> [-- <forwarded args>]` — internally call
   `newton.examples.main` with `sys.argv` rewritten. Forward all flags after
   `--` verbatim. Capture and report whether `Example.test_final()` passed.

Plus the supporting scaffolding:

- `pyproject.toml` at repo root for the `newton_cli` package. Depend on
  `newton @ file:./newton`. Optional extras mirror Newton's: `sim`, `importers`,
  `examples`. **Do not** add new required deps beyond what stdlib + Newton
  provide. Prefer `argparse` over `click`/`typer` to keep the dep surface small.
- `newton_cli/__init__.py`, `newton_cli/__main__.py`, `newton_cli/cli.py`.
- `newton_cli/io.py` with `emit(data, *, json: bool)` and
  `fail(code, message, *, hint=None, json: bool)` helpers used by every command.
- `newton_cli/_introspect.py` with the allow-list-driven public-symbol walker.
- `tests/` with `unittest` cases for the seven commands above. The tests should
  invoke the CLI via `subprocess.run([sys.executable, '-m', 'newton_cli', ...])`
  so they exercise the real argv path, not internal functions.
- `newton_cli.opencli.json` describing the generated commands per the
  OpenCLI specification at https://www.openclispec.org/.

## Out of scope (do NOT generate any of this in this pass)

- **No** `newton-cli model` command tree. The model-building surface will be
  designed test-first against `example_basic_pendulum` in the next pass.
  Generating one subcommand per `ModelBuilder.add_*` method now would lock in
  the wrong design.
- **No** `newton-cli sim` command tree. Same reason.
- **No** `newton-cli viewer` command tree. The viewer is GUI-heavy and only
  earns its place when an example needs it.
- No `newton-cli ik`, `sensors`, `selection`, `solvers` standalone trees.
- No wrapping of any private `_src` symbol, even if it looks useful.
- No code that imports `pyglet`, `imgui_bundle`, `mujoco`, or `mujoco_warp`
  at module load time. These must be lazy.

## Deliverables

Produce, in this order:

1. The directory tree you intend to create (one short list).
2. The `pyproject.toml`.
3. Each Python file under `newton_cli/`.
4. Each test file under `tests/`.
5. The `newton_cli.opencli.json` manifest.
6. A short `BOOTSTRAP_NOTES.md` documenting any decisions you made (e.g.,
   "chose argparse over typer because…", "skipped symbol X because its
   signature contained a callback") so a human reviewer can audit them.

When you finish, the following must succeed from the repo root:

```bash
uv run python -m newton_cli version --json
uv run python -m newton_cli devices list --json
uv run python -m newton_cli api list --json | head
uv run python -m newton_cli examples list --json
uv run python -m unittest discover tests
```

If any of these would fail given the code you generated, fix the code before
finalizing the output.
