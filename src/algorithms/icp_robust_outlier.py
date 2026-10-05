"""鲁棒点到面 ICP 配准工具（针对含离群点 + 高斯噪声的脏数据场景，如 L3）。

在点到面 ICP 之前，对 source/target 先做统计学离群点剔除
（Statistical Outlier Removal），降低离群点对最小二乘拟合的拉偏影响。

- 参数全部固化；调用前 np.random.seed(SEED) 显式固定随机种子。
- 输入：source_ply, target_ply
- 输出 dict：transform(4x4), fitness, rmse, elapsed_sec
- 只含算法逻辑，不含判断/调度/策略。

运行（独立自检，直接读 outputs/ICP/L3 数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\algorithms\icp_robust_outlier.py
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

# ---------------------------------------------------------------------------
# 固化参数
# ---------------------------------------------------------------------------
SEED: int = 42
NORMAL_RADIUS: float = 0.05
NORMAL_MAX_NN: int = 30

# 统计学离群点剔除：每个点的近邻平均距离与全局平均距离的偏离度超过 N_STD 倍标准差则剔除
SOR_N_NEIGHBORS: int = 30
SOR_STD_RATIO: float = 1.0

# ICP 参数（与 icp_naive 一致，保持可比）
ICP_DISTANCE_THRESHOLD: float = 0.04
ICP_MAX_ITERATION: int = 100
ICP_RELATIVE_FITNESS: float = 1e-6
ICP_RELATIVE_RMSE: float = 1e-6


def icp_robust_outlier(source_ply: str, target_ply: str) -> Dict[str, object]:
    """统计离群点剔除 + 单位阵初值点到面 ICP。返回 transform/fitness/rmse/elapsed_sec。"""
    np.random.seed(SEED)

    source = o3d.io.read_point_cloud(source_ply)
    target = o3d.io.read_point_cloud(target_ply)
    if source is None or target is None:
        raise ValueError(f"无法读取点云：{source_ply} / {target_ply}")

    # 剔除离群点（含 8% 随机离群点的目标点云，以及任何可能的源点云离群点）
    source, _ = source.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)
    target, _ = target.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)

    search_param = o3d.geometry.KDTreeSearchParamHybrid(radius=NORMAL_RADIUS, max_nn=NORMAL_MAX_NN)
    source.estimate_normals(search_param=search_param)
    target.estimate_normals(search_param=search_param)

    t0 = time.perf_counter()
    icp = reg.registration_icp(
        source,
        target,
        ICP_DISTANCE_THRESHOLD,
        np.eye(4),
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
        "elapsed_sec": elapsed,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    l3 = root / "outputs" / "ICP" / "L3"
    res = icp_robust_outlier(str(l3 / "source.ply"), str(l3 / "target.ply"))
    print("=" * 60)
    print("icp_robust_outlier.py 自检（L3 统计离群点剔除 + 点到面 ICP）")
    print(f"fitness   = {res['fitness']:.6f}")
    print(f"rmse      = {res['rmse']:.6f}")
    print(f"elapsed   = {res['elapsed_sec']:.2f} s")
    print("transform:\n" + np.array2string(res["transform"], precision=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

