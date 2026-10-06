"""Agent 配准工具注册表 + 可参数化包装器（GT-free，无场景/关卡分支）。

设计原则：
- 所有工具入口只接收 source/target 点云（或 PLY 路径）+ Agent 选择的参数倍率，
  绝不读取 gt_transform、场景标签、level。
- 每个工具描述 purpose / applicable_conditions / required_inputs /
  adjustable_parameters / returned_metrics / known_limitations。
- 参数自适应：Agent 不写绝对值，而是选择相对诊断尺度的倍率。
  base_scale = 诊断得到的代表尺度；actual = base_scale * scale。

工具清单（本轮提供给 Agent 的通用候选，EXPERIMENT_ONLY 的 SVD 不提供给 Agent）：
  LOCAL_ICP            - 单位阵初值点到面 ICP，低成本；适用小角度/干净/重叠高。
  GLOBAL_FPFH_RANSAC_ICP - SOR+FPFH+RANSAC 全局初值 + 点到面 ICP；高成本；适用大角度/脏数据。

SVD_ICP 标记 EXPERIMENT_ONLY：依赖“干净且完全重叠、可用全点集当对应源”的前提，
现实未知输入不保证成立，故不提供给 Agent 作通用候选。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import open3d as o3d

# ---------------------------------------------------------------------------
# 工具注册表（静态元数据，供 Prompt 展示，非可执行对象）
# ---------------------------------------------------------------------------
TOOL_REGISTRY: List[Dict[str, Any]] = [
    {
        "tool_name": "LOCAL_ICP",
        "purpose": "单位阵初值的点到面 ICP。低成本、快。",
        "applicable_conditions": "旋转角度较小、数据干净、source 与 target 重叠高、尺度接近。",
        "required_inputs": ["source.ply", "target.ply"],
        "adjustable_parameters": ["icp_max_corr_scale"],
        "returned_metrics": ["transform", "fitness", "rmse", "inlier_rmse", "elapsed_s"],
        "known_limitations": "初值只能单位阵；大角度/脏数据/低重叠下发散或局部最优。",
    },
    {
        "tool_name": "GLOBAL_FPFH_RANSAC_ICP",
        "purpose": "统计离群剔除 + FPFH + RANSAC 全局配准，再点到面 ICP。高成本、鲁棒。",
        "applicable_conditions": "大角度、脏数据（噪声/离群）、重叠较低、或 LOCAL_ICP 失败时的补救。",
        "required_inputs": ["source.ply", "target.ply"],
        "adjustable_parameters": ["global_corr_scale", "icp_max_corr_scale"],
        "returned_metrics": ["transform", "fitness", "rmse", "ransac_fitness", "ransac_rmse", "elapsed_s"],
        "known_limitations": "耗时高；对完全干净且小角度数据可能不必要；对极低重叠仍有限。",
    },
    {
        "tool_name": "SVD_ICP",
        "status": "EXPERIMENT_ONLY",
        "purpose": "SVD 交叉协方差全局初值（干净且完全重叠时极准）。",
        "excluded_from_agent": True,
        "reason_excluded": "依赖现实中不可保证的“干净且完全重叠”前提，不作为通用 Agent 候选。",
    },
]


def _ensure_normals(pcd: o3d.geometry.PointCloud, search_radius: float, max_nn: int = 30) -> None:
    if not pcd.has_normals():
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=search_radius, max_nn=max_nn)
        )


def _load(ply: str) -> o3d.geometry.PointCloud:
    pcd = o3d.io.read_point_cloud(ply)
    if pcd is None:
        raise ValueError(f"无法读取点云: {ply}")
    return pcd


def run_local_icp(source_ply: str, target_ply: str,
                  icp_max_corr_scale: float = 1.0,
                  base_scale: float = 0.1,
                  n_iter: int = 100) -> Dict[str, Any]:
    """LOCAL_ICP：单位阵初值点到面 ICP。
    参数：icp_max_corr_scale 相对 base_scale（诊断尺度）放大对应点距离阈值。
    返回 GT-free 指标。
    """
    max_corr = max(1e-4, float(base_scale) * float(icp_max_corr_scale))
    source = _load(source_ply)
    target = _load(target_ply)
    _ensure_normals(source, search_radius=max_corr * 1.5)
    _ensure_normals(target, search_radius=max_corr * 1.5)

    import time
    t0 = time.perf_counter()
    est = o3d.pipelines.registration.TransformationEstimationPointToPlane()
    crit = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-6, relative_rmse=1e-8, max_iteration=n_iter,
    )
    res = o3d.pipelines.registration.registration_icp(
        source, target, max_corr, np.eye(4),
        estimation_method=est, criteria=crit,
    )
    elapsed = time.perf_counter() - t0
    T = np.asarray(res.transformation, dtype=np.float64)
    return {
        "transform": T,
        "fitness": float(res.fitness),
        "rmse": float(res.inlier_rmse),
        "inlier_rmse": float(res.inlier_rmse),
        "elapsed_s": float(elapsed),
        "max_correspondence_distance": float(max_corr),
    }


def run_global_fpfh_ransac_icp(source_ply: str, target_ply: str,
                               global_corr_scale: float = 5.0,
                               icp_max_corr_scale: float = 1.0,
                               base_scale: float = 0.1) -> Dict[str, Any]:
    """GLOBAL_FPFH_RANSAC_ICP：SOR+FPFH+RANSAC 全局初值 + 点到面 ICP。
    复用 global_registration_robust 的逻辑，但把 RANSAC/ICP 对应距离阈值改为
    相对诊断尺度 base_scale 的倍率（global_corr_scale / icp_max_corr_scale）。
    返回 GT-free 指标。
    """
    import time
    np.random.seed(42)
    t0 = time.perf_counter()

    source = _load(source_ply)
    target = _load(target_ply)
    source, _ = source.remove_statistical_outlier(nb_neighbors=30, std_ratio=1.0)
    target, _ = target.remove_statistical_outlier(nb_neighbors=30, std_ratio=1.0)

    normal_radius = max(1e-3, base_scale * 0.5)
    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=30))
    target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=30))

    import open3d.pipelines.registration as reg
    n_key = min(500, len(source.points))
    step = max(1, len(source.points) // n_key)
    src_idx = list(range(0, len(source.points), step))[:n_key]
    n_key_t = min(500, len(target.points))
    step_t = max(1, len(target.points) // n_key_t)
    tgt_idx = list(range(0, len(target.points), step_t))[:n_key_t]

    fpfh_radius = max(base_scale, 0.2)
    search = o3d.geometry.KDTreeSearchParamHybrid(radius=fpfh_radius, max_nn=30)
    src_f = reg.compute_fpfh_feature(source, search, src_idx)
    tgt_f = reg.compute_fpfh_feature(target, search, tgt_idx)

    ransac_corr = max(1e-3, float(base_scale) * float(global_corr_scale))
    ransac = reg.registration_ransac_based_on_feature_matching(
        source, target, src_f, tgt_f,
        mutual_filter=True, max_correspondence_distance=ransac_corr,
    )
    icp_corr = max(1e-4, float(base_scale) * float(icp_max_corr_scale))
    icp = reg.registration_icp(
        source, target, icp_corr,
        np.asarray(ransac.transformation, dtype=np.float64),
        estimation_method=reg.TransformationEstimationPointToPlane(),
        criteria=reg.ICPConvergenceCriteria(max_iteration=100, relative_fitness=1e-6, relative_rmse=1e-6),
    )
    elapsed = time.perf_counter() - t0
    T = np.asarray(icp.transformation, dtype=np.float64)
    return {
        "transform": T,
        "fitness": float(icp.fitness),
        "rmse": float(icp.inlier_rmse),
        "ransac_fitness": float(ransac.fitness),
        "ransac_rmse": float(ransac.inlier_rmse),
        "elapsed_s": float(elapsed),
        "ransac_max_correspondence_distance": float(ransac_corr),
        "icp_max_correspondence_distance": float(icp_corr),
    }


def dispatch(tool_name: str, source_ply: str, target_ply: str,
             base_scale: float, param_policy: Dict[str, Any]) -> Dict[str, Any]:
    """按 tool_name 分发到对应可执行工具；EXPERIMENT_ONLY/未知工具报错。"""
    if tool_name == "LOCAL_ICP":
        return run_local_icp(
            source_ply, target_ply,
            icp_max_corr_scale=param_policy.get("icp_max_corr_scale", 1.0),
            base_scale=base_scale,
        )
    if tool_name == "GLOBAL_FPFH_RANSAC_ICP":
        return run_global_fpfh_ransac_icp(
            source_ply, target_ply,
            global_corr_scale=param_policy.get("global_corr_scale", 5.0),
            icp_max_corr_scale=param_policy.get("icp_max_corr_scale", 1.0),
            base_scale=base_scale,
        )
    raise ValueError(f"未知或非 Agent 可用工具: {tool_name}")
