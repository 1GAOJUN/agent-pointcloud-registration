"""朴素点-到-面 ICP 配准工具（L2 初测基线）。

- 以单位阵为初始位姿。
- 参数全部固化；调用前 np.random.seed(SEED) 显式固定随机种子。
- 输入：source_ply, target_ply
- 输出 dict：transform(4x4), fitness, rmse, elapsed_sec
- 只含算法逻辑，不含判断/调度/策略。

运行（独立自检，直接读 outputs/ICP/L2 数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\algorithms\icp_naive.py
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
ICP_DISTANCE_THRESHOLD: float = 0.04
ICP_MAX_ITERATION: int = 100
ICP_RELATIVE_FITNESS: float = 1e-6
ICP_RELATIVE_RMSE: float = 1e-6
NORMAL_RADIUS: float = 0.05
NORMAL_MAX_NN: int = 30


def icp_naive(source_ply: str, target_ply: str) -> Dict[str, object]:
    """单位阵初值的点到面 ICP。返回 transform/fitness/rmse/elapsed_sec。"""
    np.random.seed(SEED)

    source = o3d.io.read_point_cloud(source_ply)
    target = o3d.io.read_point_cloud(target_ply)
    if source is None or target is None:
        raise ValueError(f"无法读取点云：{source_ply} / {target_ply}")

    source.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
        radius=NORMAL_RADIUS, max_nn=NORMAL_MAX_NN))
    target.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
        radius=NORMAL_RADIUS, max_nn=NORMAL_MAX_NN))

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
    l2 = root / "outputs" / "ICP" / "L2"
    res = icp_naive(str(l2 / "source.ply"), str(l2 / "target.ply"))
    print("=" * 60)
    print("icp_naive.py 自检（L2 单位阵初值，点到面 ICP）")
    print(f"fitness   = {res['fitness']:.6f}")
    print(f"rmse      = {res['rmse']:.6f}")
    print(f"elapsed   = {res['elapsed_sec']:.2f} s")
    print("transform:\n" + np.array2string(res["transform"], precision=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
