"""Shape-aware visualization helper for CLI-run examples.

Usage:
    python visualize.py <state.npz> <snapshot.png> <summary.txt>
                        [--model <recipe_or_model.json>]
                        [--title "..."]

If `--model` (or an auto-discovered `model.json` sibling of `state.npz`)
is available, rebuilds the Model to obtain shape type + dimensions, then
draws each shape at its world pose as a matplotlib 3D wireframe primitive.
Falls back to a body-origin scatter plot if no model is given.

Supported shapes:
  BOX (7)       — 12-edge wireframe
  SPHERE (3)    — 2 latitude rings
  ELLIPSOID (5) — 2 latitude rings with per-axis radii
  CAPSULE (4)   — cylinder body + 2 end-caps
  CYLINDER (6)  — top + bottom circles + side verticals
  CONE (9)      — base circle + apex lines
  PLANE (1)     — drawn as a large ground quad on z=0
  MESH (8), CONVEX_MESH (10), HFIELD (2) — shown as bounding-box fallback
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # offscreen
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402


# ---------------------------------------------------------------------------
# Shape primitives: each returns a list of line segments in LOCAL space.
# A segment is a pair of 3D points. We transform segments to world space
# and hand them to Line3DCollection.
# ---------------------------------------------------------------------------

def _box_segments(hx: float, hy: float, hz: float) -> list[tuple[np.ndarray, np.ndarray]]:
    v = np.array([
        [-hx, -hy, -hz], [+hx, -hy, -hz], [+hx, +hy, -hz], [-hx, +hy, -hz],
        [-hx, -hy, +hz], [+hx, -hy, +hz], [+hx, +hy, +hz], [-hx, +hy, +hz],
    ])
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    return [(v[a], v[b]) for a, b in edges]


def _circle(radius_x: float, radius_y: float, z: float, n: int = 24) -> np.ndarray:
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([radius_x * np.cos(t), radius_y * np.sin(t), np.full_like(t, z)], axis=1)


def _ring_segments(pts: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    n = len(pts)
    return [(pts[i], pts[(i + 1) % n]) for i in range(n)]


def _sphere_segments(radius: float) -> list[tuple[np.ndarray, np.ndarray]]:
    segs: list[tuple[np.ndarray, np.ndarray]] = []
    # equator + two longitudes (cheap wireframe)
    segs += _ring_segments(_circle(radius, radius, 0.0, n=20))
    half_pi_pts = np.stack([
        radius * np.cos(np.linspace(0, 2 * math.pi, 20, endpoint=False)),
        np.zeros(20),
        radius * np.sin(np.linspace(0, 2 * math.pi, 20, endpoint=False)),
    ], axis=1)
    segs += _ring_segments(half_pi_pts)
    other = np.stack([
        np.zeros(20),
        radius * np.cos(np.linspace(0, 2 * math.pi, 20, endpoint=False)),
        radius * np.sin(np.linspace(0, 2 * math.pi, 20, endpoint=False)),
    ], axis=1)
    segs += _ring_segments(other)
    return segs


def _ellipsoid_segments(rx: float, ry: float, rz: float) -> list[tuple[np.ndarray, np.ndarray]]:
    # XY equator
    segs = _ring_segments(_circle(rx, ry, 0.0, n=24))
    # XZ ring
    t = np.linspace(0, 2 * math.pi, 20, endpoint=False)
    xz = np.stack([rx * np.cos(t), np.zeros(20), rz * np.sin(t)], axis=1)
    segs += _ring_segments(xz)
    yz = np.stack([np.zeros(20), ry * np.cos(t), rz * np.sin(t)], axis=1)
    segs += _ring_segments(yz)
    return segs


def _cylinder_segments(radius: float, half_height: float) -> list[tuple[np.ndarray, np.ndarray]]:
    top = _circle(radius, radius, +half_height, n=20)
    bot = _circle(radius, radius, -half_height, n=20)
    segs = _ring_segments(top) + _ring_segments(bot)
    # 6 vertical lines
    for i in range(0, 20, 20 // 6):
        segs.append((top[i], bot[i]))
    return segs


def _capsule_segments(radius: float, half_height: float) -> list[tuple[np.ndarray, np.ndarray]]:
    # cylinder body (Newton's capsule uses X-axis as the long axis in local frame — verify later;
    # for now use Z-axis as in our basic examples)
    segs = _cylinder_segments(radius, half_height)
    # Two hemispheres via shifted sphere rings (approximate)
    for sign, cz in ((+1, +half_height), (-1, -half_height)):
        t = np.linspace(0, 2 * math.pi, 20, endpoint=False)
        ring = np.stack([
            radius * np.cos(t),
            np.zeros(20),
            cz + sign * 0.5 * radius * np.sin(t),
        ], axis=1)
        segs += _ring_segments(ring)
    return segs


def _cone_segments(radius: float, half_height: float) -> list[tuple[np.ndarray, np.ndarray]]:
    base = _circle(radius, radius, -half_height, n=20)
    apex = np.array([0.0, 0.0, +half_height])
    segs = _ring_segments(base)
    for i in range(0, 20, 20 // 8):
        segs.append((base[i], apex))
    return segs


def _mesh_bbox_segments(bbox_half: float = 0.15) -> list[tuple[np.ndarray, np.ndarray]]:
    return _box_segments(bbox_half, bbox_half, bbox_half)


# GeoType constants (from newton.GeoType)
TYPE_NONE, TYPE_PLANE, TYPE_HFIELD, TYPE_SPHERE = 0, 1, 2, 3
TYPE_CAPSULE, TYPE_ELLIPSOID, TYPE_CYLINDER, TYPE_BOX = 4, 5, 6, 7
TYPE_MESH, TYPE_CONE, TYPE_CONVEX_MESH = 8, 9, 10


def _segments_for_shape(shape_type: int, scale: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    sx, sy, sz = float(scale[0]), float(scale[1]), float(scale[2])
    if shape_type == TYPE_BOX:
        return _box_segments(sx, sy, sz)
    if shape_type == TYPE_SPHERE:
        return _sphere_segments(sx)
    if shape_type == TYPE_ELLIPSOID:
        return _ellipsoid_segments(sx, sy, sz)
    if shape_type == TYPE_CAPSULE:
        # Newton capsule: scale[0]=radius, scale[1]=half_height (approximate)
        return _capsule_segments(sx, sy)
    if shape_type == TYPE_CYLINDER:
        return _cylinder_segments(sx, sy)
    if shape_type == TYPE_CONE:
        return _cone_segments(sx, sy)
    if shape_type in (TYPE_MESH, TYPE_CONVEX_MESH):
        return _mesh_bbox_segments()
    # plane / hfield / none → no local segments (handled separately)
    return []


# ---------------------------------------------------------------------------
# Pose math (quaternion rotation, xyzw convention to match Newton)
# ---------------------------------------------------------------------------

def _quat_rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    x, y, z, w = q
    # v' = v + 2w(q_vec × v) + 2(q_vec × (q_vec × v))
    q_vec = np.array([x, y, z])
    t = 2.0 * np.cross(q_vec, v)
    return v + w * t + np.cross(q_vec, t)


def _transform(pose: np.ndarray, local: np.ndarray) -> np.ndarray:
    return _quat_rotate(pose[3:7], local) + pose[0:3]


def _compose(pose_a: np.ndarray, pose_b: np.ndarray) -> np.ndarray:
    # world = a * b, applied to points as transform(a, transform(b, p)).
    p = _quat_rotate(pose_a[3:7], pose_b[0:3]) + pose_a[0:3]
    # q = q_a * q_b (xyzw)
    ax, ay, az, aw = pose_a[3:7]
    bx, by, bz, bw = pose_b[3:7]
    qx = aw * bx + ax * bw + ay * bz - az * by
    qy = aw * by - ax * bz + ay * bw + az * bx
    qz = aw * bz + ax * by - ay * bx + az * bw
    qw = aw * bw - ax * bx - ay * by - az * bz
    return np.array([p[0], p[1], p[2], qx, qy, qz, qw])


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _gather_shapes(model) -> list[dict]:
    """Pull shape info out of a finalized Newton Model."""
    out = []
    n = int(model.shape_count)
    if n == 0:
        return out
    shape_body = model.shape_body.numpy()
    shape_type = model.shape_type.numpy()
    shape_scale = model.shape_scale.numpy()
    shape_transform = model.shape_transform.numpy()
    for i in range(n):
        out.append({
            "type": int(shape_type[i]),
            "body": int(shape_body[i]),  # -1 means world / static
            "scale": shape_scale[i],
            "local_pose": shape_transform[i],
        })
    return out


def _plot_scene(
    body_q: np.ndarray | None,
    particle_q: np.ndarray | None,
    shapes: list[dict],
    out_path: Path,
    title: str,
) -> None:
    fig = plt.figure(figsize=(15, 5.5))
    fig.suptitle(title, fontsize=12)

    ax3d = fig.add_subplot(1, 3, 1, projection="3d")
    ax_xz = fig.add_subplot(1, 3, 2)
    ax_yz = fig.add_subplot(1, 3, 3)

    ax3d.set_title("3D scene")
    ax_xz.set_title("XZ projection")
    ax_yz.set_title("YZ projection")

    all_pts: list[np.ndarray] = []

    # ---- draw shapes (if we have them) ----
    segs_3d: list[np.ndarray] = []
    segs_xz: list[np.ndarray] = []
    segs_yz: list[np.ndarray] = []

    for shape in shapes:
        body_idx = shape["body"]
        if body_idx >= 0 and body_q is not None and body_idx < body_q.shape[0]:
            body_pose = body_q[body_idx]
        else:
            # static / world shape
            body_pose = np.array([0, 0, 0, 0, 0, 0, 1], dtype=float)

        world_pose = _compose(body_pose, shape["local_pose"])

        if shape["type"] == TYPE_PLANE:
            # huge ground quad, handled separately
            continue

        local_segs = _segments_for_shape(shape["type"], shape["scale"])
        if not local_segs:
            continue

        for a_local, b_local in local_segs:
            a_world = _transform(world_pose, np.asarray(a_local, dtype=float))
            b_world = _transform(world_pose, np.asarray(b_local, dtype=float))
            segs_3d.append(np.stack([a_world, b_world]))
            segs_xz.append(np.array([[a_world[0], a_world[2]], [b_world[0], b_world[2]]]))
            segs_yz.append(np.array([[a_world[1], a_world[2]], [b_world[1], b_world[2]]]))
            all_pts.append(a_world)
            all_pts.append(b_world)

    if segs_3d:
        ax3d.add_collection3d(Line3DCollection(segs_3d, colors="tab:blue", linewidths=0.9))
        from matplotlib.collections import LineCollection  # noqa: PLC0415
        ax_xz.add_collection(LineCollection(segs_xz, colors="tab:blue", linewidths=0.9))
        ax_yz.add_collection(LineCollection(segs_yz, colors="tab:blue", linewidths=0.9))

    # ---- draw body origins as small markers (always useful) ----
    if body_q is not None and body_q.shape[0] > 0:
        bp = body_q[:, :3]
        ax3d.scatter(bp[:, 0], bp[:, 1], bp[:, 2], c="tab:red", s=12, alpha=0.9, label="body origins")
        ax_xz.scatter(bp[:, 0], bp[:, 2], c="tab:red", s=12, alpha=0.9, label="body origins")
        ax_yz.scatter(bp[:, 1], bp[:, 2], c="tab:red", s=12, alpha=0.9, label="body origins")
        all_pts.extend(bp)

    # ---- draw particles (soft bodies / cloth) ----
    if particle_q is not None and particle_q.shape[0] > 0:
        pp = particle_q[:, :3]
        ax3d.scatter(pp[:, 0], pp[:, 1], pp[:, 2], c="tab:orange", s=3, alpha=0.5, label="particles")
        ax_xz.scatter(pp[:, 0], pp[:, 2], c="tab:orange", s=3, alpha=0.5, label="particles")
        ax_yz.scatter(pp[:, 1], pp[:, 2], c="tab:orange", s=3, alpha=0.5, label="particles")
        all_pts.extend(pp)

    # ---- ground reference line at z=0 ----
    for ax, xlabel in ((ax_xz, "x [m]"), (ax_yz, "y [m]")):
        ax.axhline(0.0, color="gray", linewidth=0.8, linestyle="--", label="z=0 (ground)")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=7)

    ax3d.set_xlabel("x"); ax3d.set_ylabel("y"); ax3d.set_zlabel("z")

    # auto-fit 3D axis
    if all_pts:
        pts = np.asarray(all_pts)
        lo, hi = pts.min(axis=0) - 0.2, pts.max(axis=0) + 0.2
        rng = (hi - lo).max()
        cx, cy, cz = 0.5 * (lo + hi)
        ax3d.set_xlim(cx - rng / 2, cx + rng / 2)
        ax3d.set_ylim(cy - rng / 2, cy + rng / 2)
        ax3d.set_zlim(cz - rng / 2, cz + rng / 2)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def _summarize(state: dict, shape_count: int | None) -> str:
    lines = ["=== newton-cli state summary ===", ""]
    if "body_q" in state:
        bq = state["body_q"]
        bqd = state.get("body_qd")
        lines.append(f"bodies:    {bq.shape[0]}")
        if shape_count is not None:
            lines.append(f"shapes:    {shape_count}")
        lines.append(f"  position bbox  x=[{bq[:,0].min():+7.3f}, {bq[:,0].max():+7.3f}]  "
                     f"y=[{bq[:,1].min():+7.3f}, {bq[:,1].max():+7.3f}]  "
                     f"z=[{bq[:,2].min():+7.3f}, {bq[:,2].max():+7.3f}]")
        if bqd is not None:
            lines.append(f"  max |body_qd|  {np.abs(bqd).max():.4f}")
    if "particle_q" in state:
        pq = state["particle_q"]
        pqd = state.get("particle_qd")
        lines.append(f"particles: {pq.shape[0]}")
        lines.append(f"  position bbox  x=[{pq[:,0].min():+7.3f}, {pq[:,0].max():+7.3f}]  "
                     f"y=[{pq[:,1].min():+7.3f}, {pq[:,1].max():+7.3f}]  "
                     f"z=[{pq[:,2].min():+7.3f}, {pq[:,2].max():+7.3f}]")
        if pqd is not None:
            lines.append(f"  max |particle_qd|  {np.abs(pqd).max():.4f}")

    if "body_q" in state and state["body_q"].shape[0] > 0:
        lines.append("")
        lines.append("first bodies (index: [px py pz] | [qx qy qz qw]):")
        bq = state["body_q"]
        for i in range(min(8, bq.shape[0])):
            row = bq[i]
            lines.append(
                f"  {i:3d}: [{row[0]:+7.3f} {row[1]:+7.3f} {row[2]:+7.3f}] | "
                f"[{row[3]:+6.3f} {row[4]:+6.3f} {row[5]:+6.3f} {row[6]:+6.3f}]"
            )
        if bq.shape[0] > 8:
            lines.append(f"  ... ({bq.shape[0] - 8} more)")

    for key in ("body_q", "body_qd", "particle_q", "particle_qd"):
        if key in state:
            arr = state[key]
            total = arr.size
            finite = int(np.isfinite(arr).sum())
            if finite != total:
                lines.append(f"  WARN: {key} has {total - finite} non-finite values")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_path")
    parser.add_argument("snapshot_path")
    parser.add_argument("summary_path")
    parser.add_argument("--model", default=None,
        help="Path to the recipe/model JSON. If omitted, looks for model.json next to the state.")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    state_path = Path(args.state_path)
    snapshot_path = Path(args.snapshot_path)
    summary_path = Path(args.summary_path)

    if not state_path.exists():
        print(f"ERROR: state file not found: {state_path}", file=sys.stderr)
        return 1

    with np.load(state_path) as data:
        state = {k: data[k] for k in data.files}

    # Try to load a recipe/model next to the state so we can draw real shapes.
    model_path = Path(args.model) if args.model else (state_path.parent / "model.json")
    shapes: list[dict] = []
    if model_path.exists():
        try:
            from newton_cli.recipes import build_model_from_recipe  # noqa: PLC0415

            model = build_model_from_recipe(model_path, device="cpu")
            shapes = _gather_shapes(model)
        except Exception as e:  # noqa: BLE001
            print(f"[visualize] could not load model for shape info: {e}", file=sys.stderr)
            shapes = []
    else:
        print(f"[visualize] no model.json next to state; falling back to body-origin scatter",
              file=sys.stderr)

    body_q = state.get("body_q")
    particle_q = state.get("particle_q")

    title = args.title or state_path.stem
    if shapes:
        title += f"  ({len(shapes)} shapes, {body_q.shape[0] if body_q is not None else 0} bodies)"

    _plot_scene(body_q, particle_q, shapes, snapshot_path, title)

    summary = _summarize(state, len(shapes) if shapes else None)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"[visualize] wrote {snapshot_path}")
    print(f"[visualize] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
