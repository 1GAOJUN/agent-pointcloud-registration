"""鲁棒 FPFH+RANSAC 全局粗配准 + 点到面 ICP 精化工具（针对含高斯噪声 + 离群点的脏数据场景，如 L3）。

在 L2 版 global_registration.py 的基础上：
- 配准前先做统计学离群点剔除，降低离群点对特征提取和 RANSAC 匹配的影响；
- 将 RANSAC 最大对应点距离阈值放宽（脏数据真实表面局部尺度比干净数据大）。

参数全部固化；调用前 np.random.seed(SEED) 显式固定随机种子。
- 输入：source_ply, target_ply
- 输出 dict：transform(4x4), fitness, rmse, ransac_fitness, ransac_rmse, elapsed_sec
- 只含算法逻辑，不含判断/调度/策略。

运行（独立自检，直接读 outputs/ICP/L3 数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\algorithms\global_registration_robust.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

# ---------------------------------------------------------------------------
# 固化参数（针对 L3：中等角度旋转 + 高斯噪声σ=0.004 + 8%离群点）
# ---------------------------------------------------------------------------
SEED: int = 42

NORMAL_RADIUS: float = 0.05
NORMAL_MAX_NN: int = 30

SOR_N_NEIGHBORS: int = 30
SOR_STD_RATIO: float = 1.0

FPFH_NUM_KEYPOINTS: int = 500
FPFH_SEARCH_RADIUS: float = 0.5
FPFH_MAX_NN: int = 30

# 关键区别：L2 版为 0.1（干净数据），L3 脏数据需放宽，避免有效匹配点过少导致 RANSAC 退化
RANSAC_MAX_CORRESPONDENCE_DISTANCE: float = 0.5
RANSAC_MUTUAL_FILTER: bool = True

ICP_DISTANCE_THRESHOLD: float = 0.04
ICP_MAX_ITERATION: int = 100
ICP_RELATIVE_FITNESS: float = 1e-6
ICP_RELATIVE_RMSE: float = 1e-6


def _load_and_clean(ply_path: str) -> o3d.geometry.PointCloud:
    pcd = o3d.io.read_point_cloud(ply_path)
    if pcd is None:
        raise ValueError(f"无法读取点云：{ply_path}")
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
        radius=NORMAL_RADIUS, max_nn=NORMAL_MAX_NN))
    return pcd


def _fpfh_index_subsample(n_points: int, n_keypoints: int) -> List[int]:
    if n_points <= 0:
        return []
    n_keypoints = min(n_keypoints, n_points)
    step = max(1, n_points // n_keypoints)
    return list(range(0, n_points, step))[:n_keypoints]


def global_registration_robust(source_ply: str, target_ply: str) -> Dict[str, object]:
    """统计离群点剔除 + FPFH + RANSAC 全局粗配准 + 点到面 ICP 精化。"""
    np.random.seed(SEED)

    source = _load_and_clean(source_ply)
    target = _load_and_clean(target_ply)

    search = o3d.geometry.KDTreeSearchParamHybrid(radius=FPFH_SEARCH_RADIUS, max_nn=FPFH_MAX_NN)
    src_idx = _fpfh_index_subsample(len(source.points), FPFH_NUM_KEYPOINTS)
    tgt_idx = _fpfh_index_subsample(len(target.points), FPFH_NUM_KEYPOINTS)
    source_fpfh = reg.compute_fpfh_feature(source, search, src_idx)
    target_fpfh = reg.compute_fpfh_feature(target, search, tgt_idx)

    ransac = reg.registration_ransac_based_on_feature_matching(
        source,
        target,
        source_fpfh,
        target_fpfh,
        mutual_filter=RANSAC_MUTUAL_FILTER,
        max_correspondence_distance=RANSAC_MAX_CORRESPONDENCE_DISTANCE,
    )

    icp = reg.registration_icp(
        source,
        target,
        ICP_DISTANCE_THRESHOLD,
        np.asarray(ransac.transformation, dtype=np.float64),
        estimation_method=reg.TransformationEstimationPointToPlane(),
        criteria=reg.ICPConvergenceCriteria(
            max_iteration=ICP_MAX_ITERATION,
            relative_fitness=ICP_RELATIVE_FITNESS,
            relative_rmse=ICP_RELATIVE_RMSE,
        ),
    )

    t_elapsed = time.perf_counter() - _T0
    return {
        "transform": np.asarray(icp.transformation, dtype=np.float64),
        "fitness": float(icp.fitness),
        "rmse": float(icp.inlier_rmse),
        "ransac_fitness": float(ransac.fitness),
        "ransac_rmse": float(ransac.inlier_rmse),
        "elapsed_sec": t_elapsed,
    }


_T0 = time.perf_counter()


def main(argv: list) -> int:
    global _T0
    root = Path(__file__).resolve().parents[2]
    l3_dir = root / "outputs" / "ICP" / "L3"
    source_ply = str(l3_dir / "source.ply")
    target_ply = str(l3_dir / "target.ply")
    _T0 = time.perf_counter()
    res = global_registration_robust(source_ply, target_ply)
    print("=" * 60)
    print("global_registration_robust.py 自检（L3 离群点剔除 + FPFH + RANSAC + ICP）")
    print(f"ransac_fitness = {res['ransac_fitness']:.4f}  ransac_rmse    = {res['ransac_rmse']:.6f}")
    print(f"icp_fitness    = {res['fitness']:.4f}  icp_rmse       = {res['rmse']:.6f}")
    print(f"elapsed_sec    = {res['elapsed_sec']:.2f}")
    print("transform:\n" + np.array2string(res["transform"], precision=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
