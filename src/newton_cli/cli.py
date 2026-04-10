"""Top-level argparse dispatcher for newton-cli.

Phase 0 surface only — see PLAN.md for the wave roadmap.
"""

from __future__ import annotations

import argparse
import sys

from newton_cli import __version__ as cli_version
from newton_cli._introspect import (
    PRIVATE_MARKER,
    PUBLIC_MODULES,
    PrivateModuleError,
    describe_symbol,
    list_symbols,
)
from newton_cli._warp import init_warp_silently
from newton_cli.io import (
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_TIMEOUT,
    EXIT_USER_ERROR,
    emit,
    fail,
)


# ---------------------------------------------------------------------------
# parser construction
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="newton-cli",
        description="Agent-native CLI for NVIDIA Newton physics engine.",
    )
    parser.add_argument("--version", action="version", version=f"newton-cli {cli_version}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # version
    p_version = sub.add_parser("version", help="Print Newton/Warp/Python/CLI versions.")
    p_version.add_argument("--json", action="store_true", dest="json_mode")
    p_version.set_defaults(func=cmd_version)

    # devices
    p_devices = sub.add_parser("devices", help="Inspect compute devices.")
    devices_sub = p_devices.add_subparsers(dest="subcommand", metavar="<subcommand>")
    p_devices_list = devices_sub.add_parser("list", help="List Warp devices.")
    p_devices_list.add_argument("--json", action="store_true", dest="json_mode")
    p_devices_list.set_defaults(func=cmd_devices_list)

    # api
    p_api = sub.add_parser("api", help="Browse Newton's public API.")
    api_sub = p_api.add_subparsers(dest="subcommand", metavar="<subcommand>")
    p_api_list = api_sub.add_parser("list", help="List public symbols.")
    p_api_list.add_argument("--module", default=None, help="Filter to one public module.")
    p_api_list.add_argument("--json", action="store_true", dest="json_mode")
    p_api_list.set_defaults(func=cmd_api_list)
    p_api_describe = api_sub.add_parser("describe", help="Describe one public symbol.")
    p_api_describe.add_argument("symbol", help="Dotted name like 'ModelBuilder' or 'geometry.GeoType'.")
    p_api_describe.add_argument("--json", action="store_true", dest="json_mode")
    p_api_describe.set_defaults(func=cmd_api_describe)

    # model
    p_model = sub.add_parser("model", help="Build / inspect Newton models.")
    model_sub = p_model.add_subparsers(dest="subcommand", metavar="<subcommand>")
    p_model_build = model_sub.add_parser("build", help="Build a model from a recipe JSON.")
    p_model_build.add_argument("--recipe", required=True, help="Path to recipe JSON.")
    p_model_build.add_argument("--out", required=True, help="Path to write the materialized model file (recipe copy).")
    p_model_build.add_argument("--device", default=None, help="Warp device override (cpu / cuda:0).")
    p_model_build.add_argument("--json", action="store_true", dest="json_mode")
    p_model_build.set_defaults(func=cmd_model_build)

    # sim
    p_sim = sub.add_parser("sim", help="Run a simulation.")
    sim_sub = p_sim.add_subparsers(dest="subcommand", metavar="<subcommand>")
    p_sim_run = sim_sub.add_parser("run", help="Run the standard step loop on a model.")
    p_sim_run.add_argument("--model", required=True, help="Path to a model file.")
    p_sim_run.add_argument("--solver", required=True, help="Solver class name from newton.solvers (e.g. SolverXPBD).")
    p_sim_run.add_argument(
        "--solver-arg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        dest="solver_args",
        help="Solver constructor kwarg as key=value. Repeatable. Values are coerced bool/int/float/str.",
    )
    p_sim_run.add_argument("--num-frames", type=int, default=100)
    p_sim_run.add_argument("--fps", type=float, default=100.0)
    p_sim_run.add_argument("--substeps", type=int, default=10)
    p_sim_run.add_argument("--device", default=None)
    p_sim_run.add_argument("--out", required=True, help="Path to write the final state .npz.")
    p_sim_run.add_argument("--json", action="store_true", dest="json_mode")
    p_sim_run.set_defaults(func=cmd_sim_run)

    # viewer
    p_viewer = sub.add_parser("viewer", help="Render scenes via Newton's OpenGL viewer.")
    viewer_sub = p_viewer.add_subparsers(dest="subcommand", metavar="<subcommand>")
    p_viewer_render = viewer_sub.add_parser(
        "render",
        help="Render the final state of a (model, state) pair to a PNG (headless GL).",
    )
    p_viewer_render.add_argument("--model", required=True, help="Path to the recipe/model JSON.")
    p_viewer_render.add_argument("--state", required=True, help="Path to the .npz state file.")
    p_viewer_render.add_argument("--out", required=True, help="Path to write the PNG.")
    p_viewer_render.add_argument("--width", type=int, default=1280)
    p_viewer_render.add_argument("--height", type=int, default=720)
    p_viewer_render.add_argument("--device", default="cuda:0",
        help="Warp device for model + GL interop (cuda:0 strongly recommended).")
    p_viewer_render.add_argument("--json", action="store_true", dest="json_mode")
    p_viewer_render.set_defaults(func=cmd_viewer_render)

    # run-script
    p_runscript = sub.add_parser(
        "run-script",
        help="Execute a Python script in a subprocess (B-route escape hatch).",
    )
    p_runscript.add_argument("script", help="Path to a Python script to execute.")
    p_runscript.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Kill the script and exit 5 if it runs longer than this many seconds.",
    )
    p_runscript.add_argument(
        "--artifact-dir",
        default=None,
        help="Directory injected as NEWTON_CLI_ARTIFACT_DIR. Defaults to a temp dir alongside the script.",
    )
    p_runscript.add_argument(
        "--forward",
        action="append",
        default=[],
        metavar="ARG",
        help="Extra positional arg to forward to the script. Repeatable.",
    )
    p_runscript.add_argument("--json", action="store_true", dest="json_mode")
    p_runscript.set_defaults(func=cmd_run_script)

    # examples
    p_examples = sub.add_parser("examples", help="Run / inspect Newton examples.")
    ex_sub = p_examples.add_subparsers(dest="subcommand", metavar="<subcommand>")
    p_ex_list = ex_sub.add_parser("list", help="List built-in Newton examples.")
    p_ex_list.add_argument("--json", action="store_true", dest="json_mode")
    p_ex_list.set_defaults(func=cmd_examples_list)
    p_ex_describe = ex_sub.add_parser("describe", help="Describe one example.")
    p_ex_describe.add_argument("name")
    p_ex_describe.add_argument("--json", action="store_true", dest="json_mode")
    p_ex_describe.set_defaults(func=cmd_examples_describe)
    p_ex_run = ex_sub.add_parser(
        "run",
        help="Run a built-in Newton example. Args after `--` are forwarded.",
    )
    p_ex_run.add_argument("name")
    p_ex_run.add_argument("--json", action="store_true", dest="json_mode")
    p_ex_run.add_argument("forwarded", nargs=argparse.REMAINDER, help="Args forwarded to the example.")
    p_ex_run.set_defaults(func=cmd_examples_run)

    return parser


