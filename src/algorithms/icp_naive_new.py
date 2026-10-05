"""朴素点到面 ICP（全新独立实现，从零封装，不依赖任何旧工具文件）。

输入输出统一接口：
    register(source_pcd, target_pcd, T_init) -> dict
输出 dict 至少包含：
    transform: 4x4 变换矩阵（np.ndarray）
    fitness:   Open3D 评估 fitness（0~1）
    rmse:      最终点到面距离（单位与点云一致）
    elapsed_s: 算法耗时（秒）

算法说明：
    - 使用 Open3D 0.20.0 的 registration_icp + TransformationEstimationPointToPlane
      （点到面变体的经典 ICP）；
    - target 需要法向（点云从 PLY 读入时不带法向），内部自动用半径搜索补法向；
    - 固定迭代次数与收敛阈值，参数全部写死，无任何随机量；
    - 不做 outlier 裁剪（L2 场景数据干净，无 outlier/noise/crop）；
    - 仅输出结果与诊断指标，不写任何策略/调度逻辑。

Open3D 0.20.0 API 注意：
    - RegistrationResult 使用 .transformation（旧版 .transform）；
    - RegistrationResult 没有 .converged 属性，用 max_iteration 判断达到上限。

参数固化（写死）：
    max_correspondence_distance = 0.1
    max_iteration               = 50
    relative_fitness            = 1e-6
    relative_rmse               = 1e-8
    normal_search_radius        = 0.15
"""

from __future__ import annotations

import time
from typing import Dict, Optional

import numpy as np
import open3d as o3d

MAX_CORR_DIST: float = 0.1
MAX_ITER: int = 50
REL_FITNESS: float = 1e-6
REL_RMSE: float = 1e-8
NORMAL_SEARCH_RADIUS: float = 0.15


def _ensure_normals(pcd, search_radius: float) -> None:
    """若点云无法向，则原地补法向（半径搜索法向估计）。"""
    if not pcd.has_normals():
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=search_radius, max_nn=30))


def register(source_pcd, target_pcd, T_init: Optional[np.ndarray] = None) -> Dict:
    """对 source/target 执行一次朴素点到面 ICP，返回结果 dict。

    注意：会原地修改 target_pcd（补法向）；如需保留原始数据请先深拷贝。

    Args:
        source_pcd: 源点云（o3d.geometry.PointCloud）。
        target_pcd: 目标点云（o3d.geometry.PointCloud）。
        T_init:     4x4 初始刚体变换矩阵。默认单位阵。

    Returns:
        dict:
            transform   (np.ndarray, 4x4)
            fitness     (float)
            inlier_rmse (float)
            rmse        (float, 同 inlier_rmse)
            elapsed_s   (float)
    """
    if T_init is None:
        T_init = np.eye(4, dtype=np.float64)
    T_init = np.asarray(T_init, dtype=np.float64)

    _ensure_normals(target_pcd, NORMAL_SEARCH_RADIUS)

    est = o3d.pipelines.registration.TransformationEstimationPointToPlane()
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=REL_FITNESS,
        relative_rmse=REL_RMSE,
        max_iteration=MAX_ITER,
    )

    t0 = time.perf_counter()
    result = o3d.pipelines.registration.registration_icp(
        source=source_pcd,
        target=target_pcd,
        max_correspondence_distance=MAX_CORR_DIST,
        init=T_init,
        estimation_method=est,
        criteria=criteria,
    )
    elapsed_s = time.perf_counter() - t0

    T_out = np.asarray(result.transformation, dtype=np.float64)
    return {
        "transform": T_out,
        "fitness": float(result.fitness),
        "inlier_rmse": float(result.inlier_rmse),
        "rmse": float(result.inlier_rmse),
        "elapsed_s": float(elapsed_s),
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    l2_dir = root / "outputs" / "L2"
    src = o3d.io.read_point_cloud(str(l2_dir / "source.ply"))
    tgt = o3d.io.read_point_cloud(str(l2_dir / "target.ply"))
    T0 = np.eye(4)

    out = register(src, tgt, T0)
    report = {
        "method": "naive_point_to_plane_icp (init=I)",
        "transform": out["transform"].tolist(),
        "fitness": out["fitness"],
        "inlier_rmse": out["inlier_rmse"],
        "elapsed_s": out["elapsed_s"],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
