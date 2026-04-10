"""Headless OpenGL rendering via newton.viewer.ViewerGL.

Produces PNG snapshots from a (recipe, state) pair. Uses Newton's own GL
viewer in headless mode so the output visually matches what you'd see
running `python -m newton.examples <name>` with the default viewer.

Heavy imports (pyglet / imgui_bundle / newton.viewer) are deferred to the
call site so the CLI's default code path stays headless-clean.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from newton_cli.recipes import build_model_from_recipe
from newton_cli.state_io import load_state_npz_into


def _replicas_have_physical_spacing(model, state) -> bool:
    """Return True if state.body_q already spreads replicas in world space.

    Computes per-world centroids from shape_world + body positions and
    checks if any two centroids differ by more than a small threshold.
    """
    import numpy as _np  # noqa: PLC0415

    bq = getattr(state, "body_q", None)
    if bq is None:
        return False
    bq_np = bq.numpy()
    if bq_np.shape[0] == 0:
        return False

    world_count = int(getattr(model, "world_count", 1))
    if world_count <= 1:
        return False

    # Map shapes -> worlds -> attached body -> body positions
    try:
        shape_world = model.shape_world.numpy()
        shape_body = model.shape_body.numpy()
    except Exception:  # noqa: BLE001
        return False

    centroids: dict[int, list] = {}
    for sidx in range(len(shape_world)):
        w = int(shape_world[sidx])
        b = int(shape_body[sidx])
        if w < 0 or b < 0 or b >= bq_np.shape[0]:
            continue
        centroids.setdefault(w, []).append(bq_np[b, :3])

    if len(centroids) < 2:
        return False
    means = _np.stack([_np.mean(_np.stack(pts), axis=0) for pts in centroids.values()])
    # If any pair of world centroids differs by > 0.1 m, physical spacing is present.
    diffs = _np.linalg.norm(means[:, None, :] - means[None, :, :], axis=-1)
    return bool((diffs > 0.1).any())


def _fit_camera_to_scene(viewer, state, model=None) -> None:
    """Point Newton's ViewerGL camera at whatever is actually in the scene.

    Newton's camera uses yaw/pitch (not look-at). For Z-up, front direction is
        front = (cos(yaw)*cos(pitch), sin(yaw)*cos(pitch), sin(pitch))
    so given a desired look vector D = center - cam_pos we compute
        yaw   = atan2(D_y, D_x)
        pitch = asin(D_z / |D|)
    """
    import math  # noqa: PLC0415

    import numpy as _np  # noqa: PLC0415
    import warp as wp  # noqa: PLC0415

    pts = []
    bq = getattr(state, "body_q", None)
    if bq is not None:
        bq_np = bq.numpy() if isinstance(bq, wp.array) else bq
        if bq_np.shape[0] > 0:
            pts.append(bq_np[:, :3])
    pq = getattr(state, "particle_q", None)
    if pq is not None:
        pq_np = pq.numpy() if isinstance(pq, wp.array) else pq
        if pq_np.shape[0] > 0:
            pts.append(pq_np[:, :3])

    if not pts:
        return  # nothing to frame

    all_pts = _np.concatenate(pts, axis=0)

    # If the viewer is applying its own world_offsets layout (case b above),
    # the rendered replicas won't be at their state.body_q positions — they'll
    # be offset by world_index * spacing. Expand the bbox accordingly so
    # the camera still frames everything that will actually render.
    world_offsets = getattr(viewer, "world_offsets", None)
    world_count = int(getattr(model, "world_count", 1)) if model is not None else 1
    if world_offsets is not None and world_count > 1:
        try:
            wo = _np.asarray([float(v) for v in world_offsets], dtype=float)
            if _np.linalg.norm(wo) > 1e-9:
                # Viewer grid layout: replicas spread on a 2D square grid
                # perpendicular to the up axis, spacing=wo for each step.
                side = int(_np.ceil(_np.sqrt(world_count)))
                grid_pts = []
                for w in range(world_count):
                    gx, gy = divmod(w, side)
                    offset = _np.array([gx * wo[0], gy * wo[1], w * wo[2]])
                    # shift all_pts by offset and concatenate
                    grid_pts.append(all_pts + offset)
                all_pts = _np.concatenate(grid_pts, axis=0)
        except Exception:  # noqa: BLE001
            pass

    lo = all_pts.min(axis=0)
    hi = all_pts.max(axis=0)
    center = 0.5 * (lo + hi)
    extent_xyz = hi - lo
    # Use the horizontal diagonal as "how wide is the scene"; add a z cushion.
    horizontal = float(_np.linalg.norm(extent_xyz[:2]))
    vertical = float(extent_xyz[2])
    span = max(horizontal, vertical * 1.5, 2.0)

    # Place camera on a 3/4 perspective: offset +X, -Y, +Z relative to center.
    # Distance scales with fov=45° → half-angle 22.5° → needs dist > span / tan(22.5°) ≈ 2.41*span
    # We pick 2.2 * span which slightly under-frames → subject fills ~85% of view.
    distance = span * 2.2
    offset = _np.array([distance * 0.7, -distance * 0.7, distance * 0.45])
    cam_pos_np = center + offset
    cam_pos = wp.vec3(float(cam_pos_np[0]), float(cam_pos_np[1]), float(cam_pos_np[2]))

    # Compute yaw/pitch to look at center (Z-up convention).
    look = center - cam_pos_np
    ln = _np.linalg.norm(look)
    if ln < 1e-6:
        return
    look = look / ln
    yaw_rad = math.atan2(look[1], look[0])
    pitch_rad = math.asin(max(-1.0, min(1.0, look[2])))
    yaw = math.degrees(yaw_rad)
    pitch = math.degrees(pitch_rad)

    viewer.set_camera(pos=cam_pos, pitch=pitch, yaw=yaw)


def render_state_to_png(
    model_path: str | Path,
    state_path: str | Path,
    out_path: str | Path,
    *,
    width: int = 1280,
    height: int = 720,
    device: str = "cuda:0",
) -> dict:
    """Render the final state of a model to a PNG via headless ViewerGL.

    Args:
        model_path: Path to the recipe/model JSON (the "model file" IS the recipe).
        state_path: Path to the .npz state file written by `sim run`.
        out_path: PNG output path.
        width: Render width in pixels.
        height: Render height in pixels.
        device: Warp device ('cuda:0' strongly recommended for GL interop).

    Returns:
        A dict with metadata (shape, out_path, body_count, ...) suitable for
        JSON emission.
    """
    import warp as wp  # noqa: PLC0415

    import newton.viewer as vw  # noqa: PLC0415

    model_path = Path(model_path)
    state_path = Path(state_path)
    out_path = Path(out_path)

    with wp.ScopedDevice(device):
        model = build_model_from_recipe(model_path, device=device)
        state = model.state()
        load_state_npz_into(state, state_path)

        viewer = vw.ViewerGL(width=width, height=height, headless=True)
        try:
            viewer.set_model(model)

            # Show particles by default — MPM scenes otherwise render only
            # the colliders with nothing where the particles should be.
            if hasattr(viewer, "show_particles"):
                viewer.show_particles = True

            # Decide whether the recipe already baked physical spacing into
            # the replicas. Two cases:
            #  (a) recipe did `replicate(..., spacing=[...])` — replica
            #      centroids in state.body_q differ — viewer's auto-layout
            #      would double-count. Zero out viewer world_offsets.
            #  (b) recipe used add_world(...) or replicate with zero spacing —
            #      replica centroids overlap. Let the viewer's default auto
            #      layout spread them visually (otherwise robots render on
            #      top of each other).
            if _replicas_have_physical_spacing(model, state):
                viewer.set_world_offsets((0.0, 0.0, 0.0))

            # Auto-fit the camera based on the scene's body/particle bounding
            # box (after any viewer-side world_offsets layout has been decided).
            _fit_camera_to_scene(viewer, state, model)

            # Sim_time=0 — we're rendering a still frame of the final state.
            viewer.begin_frame(0.0)
            viewer.log_state(state)
            viewer.end_frame()

            frame = viewer.get_frame()
            img = frame.numpy()
        finally:
            viewer.close()

    # Newton's ViewerGL.get_frame() returns the framebuffer already in
    # top-left origin (empirically verified with a simple pendulum scene),
    # so NO manual vertical flip is needed. Earlier versions of this file
    # had a double-flip that made every render come out upside-down.
    if img.dtype != np.uint8:
        img = np.clip(img * 255.0, 0, 255).astype(np.uint8)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write via Pillow (already installed as a matplotlib transitive dep).
    from PIL import Image  # noqa: PLC0415

    Image.fromarray(img).save(out_path)

    return {
        "out_path": str(out_path),
        "width": int(img.shape[1]),
        "height": int(img.shape[0]),
        "channels": int(img.shape[2]) if img.ndim == 3 else 1,
        "body_count": int(model.body_count),
        "shape_count": int(model.shape_count),
    }