# ---------------------------------------------------------------------------
# command implementations
# ---------------------------------------------------------------------------

def cmd_version(args: argparse.Namespace) -> int:
    import platform  # noqa: PLC0415

    import newton  # noqa: PLC0415
    import warp  # noqa: PLC0415

    data = {
        "newton": newton.__version__,
        "warp": warp.__version__,
        "python": platform.python_version(),
        "newton_cli": cli_version,
    }
    human = (
        f"newton     {data['newton']}\n"
        f"warp       {data['warp']}\n"
        f"python     {data['python']}\n"
        f"newton-cli {data['newton_cli']}"
    )
    emit(data, json_mode=args.json_mode, human=human)
    return EXIT_OK


def cmd_devices_list(args: argparse.Namespace) -> int:
    init_warp_silently()
    import warp as wp  # noqa: PLC0415

    devices = []
    for d in wp.get_devices():
        name = str(d)
        kind = "cuda" if name.startswith("cuda") else "cpu"
        devices.append({"name": name, "kind": kind})
    human_lines = [f"{d['name']:10} {d['kind']}" for d in devices]
    emit({"devices": devices}, json_mode=args.json_mode, human="\n".join(human_lines))
    return EXIT_OK


def cmd_api_list(args: argparse.Namespace) -> int:
    try:
        symbols = list_symbols(args.module)
    except PrivateModuleError as e:
        fail(EXIT_USER_ERROR, str(e), json_mode=args.json_mode, error_code="private_module")
    payload = {"symbols": [s.to_dict() for s in symbols], "count": len(symbols)}
    human = "\n".join(f"{s.module:20} {s.kind:9} {s.name}" for s in symbols)
    emit(payload, json_mode=args.json_mode, human=human)
    return EXIT_OK


