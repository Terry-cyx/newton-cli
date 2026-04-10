"""Simulation runner — wraps the standard Newton step loop.

This is the same loop every Newton example uses:

    for substep in range(substeps):
        state.clear_forces()
        model.collide(state, contacts)
        solver.step(state_in, state_out, control, contacts, dt)
        state_in, state_out = state_out, state_in

We do NOT capture a CUDA graph here — graph capture is an optional speedup
that examples opt into; the CLI's first-principles loop is the explicit one.
"""

from __future__ import annotations

import warp as wp

import newton


def resolve_solver(name: str) -> type:
    """Look up a solver class on `newton.solvers` by name."""
    cls = getattr(newton.solvers, name, None)
    if cls is None or not isinstance(cls, type):
        raise ValueError(
            f"unknown solver '{name}'. Available: "
            f"{', '.join(sorted(n for n in dir(newton.solvers) if n.startswith('Solver') and n != 'SolverBase'))}"
        )
    return cls


def parse_solver_args(pairs: list[str] | None) -> dict:
    """Parse repeated `key=value` strings into a typed kwargs dict.

    Values are coerced bool > int > float > str (in that priority order) so
    that `iterations=10` becomes int(10), `enable_restitution=true` becomes
    True, and unrecognized strings stay as strings.
    """
    out: dict = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"--solver-arg must be key=value, got {pair!r}")
        k, _, v = pair.partition("=")
        out[k.strip()] = _coerce_scalar(v.strip())
    return out


def _coerce_scalar(v: str):
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _instantiate_solver(solver_cls, model, solver_kwargs):
    """Construct a solver instance, auto-wrapping kwargs into a Config object
    if the solver's ctor requires one (e.g. SolverImplicitMPM)."""
    import inspect  # noqa: PLC0415

    kwargs = dict(solver_kwargs or {})
    sig = inspect.signature(solver_cls.__init__)
    params = sig.parameters
    has_config_param = "config" in params and params["config"].default is inspect.Parameter.empty
    if has_config_param and hasattr(solver_cls, "Config"):
        config = solver_cls.Config()
        for k, v in kwargs.items():
            if hasattr(config, k):
                setattr(config, k, v)
            else:
                raise ValueError(
                    f"{solver_cls.__name__}.Config has no field '{k}'"
                )
        return solver_cls(model, config=config)
    return solver_cls(model, **kwargs)


def run_simulation(
    model: newton.Model,
    *,
    solver_name: str,
    num_frames: int,
    fps: float,
    substeps: int,
    solver_kwargs: dict | None = None,
) -> newton.State:
    """Run the standard Newton step loop and return the final State."""
    solver_cls = resolve_solver(solver_name)
    solver = _instantiate_solver(solver_cls, model, solver_kwargs)

    # Seed the model's own body_q from its joint_q FIRST. State allocations
    # below will inherit those values. Examples typically do this — if we
    # only seed state_in, model.body_q stays stale and downstream reads
    # (e.g. collision-pipeline reference frames) see the wrong pose.
    newton.eval_fk(model, model.joint_q, model.joint_qd, model)

    state_in = model.state()
    state_out = model.state()
    control = model.control()
    contacts = model.contacts()

    frame_dt = 1.0 / float(fps)
    sim_dt = frame_dt / substeps

    # MPM and particle-based solvers that implement `project_outside` need an
    # extra projection pass per substep to push particles out of colliders.
    has_project_outside = hasattr(solver, "project_outside")

    for _frame in range(num_frames):
        for _ in range(substeps):
            state_in.clear_forces()
            model.collide(state_in, contacts)
            solver.step(state_in, state_out, control, contacts, sim_dt)
            if has_project_outside:
                solver.project_outside(state_out, state_out, sim_dt)
            state_in, state_out = state_out, state_in

    # Make sure host-side reads see the final values.
    wp.synchronize()
    return state_in
