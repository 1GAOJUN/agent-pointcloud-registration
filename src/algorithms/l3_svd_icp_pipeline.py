"""L3 型场景（中等角度旋转 + 高斯噪声 + 离群点）配准工具。

流程：统计离群点剔除 → SVD 交叉协方差全局初值 → 点到面 ICP 精化。
组合调用已有工具 svd_global_init_new.estimate_global_init 与 icp_naive_new.register。

- 参数全部固化；调用前 np.random.seed(SEED) 显式固定随机种子。
- 输入：source_ply, target_ply
- 输出 dict：transform(4x4), fitness, rmse, svd_fitness, svd_rmse, elapsed_sec
- 只含算法逻辑，不含判断/调度/策略。

运行（独立自检，直接读 outputs/ICP/L3 数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\algorithms\l3_svd_icp_pipeline.py
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

import numpy as np
import open3d as o3d

from src.algorithms.icp_naive_new import register
from src.algorithms.svd_global_init_new import estimate_global_init

# ---------------------------------------------------------------------------
# 固化参数（针对 L3：中等角度旋转 + 高斯噪声σ=0.004 + 8%离群点）
# ---------------------------------------------------------------------------
SEED: int = 42

SOR_N_NEIGHBORS: int = 30
SOR_STD_RATIO: float = 1.0

NORMAL_RADIUS: float = 0.05
NORMAL_MAX_NN: int = 30


def l3_svd_icp(source_ply: str, target_ply: str) -> Dict[str, object]:
    """离群点剔除 + SVD全局初值 + 点到面ICP精化。返回统一结果dict。"""
    np.random.seed(SEED)

    source = o3d.io.read_point_cloud(source_ply)
    target = o3d.io.read_point_cloud(target_ply)
    if source is None or target is None:
        raise ValueError(f"无法读取点云：{source_ply} / {target_ply}")

    source, _ = source.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)
    target, _ = target.remove_statistical_outlier(nb_neighbors=SOR_N_NEIGHBORS, std_ratio=SOR_STD_RATIO)

    t0 = time.perf_counter()
    svd = estimate_global_init(source, target)
    T_init = svd["transform"]

    icp = register(source, target, T_init)
    elapsed = time.perf_counter() - t0

    return {
        "transform": np.asarray(icp["transform"], dtype=np.float64),
        "fitness": float(icp["fitness"]),
        "rmse": float(icp["rmse"]),
        "svd_fitness": float(svd["fitness"]),
        "svd_rmse": float(svd["rmse"]),
        "elapsed_sec": elapsed,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    l3 = root / "outputs" / "ICP" / "L3"
    res = l3_svd_icp(str(l3 / "source.ply"), str(l3 / "target.ply"))
    print("=" * 60)
    print("l3_svd_icp_pipeline.py 自检（L3 离群点剔除 + SVD全局初值 + ICP精化）")
    print(f"svd_fitness = {res['svd_fitness']:.4f}  svd_rmse    = {res['svd_rmse']:.6f}")
    print(f"icp_fitness = {res['fitness']:.4f}  icp_rmse    = {res['rmse']:.6f}")
    print(f"elapsed     = {res['elapsed_sec']:.2f} s")
    print("transform:\n" + np.array2string(res["transform"], precision=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