def cmd_api_describe(args: argparse.Namespace) -> int:
    if PRIVATE_MARKER in args.symbol.split("."):
        fail(
            EXIT_USER_ERROR,
            f"refusing to describe private symbol '{args.symbol}'",
            hint="newton._src is internal — only public modules are allowed.",
            json_mode=args.json_mode,
            error_code="private_module",
        )
    try:
        info = describe_symbol(args.symbol)
    except PrivateModuleError as e:
        fail(EXIT_USER_ERROR, str(e), json_mode=args.json_mode, error_code="private_module")
    except LookupError as e:
        fail(EXIT_USER_ERROR, str(e), json_mode=args.json_mode, error_code="unknown_symbol")
    human = (
        f"{info['module']}.{info['name']}  ({info['kind']})\n"
        f"signature: {info['signature']}\n\n"
        f"{info['doc']}"
    )
    emit(info, json_mode=args.json_mode, human=human)
    return EXIT_OK


def cmd_model_build(args: argparse.Namespace) -> int:
    import json as _json  # noqa: PLC0415
    import shutil  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    from newton_cli.recipes import RecipeError, build_model_from_recipe  # noqa: PLC0415

    recipe_path = Path(args.recipe)
    out_path = Path(args.out)
    if not recipe_path.exists():
        fail(EXIT_USER_ERROR, f"recipe not found: {recipe_path}", json_mode=args.json_mode)

    # Validate by actually building the model. We don't keep it around — sim run
    # will rebuild from the recipe — but this catches recipe errors at build time.
    try:
        model = build_model_from_recipe(recipe_path, device=args.device)
    except RecipeError as e:
        fail(EXIT_USER_ERROR, f"recipe error: {e}", json_mode=args.json_mode, error_code="recipe_error")
    except Exception as e:  # noqa: BLE001
        fail(EXIT_RUNTIME_ERROR, f"{type(e).__name__}: {e}", json_mode=args.json_mode)

    # The "model file" is just a copy of the recipe. The recipe IS the model.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(recipe_path, out_path)

    info = {
        "model_path": str(out_path),
        "body_count": int(model.body_count),
        "joint_count": int(model.joint_count),
        "shape_count": int(model.shape_count),
        "articulation_count": int(model.articulation_count),
    }
    emit(info, json_mode=args.json_mode, human=_json.dumps(info, indent=2))
    return EXIT_OK


def cmd_sim_run(args: argparse.Namespace) -> int:
    from pathlib import Path  # noqa: PLC0415

    import warp as wp  # noqa: PLC0415

    from newton_cli.recipes import RecipeError, build_model_from_recipe  # noqa: PLC0415
    from newton_cli.sim import parse_solver_args, run_simulation  # noqa: PLC0415
    from newton_cli.state_io import save_state_npz  # noqa: PLC0415

    model_path = Path(args.model)
    out_path = Path(args.out)
    if not model_path.exists():
        fail(EXIT_USER_ERROR, f"model not found: {model_path}", json_mode=args.json_mode)

    device_ctx = wp.ScopedDevice(args.device) if args.device else _nullctx()
    try:
        with device_ctx:
            try:
                model = build_model_from_recipe(model_path, device=args.device)
            except RecipeError as e:
                fail(EXIT_USER_ERROR, f"recipe error: {e}", json_mode=args.json_mode, error_code="recipe_error")
            try:
                try:
                    solver_kwargs = parse_solver_args(args.solver_args)
                except ValueError as e:
                    fail(EXIT_USER_ERROR, str(e), json_mode=args.json_mode)
                final_state = run_simulation(
                    model,
                    solver_name=args.solver,
                    num_frames=args.num_frames,
                    fps=args.fps,
                    substeps=args.substeps,
                    solver_kwargs=solver_kwargs,
                )
            except ValueError as e:
                fail(EXIT_USER_ERROR, str(e), json_mode=args.json_mode)
            except Exception as e:  # noqa: BLE001
                fail(EXIT_RUNTIME_ERROR, f"{type(e).__name__}: {e}", json_mode=args.json_mode)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            save_state_npz(final_state, out_path)
    finally:
        pass

    info = {
        "state_path": str(out_path),
        "num_frames": args.num_frames,
        "fps": args.fps,
        "substeps": args.substeps,
        "solver": args.solver,
    }
    emit(info, json_mode=args.json_mode, human=f"sim run ok → {out_path}")
    return EXIT_OK


