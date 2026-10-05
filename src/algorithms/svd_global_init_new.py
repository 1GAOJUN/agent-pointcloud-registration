"""全局刚体初值估计工具（SVD 交叉协方差法，全新独立实现）。

输入输出统一接口：
    estimate_global_init(source_pcd, target_pcd) -> dict
输出 dict 至少包含：
    transform: 4x4 刚体变换矩阵（source -> target 坐标系）
    fitness:   初值对齐后 source 点到 target 最近点的近似 fitness（0~1）
    rmse:      初值对齐后 source 点到 target 最近点的均方根距离
    elapsed_s: 算法耗时（秒）

算法说明：
    - 对 source/target 各取子集（固化随机种子）做质心中心化；
    - 计算交叉协方差矩阵 N = (S - c_s)^T @ (T - c_t)；
    - SVD: N = U @ diag(S) @ V^T；
    - 旋转 R = V @ diag(1, 1, det(V^T U)) @ U^T；
    - 平移 t = c_t - R @ c_s；
    - 合成 T = [[R, t], [0, 1]]。
    对干净（无 outlier/无 noise）数据可直接给出极精确的刚体初值，
    使后续 ICP 快速收敛。

参数固化（写死）：
    sample_seed    = 202
    sample_ratio   = 0.5   （取 50% 点做 SVD，兼顾速度与精度）
    stat_corr_dist = 0.1   （fitness/rmse 统计阈值）
"""

from __future__ import annotations

import time
from typing import Dict, Optional

import numpy as np
import open3d as o3d

SAMPLE_SEED: int = 202
SAMPLE_RATIO: float = 0.5
STAT_CORR_DIST: float = 0.1


def _subsample(pcd, ratio: float, seed: int):
    """以固定随机种子对点云做子采样（无放回），返回子集点云。"""
    rng = np.random.RandomState(seed)
    n = len(pcd.points)
    k = int(n * ratio)
    idx = rng.choice(n, size=k, replace=False)
    return pcd.select_by_index(idx)


def _nearest_neighbor_stats(pcd_a, pcd_b, max_dist: float):
    """批量统计 pcd_a 每点到 pcd_b 最近邻距离的 fitness / rmse。"""
    dists = np.asarray(
        o3d.pipelines.registration.compute_point_cloud_distance(pcd_a, pcd_b, max_dist)
    ) if hasattr(o3d.pipelines.registration, "compute_point_cloud_distance") else None
    if dists is None:
        kdt = o3d.geometry.KDTreeFlann(pcd_b)
        pts = np.asarray(pcd_a.points)
        out = np.empty((len(pts),))
        for j in range(len(pts)):
            _, idx, d2 = kdt.search_vector_3d(
                np.array(pts[j], dtype=np.float64).reshape(3, 1),
                o3d.geometry.KDTreeSearchParamHybrid(radius=max_dist, max_nn=1))
            out[j] = np.sqrt(d2[0]) if len(d2) > 0 else max_dist
        dists = out
    inliers = dists < max_dist
    n_in = int(inliers.sum())
    fitness = n_in / len(dists)
    rmse = float(np.sqrt((dists[inliers] ** 2).mean())) if n_in > 0 else float(dists.mean())
    return fitness, rmse


def estimate_global_init(source_pcd, target_pcd,
                         T_init: Optional[np.ndarray] = None) -> Dict:
    """估计 source -> target 的全局刚体初值。

    Args:
        source_pcd: 源点云（o3d.geometry.PointCloud）。
        target_pcd: 目标点云（o3d.geometry.PointCloud）。
        T_init:     可选，若提供则直接透传该矩阵（供调用方固定初值使用）。

    Returns:
        dict:
            transform   (np.ndarray, 4x4)
            fitness     (float, 0~1)
            rmse        (float)
            elapsed_s   (float)
    """
    if T_init is not None:
        return {
            "transform": np.asarray(T_init, dtype=np.float64),
            "fitness": 0.0,
            "rmse": 0.0,
            "elapsed_s": 0.0,
        }

    t0 = time.perf_counter()

    src_sub = _subsample(source_pcd, SAMPLE_RATIO, SAMPLE_SEED)
    tgt_sub = _subsample(target_pcd, SAMPLE_RATIO, SAMPLE_SEED)

    S = np.asarray(src_sub.points, dtype=np.float64)
    T = np.asarray(tgt_sub.points, dtype=np.float64)

    c_s = S.mean(axis=0)
    c_t = T.mean(axis=0)

    N = (S - c_s).T @ (T - c_t)
    U, _, Vt = np.linalg.svd(N)
    d = np.linalg.det(Vt.T @ U.T)
    Dm = np.diag([1.0, 1.0, d])
    R = Vt.T @ Dm @ U.T

    t = c_t - R @ c_s
    T_svd = np.eye(4, dtype=np.float64)
    T_svd[:3, :3] = R
    T_svd[:3, 3] = t

    # 统计对齐后的 fitness / rmse：对 source 全量点施加 T_svd，统计到 target 距离
    src_pts = np.asarray(source_pcd.points) @ R.T + t
    src_transformed = o3d.geometry.PointCloud()
    src_transformed.points = o3d.utility.Vector3dVector(src_pts)
    fitness, rmse = _nearest_neighbor_stats(src_transformed, target_pcd, STAT_CORR_DIST)

    elapsed_s = time.perf_counter() - t0
    return {
        "transform": T_svd,
        "fitness": fitness,
        "rmse": rmse,
        "elapsed_s": elapsed_s,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    l2_dir = root / "outputs" / "L2"
    src = o3d.io.read_point_cloud(str(l2_dir / "source.ply"))
    tgt = o3d.io.read_point_cloud(str(l2_dir / "target.ply"))
    out = estimate_global_init(src, tgt)
    report = {
        "method": "svd_cross_covariance_global_init",
        "transform": out["transform"].tolist(),
        "fitness": out["fitness"],
        "rmse": out["rmse"],
        "elapsed_s": out["elapsed_s"],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

