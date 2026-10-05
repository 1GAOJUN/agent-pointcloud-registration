"""L2 大角度场景全局粗配准算法模块。

方案：FPFH 特征匹配 + RANSAC 全局粗配准 + 点到面 ICP 精化。
- 仅新增文件，不修改任何已有核心模块（make_data / evaluate / run_benchmark）。
- 只依赖 open3d==0.20.0 与 numpy，参数全部硬编码以保证可复现。
- 适配 Open3D 0.20 API：
    * registration_icp 返回 RegistrationResult（含 fitness / inlier_rmse / transformation）
    * compute_fpfh_feature(pcd, search_param, indices) 直接对全点云取均匀索引子集计算
    * registration_ransac_based_on_feature_matching(source, target, sf, tf, mutual_filter, ...)
    * 法向量仅用 estimate_normals（0.20 已移除 estimate_normals_for_slicing）

运行（可独立验证，直接读 outputs/ICP/L2 已有数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\algorithms\global_registration.py
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
# 硬编码参数（Open3D 0.20 最佳实践，针对 30k 点、球+盒+柱不对称拼接体）
# ---------------------------------------------------------------------------

# 法向量估计（KDTree 半径 + 最大邻域数；半径匹配点云局部特征尺度）
NORMAL_RADIUS: float = 0.05
NORMAL_MAX_NN: int = 30

# FPFH 计算：均匀子集关键点个数（球+盒+柱细节丰富，500 个足够覆盖）
FPFH_NUM_KEYPOINTS: int = 500
# FPFH 局部搜索半径（覆盖局部邻域，点云尺度 ~0.5）
FPFH_SEARCH_RADIUS: float = 0.5
FPFH_MAX_NN: int = 30

# RANSAC 特征匹配全局配准
RANSAC_MAX_CORRESPONDENCE_DISTANCE: float = 0.1  # 内点判定距离（点云尺度）
RANSAC_MUTUAL_FILTER: bool = True                 # 互近邻过滤，剔除误匹配

# ICP 精化（与基线一致的点到面法 + 收敛准则，仅初值不同）
ICP_DISTANCE_THRESHOLD: float = 0.04
ICP_MAX_ITERATION: int = 100
ICP_RELATIVE_FITNESS: float = 1e-6
ICP_RELATIVE_RMSE: float = 1e-6


def _load_pointcloud(ply_path: str) -> o3d.geometry.PointCloud:
    """读取 PLY 点云。缺失时抛异常。"""
    if not Path(ply_path).exists():
        raise FileNotFoundError(f"点云文件不存在：{ply_path}")
    pcd = o3d.io.read_point_cloud(ply_path)
    if pcd is None:
        raise ValueError(f"无法读取点云：{ply_path}")
    return pcd


def _estimate_normals(pcd: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
    """估计法向量（FPFH 与点到面 ICP 都依赖法向量；与基线一致用 KDTree 半径）。"""
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=NORMAL_RADIUS, max_nn=NORMAL_MAX_NN
        )
    )
    return pcd


def _fpfh_index_subsample(n_points: int, n_keypoints: int) -> List[int]:
    """全点云均匀取 n_keypoints 个索引作为 FPFH 计算关键点。"""
    if n_points <= 0:
        return []
    n_keypoints = min(n_keypoints, n_points)
    step = max(1, n_points // n_keypoints)
    return list(range(0, n_points, step))[:n_keypoints]


def _extract_fpfh(pcd: o3d.geometry.PointCloud):
    """提取均匀子集索引与 FPFH 描述子（Open3D 0.20 compute_fpfh_feature）。"""
    indices = _fpfh_index_subsample(len(pcd.points), FPFH_NUM_KEYPOINTS)
    search = o3d.geometry.KDTreeSearchParamHybrid(
        radius=FPFH_SEARCH_RADIUS, max_nn=FPFH_MAX_NN
    )
    fpfh = reg.compute_fpfh_feature(pcd, search, indices)
    return indices, fpfh


def global_registration(
    source_ply: str,
    target_ply: str,
) -> Dict[str, object]:
    """FPFH + RANSAC 粗配准 + 点到面 ICP 精化。

    Args:
        source_ply: 源点云路径。
        target_ply: 目标点云路径。
    Returns:
        dict，含：
            transform        4x4 np.ndarray（source→target）
            fitness          ICP 精化后拟合比例
            rmse             ICP 精化后残差均方根（inlier_rmse）
            ransac_fitness   RANSAC 粗配准拟合比例
            ransac_rmse      RANSAC 粗配准残差均方根
            elapsed_sec      总耗时（秒）
    """
    t0 = time.perf_counter()

    source = _load_pointcloud(source_ply)
    target = _load_pointcloud(target_ply)
    source = _estimate_normals(source)
    target = _estimate_normals(target)

    # 1. FPFH 特征
    _src_idx, source_fpfh = _extract_fpfh(source)
    _tgt_idx, target_fpfh = _extract_fpfh(target)

    # 2. RANSAC 特征匹配 → 全局粗配准（source→target）
    ransac = reg.registration_ransac_based_on_feature_matching(
        source,
        target,
        source_fpfh,
        target_fpfh,
        mutual_filter=RANSAC_MUTUAL_FILTER,
        max_correspondence_distance=RANSAC_MAX_CORRESPONDENCE_DISTANCE,
    )

    # 3. ICP 精化：以 RANSAC 粗变换为初值
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

    elapsed = time.perf_counter() - t0
    return {
        "transform": np.asarray(icp.transformation, dtype=np.float64),
        "fitness": float(icp.fitness),
        "rmse": float(icp.inlier_rmse),
        "ransac_fitness": float(ransac.fitness),
        "ransac_rmse": float(ransac.inlier_rmse),
        "elapsed_sec": elapsed,
    }


def main(argv: list) -> int:
    """独立入口：读 outputs/ICP/L2 已有数据，打印配准结果。"""
    root = Path(__file__).resolve().parents[2]
    l2_dir = root / "outputs" / "ICP" / "L2"
    source_ply = str(l2_dir / "source.ply")
    target_ply = str(l2_dir / "target.ply")

    if not Path(source_ply).exists() or not Path(target_ply).exists():
        print(f"[FAIL] 缺少 L2 点云数据：{l2_dir}")
        print("      请先运行 src/run_benchmark.py 生成 outputs/ICP/L2。")
        return 1

    res = global_registration(source_ply, target_ply)
    T = res["transform"]
    print("=" * 60)
    print("global_registration.py 自检（L2 FPFH+RANSAC+ICP）")
    print("=" * 60)
    print(f"ransac_fitness = {res['ransac_fitness']:.4f}  "
          f"ransac_rmse    = {res['ransac_rmse']:.6f}")
    print(f"icp_fitness    = {res['fitness']:.4f}  "
          f"icp_rmse       = {res['rmse']:.6f}")
    print(f"elapsed_sec    = {res['elapsed_sec']:.2f}")
    print("transform:\n" + np.array2string(T, precision=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