import contextlib as _contextlib  # noqa: E402


@_contextlib.contextmanager
def _nullctx():
    yield


def cmd_viewer_render(args: argparse.Namespace) -> int:
    from pathlib import Path  # noqa: PLC0415

    model_path = Path(args.model)
    state_path = Path(args.state)
    if not model_path.exists():
        fail(EXIT_USER_ERROR, f"model not found: {model_path}", json_mode=args.json_mode)
    if not state_path.exists():
        fail(EXIT_USER_ERROR, f"state not found: {state_path}", json_mode=args.json_mode)

    try:
        from newton_cli.render import render_state_to_png  # noqa: PLC0415
    except ImportError as e:
        fail(
            4,
            f"viewer render requires pyglet + imgui_bundle: {e}",
            hint="uv pip install 'pyglet>=2.1.6,<3' imgui_bundle",
            json_mode=args.json_mode,
            error_code="missing_dependency",
        )

    try:
        info = render_state_to_png(
            model_path=model_path,
            state_path=state_path,
            out_path=args.out,
            width=args.width,
            height=args.height,
            device=args.device,
        )
    except Exception as e:  # noqa: BLE001
        fail(EXIT_RUNTIME_ERROR, f"{type(e).__name__}: {e}", json_mode=args.json_mode)

    emit(
        info,
        json_mode=args.json_mode,
        human=f"rendered {info['width']}x{info['height']} PNG -> {info['out_path']}",
    )
    return EXIT_OK


def cmd_run_script(args: argparse.Namespace) -> int:
    """B-route escape hatch: execute a Python script in a subprocess.

    The script runs under the same Python interpreter as the CLI (so it sees
    the project venv). We inject an artifact directory the script can dump
    files into; on exit we list everything in that directory.

    Exit codes:
        0  script exited 0
        2  --script doesn't exist
        3  script exited non-zero (script-side runtime error)
        5  script timed out (--timeout exceeded)
    """
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    import time  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    script_path = Path(args.script)
    if not script_path.exists():
        fail(
            EXIT_USER_ERROR,
            f"script not found: {script_path}",
            json_mode=args.json_mode,
        )
    # Always pass an absolute script path to subprocess so the cwd override
    # below doesn't double-up with a relative argv path.
    script_path = script_path.resolve()

    # Resolve / create artifact dir. Always pass an *absolute* path to the
    # subprocess so the cwd override below doesn't make it ambiguous.
    if args.artifact_dir:
        artifact_dir = Path(args.artifact_dir).resolve()
        artifact_dir.mkdir(parents=True, exist_ok=True)
        cleanup_dir = False
    else:
        artifact_dir = Path(tempfile.mkdtemp(prefix="newton_cli_artifacts_")).resolve()
        cleanup_dir = False  # leave it on disk so the caller can fish things out

    env = os.environ.copy()
    env["NEWTON_CLI_ARTIFACT_DIR"] = str(artifact_dir)

    cmd = [sys.executable, str(script_path), *list(args.forward or [])]
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
            cwd=str(script_path.parent.resolve()),
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        duration = time.monotonic() - started
        fail(
            EXIT_TIMEOUT,
            f"script timed out after {args.timeout}s",
            hint=f"partial stdout: {(e.stdout or '')[:200]}",
            json_mode=args.json_mode,
        )

    duration = time.monotonic() - started
    stdout_lines = (proc.stdout or "").splitlines()
    stderr_lines = (proc.stderr or "").splitlines()

    # Collect artifacts.
    artifacts = []
    if artifact_dir.exists():
        for f in sorted(artifact_dir.rglob("*")):
            if f.is_file():
                artifacts.append({
                    "path": str(f.resolve()),
                    "size": f.stat().st_size,
                })

    payload = {
        "exit_code": int(proc.returncode),
        "duration_s": round(duration, 4),
        "stdout_lines": stdout_lines,
        "stderr_lines": stderr_lines,
        "artifact_dir": str(artifact_dir.resolve()),
        "artifacts": artifacts,
    }

    if proc.returncode != 0:
        # Surface as runtime error but still emit the structured envelope so
        # the caller can read stderr_lines for diagnosis.
        if args.json_mode:
            sys.stdout.write(
                __import__("json").dumps({"schema": "newton-cli/v1", "data": payload})
            )
            sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            sys.stdout.write(f"script exited {proc.returncode} after {duration:.2f}s\n")
            if stderr_lines:
                sys.stdout.write("--- stderr ---\n" + "\n".join(stderr_lines) + "\n")
        return EXIT_RUNTIME_ERROR

    emit(
        payload,
        json_mode=args.json_mode,
        human=f"script ok in {duration:.2f}s ({len(artifacts)} artifacts under {artifact_dir})",
    )
    return EXIT_OK


