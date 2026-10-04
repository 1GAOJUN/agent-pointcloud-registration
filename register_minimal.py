"""Point cloud registration minimal example (sphere + offset box, asymmetric).

Pipeline:
  1. Build an asymmetric shape (sphere + offset box) with Open3D built-in
     geometry, sample it into a point cloud ("source").
  2. Clone the source and apply a known ground-truth transform:
         R_z(15 deg) and t = [0.3, 0.1, 0.2]  ->  "target"
  3. Run ICP from the identity initialization to register source -> target.
  4. Compare the ICP-estimated transform with the ground truth and report
     rotation error (degrees) and translation error.
  5. Save one visualization screenshot (before) and one (after) to outputs/.

Run inside the conda env `pointcloud_agh` (never base):
    conda activate pointcloud_agh
    python register_minimal.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

OUT_DIR = Path(__file__).resolve().parent / "outputs"


def rotz(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [c, -s, 0.0],
        [s,  c, 0.0],
        [0.0, 0.0, 1.0],
    ])


def build_source_pointcloud() -> o3d.geometry.PointCloud:
    """Sphere + an offset box -> asymmetric shape, sampled into a point cloud."""
    sphere = o3d.geometry.TriangleMesh.create_sphere(radius=0.5)
    box = o3d.geometry.TriangleMesh.create_box(
        width=0.6, height=0.6, depth=0.6,
    ).translate([0.5, -0.4, 0.4])  # offset box => asymmetric union
    mesh = sphere + box
    mesh.remove_duplicated_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_non_manifold_edges()
    mesh.compute_vertex_normals()
    # Sample 30k points on the mesh surface, then estimate normals for ICP.
    pc = mesh.sample_points_uniformly(30000)
    pc.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
    return pc


def snapshot(source: o3d.geometry.PointCloud,
             target: o3d.geometry.PointCloud,
             source_after_icp: o3d.geometry.PointCloud,
             show_before: bool,
             path: Path) -> None:
    """Render source(+after-ICP) vs target into one view, save a PNG.

    Uses a short render pass instead of vis.run() so the script is
    non-blocking and can run in automated / headless GUI contexts.
    """
    vis = o3d.visualization.Visualizer()
    vis.create_window(width=900, height=700,
                      window_name="ICP registration" +
                                  (" (before)" if show_before else " (after)"))
    vis.add_geometry(target)
    if show_before:
        vis.add_geometry(source)
    else:
        vis.add_geometry(source_after_icp)
        vis.get_render_option().point_size = 4
    vis.capture_screen_image(str(path), do_render=True)
    vis.destroy_window()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1. Build the asymmetric source shape ----
    source_pc = build_source_pointcloud()
    print(f"source points: {len(source_pc.points)}")

    # ---- 2. Ground-truth transform: R_z(15 deg) + t = [0.3, 0.1, 0.2] ----
    gt_R = rotz(math.radians(15.0))
    gt_t = np.array([0.3, 0.1, 0.2])
    gt_T = np.eye(4)
    gt_T[:3, :3] = gt_R
    gt_T[:3, 3] = gt_t

    target_pc = o3d.geometry.PointCloud(source_pc)
    target_pc.transform(gt_T)  # target = source transformed by ground truth
    print("ground-truth transform:\n", gt_T)

    # ---- 3. ICP: register source -> target, start from identity ----
    result = reg.registration_icp(
        source_pc, target_pc,
        0.04,  # max_correspondence_distance
        np.eye(4),
        estimation_method=reg.TransformationEstimationPointToPlane(),
        criteria=reg.ICPConvergenceCriteria(
            max_iteration=100, relative_fitness=1e-6, relative_rmse=1e-6,
        ),
    )
    est_T = result.transformation
    info = result

    source_after = o3d.geometry.PointCloud(source_pc)
    source_after.transform(est_T)

    # ---- 4. Compare ICP vs ground truth ----
    est_R = est_T[:3, :3]
    est_t = est_T[:3, 3]
    dR = est_R.T @ gt_R
    rot_err = math.degrees(math.acos(np.clip(0.5 * (np.trace(dR) - 1.0),
                                              -1.0, 1.0)))
    trans_err = float(np.linalg.norm(est_t - gt_t))
    print(f"rotation error (deg)   : {rot_err:.6f}")
    print(f"translation error (m)  : {trans_err:.6f}")
    print("estimated transform:\n", est_T)

    # ---- 5. Before/after visualizations ----
    snapshot(source_pc, target_pc, source_after, True,
             OUT_DIR / "before.png")
    snapshot(source_pc, target_pc, source_after, False,
             OUT_DIR / "after.png")
    print(f"screenshots saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
