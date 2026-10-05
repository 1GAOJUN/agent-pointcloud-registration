"""多初值点到面 ICP 配准工具（中等角度旋转 + 脏数据（噪声+离群点）场景，如 L3）。

对单位阵初值施加一组固化的离散 Z 轴预旋转（0/90/180/270 度），每个初值各自
跑一次"统计离群点剔除 + 点到面 ICP"，最终取 ICP fitness 最高（并列时取 rmse 最低）
的变换作为输出。

- 参数全部固化；调用前 np.random.seed(SEED) 显式固定随机种子。
- 输入：source_ply, target_ply
- 输出 dict：transform(4x4), fitness, rmse, n_candidates, elapsed_sec
- 只含算法逻辑（取最优候选属于算法本身的输出选择，不属于判断/调度/策略）。

运行（独立自检，直接读 outputs/ICP/L3 数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\algorithms\icp_multistart.py
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

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

ICP_DISTANCE_THRESHOLD: float = 0.04
ICP_MAX_ITERATION: int = 100
ICP_RELATIVE_FITNESS: float = 1e-6
ICP_RELATIVE_RMSE: float = 1e-6

# 固化的离散 Z 轴预旋转角度（度）
PRE_ROT_Z_DEGS: tuple = (0, 90, 180, 270)


def _rot_z(deg: float) -> np.ndarray:
    r = np.deg2rad(deg)
    c, s = np.cos(r), np.sin(r)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def icp_multistart(source_ply: str, target_ply: str) -> Dict[str, object]:
    """多初值（Z轴 0/90/180/270° 预旋转）+ 统计离群点剔除 + 点到面 ICP，取最优候选。"""
    np.random.seed(SEED)

    source = o3d.io.read_point_cloud(source_ply)
    target = o3d.io.read_point_cloud(target_ply)
    if source is None or target is None:
        raise ValueError(f"无法读取点云：{source_ply} / {target_ply}")

    source, _ = source.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)
    target, _ = target.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)

    search_param = o3d.geometry.KDTreeSearchParamHybrid(radius=NORMAL_RADIUS, max_nn=NORMAL_MAX_NN)
    source.estimate_normals(search_param=search_param)
    target.estimate_normals(search_param=search_param)

    t0 = time.perf_counter()
    best = None
    for deg in PRE_ROT_Z_DEGS:
        init = np.eye(4)
        init[:3, :3] = _rot_z(deg)
        icp = reg.registration_icp(
            source,
            target,
            ICP_DISTANCE_THRESHOLD,
            init,
            estimation_method=reg.TransformationEstimationPointToPlane(),
            criteria=reg.ICPConvergenceCriteria(
                max_iteration=ICP_MAX_ITERATION,
                relative_fitness=ICP_RELATIVE_FITNESS,
                relative_rmse=ICP_RELATIVE_RMSE,
            ),
        )
        cand = {
            "deg": deg,
            "transform": np.asarray(icp.transformation, dtype=np.float64),
            "fitness": float(icp.fitness),
            "rmse": float(icp.inlier_rmse),
        }
        if best is None or cand["fitness"] > best["fitness"] or (
            cand["fitness"] == best["fitness"] and cand["rmse"] < best["rmse"]
        ):
            best = cand

    elapsed = time.perf_counter() - t0

    return {
        "transform": best["transform"],
        "fitness": best["fitness"],
        "rmse": best["rmse"],
        "n_candidates": len(PRE_ROT_Z_DEGS),
        "elapsed_sec": elapsed,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    l3 = root / "outputs" / "ICP" / "L3"
    res = icp_multistart(str(l3 / "source.ply"), str(l3 / "target.ply"))
    print("=" * 60)
    print("icp_multistart.py 自检（L3 多初值 + 离群点剔除 + 点到面 ICP）")
    print(f"fitness   = {res['fitness']:.6f}")
    print(f"rmse      = {res['rmse']:.6f}")
    print(f"candidates = {res['n_candidates']}")
    print(f"elapsed   = {res['elapsed_sec']:.2f} s")
    print("transform:\n" + np.array2string(res["transform"], precision=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