def cmd_examples_list(args: argparse.Namespace) -> int:
    import newton.examples as ex  # noqa: PLC0415

    examples = [
        {"name": name, "module": module}
        for name, module in ex.get_examples().items()
    ]
    human = "\n".join(e["name"] for e in examples)
    emit({"examples": examples, "count": len(examples)}, json_mode=args.json_mode, human=human)
    return EXIT_OK


def cmd_examples_describe(args: argparse.Namespace) -> int:
    import importlib  # noqa: PLC0415
    import inspect  # noqa: PLC0415

    import newton.examples as ex  # noqa: PLC0415

    examples = ex.get_examples()
    if args.name not in examples:
        fail(
            EXIT_USER_ERROR,
            f"unknown example '{args.name}'",
            hint=f"see `newton-cli examples list` for valid names ({len(examples)} available)",
            json_mode=args.json_mode,
            error_code="unknown_example",
        )

    module_path = examples[args.name]
    try:
        module = importlib.import_module(module_path)
    except Exception as e:  # pragma: no cover - defensive
        fail(EXIT_RUNTIME_ERROR, f"failed to import example module: {e}", json_mode=args.json_mode)

    # Find the Example class (most examples define `class Example`)
    example_cls = getattr(module, "Example", None)
    doc = inspect.getdoc(example_cls) or inspect.getdoc(module) or ""

    parser = ex.create_parser()
    flags = []
    for action in parser._actions:
        if not action.option_strings:
            continue
        if action.option_strings == ["-h", "--help"]:
            continue
        flags.append(
            {
                "name": action.option_strings[0],
                "aliases": action.option_strings[1:],
                "dest": action.dest,
                "default": action.default,
                "help": action.help or "",
                "kind": type(action).__name__,
            }
        )

    info = {"name": args.name, "module": module_path, "doc": doc, "flags": flags}
    human = f"{args.name}  ({module_path})\n\n{doc}\n\nflags:\n" + "\n".join(
        f"  {f['name']}  {f['help']}" for f in flags
    )
    emit(info, json_mode=args.json_mode, human=human)
    return EXIT_OK


def cmd_examples_run(args: argparse.Namespace) -> int:
    """Forward to newton.examples.main with sys.argv rewritten."""
    import newton.examples as ex  # noqa: PLC0415

    examples = ex.get_examples()
    if args.name not in examples:
        fail(
            EXIT_USER_ERROR,
            f"unknown example '{args.name}'",
            json_mode=args.json_mode,
            error_code="unknown_example",
        )

    forwarded = list(args.forwarded or [])
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    saved_argv = sys.argv
    sys.argv = ["newton.examples", args.name, *forwarded]
    try:
        ex.main()
    except SystemExit as e:
        # newton.examples.main calls sys.exit on usage errors; treat 0 as success.
        code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
        if code != 0:
            fail(EXIT_RUNTIME_ERROR, f"example exited with code {code}", json_mode=args.json_mode)
    except Exception as e:
        fail(EXIT_RUNTIME_ERROR, f"example raised {type(e).__name__}: {e}", json_mode=args.json_mode)
    finally:
        sys.argv = saved_argv

    emit({"name": args.name, "status": "ok"}, json_mode=args.json_mode, human=f"example {args.name} ok")
    return EXIT_OK


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return EXIT_USER_ERROR
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
