"""Active Observation Probes（B2B — Phase B2B Active Observation Probe）。

两个 Probe 都是 Agnes 可自主调用的"观测工具"，不是配准算法，
因此独立于 agent_tools.TOOL_REGISTRY（正式配准工具）注册：

  Probe A  PCA_ORIENTATION   — 粗姿态/主轴差异估计（纯 numpy，微秒级成本）
  Probe B  CHEAP_LOCAL_ICP   — 固定低成本 LOCAL ICP（5 迭代，无 Global 初始化、无 SOR）

设计原则（与 B1 06_PROBE_PLAN / 07_ARCHITECTURE 一致）：
- Probe 只输出可观测数值指标，绝不读 gt_transform / rotation_error / translation_error / 场景标签
- Probe 不修改输入点云（numpy 视图操作；Open3D 对象为本地加载副本）
- Python 不根据任何诊断指标自动选择 Probe；是否调用、调用哪个由 Agnes 在
  decision JSON 的 requested_probe 字段中给出（白名单 + 配额校验见 agnnes_agent.py）

成本对比（L2 seed_202 实测，outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/_cost_profile.json）：
- 正式 LOCAL_ICP：max_iteration=100，ICP+normal wall ≈ 5.06 s
- CHEAP_LOCAL_ICP：max_iteration=5，wall ≈ 0.32 s（≈6% 正式成本）
- PCA_ORIENTATION：numpy 3x3 eigh，< 1 ms
"""

from __future__ import annotations

import copy
import itertools
import time
from typing import Any, Dict, List, Optional

import numpy as np

# 每 case 的 Probe 调用次数上限（合法 guardrail；顺序由 Agnes 决定，Python 不规定）
MAX_PROBES_PER_RUN = 2

PROBE_WHITELIST = ("PCA_ORIENTATION", "CHEAP_LOCAL_ICP", "NONE")

# 采样上限（与 agent_diagnose.SAMPLE_LIMIT 一致，保持诊断/Probe 采样风格统一）
_PCA_SAMPLE_LIMIT = 1000
_PCA_SEED = 101

# Cheap ICP Probe 固定参数（低成本约定；不随 Agnes 参数策略变化）
_CHEAP_ICP_MAX_ITER = 5
_CHEAP_ICP_CORR_SCALE = 2.0   # max_corr = base_scale * 2.0（与正式 LOCAL_ICP 常用档位相同，迭代数才是成本差的主因）

PROBE_REGISTRY: List[Dict[str, Any]] = [
    {
        "probe_name": "PCA_ORIENTATION",
        "tool_name": "PCA_ORIENTATION",
        "type": "probe",
        "purpose": "PCA 主轴 frame 对比，估计 source→target 的粗旋转角与主轴各向异性。低成本（微秒级）。",
        "returns": [
            "rotation_estimate_deg (float or null)",
            "orientation_confidence: HIGH|MEDIUM|LOW",
            "ambiguity_detected: bool",
            "ambiguity_reason: string or null",
            "source_anisotropy: float (λmax/λmin)",
            "target_anisotropy: float",
            "ambiguity_handling: string",
            "runtime_s: float",
        ],
        "cost": "extremely low (numpy 3x3 eigendecomposition, <1 ms on 1000-point samples)",
        "limitations": [
            "各向同性/对称/近平面/近细长点云时 orientation_confidence=LOW，rotation_estimate_deg=null",
            "输出角度是 PCA frame 相对旋转，不是逐点配准意义上的旋转误差",
            "不得据此做'角度>X 就用某算法'的固定映射，那是 Agnes 的专业判断",
        ],
    },
    {
        "probe_name": "CHEAP_LOCAL_ICP",
        "tool_name": "CHEAP_LOCAL_ICP",
        "type": "probe",
        "purpose": "固定低成本局部 ICP（identity 初值、5 次迭代、不做 Global 初始化、不做 SOR），"
                  "回答'当前局部初始化是否已有收敛迹象'。",
        "returns": [
            "initial_fitness / probe_fitness / fitness_improvement",
            "initial_rmse (or null) / probe_rmse",
            "correspondence_count (or null)",
            "source_to_target_support / target_to_source_support",
            "bidirectional_support / support_confidence",
            "iterations: 5",
            "runtime_s",
            "transform_delta_magnitude (or null)",
        ],
        "cost": "low: 5 ICP iterations, ≈6% of formal LOCAL_ICP wall time (measured)",
        "limitations": [
            "仅反映 identity 初值下的局部收敛趋势，大旋转下可能处于错误 basin",
            "不替代正式 LOCAL_ICP / GLOBAL_FPFH_RANSAC_ICP 的完整配准",
            "结果只作为 Agnes 的观察信息，不由 Python 映射成算法选择",
        ],
    },
]


# ---------------------------------------------------------------------------
# Probe A: PCA Orientation Probe
# ---------------------------------------------------------------------------

def _pca_frame(pts: np.ndarray, sample_limit: int = _PCA_SAMPLE_LIMIT) -> Dict[str, Any]:
    """对点集采样后做 PCA，返回特征值/向量与稳定性分级。纯 numpy，无 GT。"""
    rng = np.random.RandomState(_PCA_SEED)
    if len(pts) > sample_limit:
        pts = pts[rng.choice(len(pts), size=sample_limit, replace=False)]
    c = pts - pts.mean(axis=0)
    cov = (c.T @ c) / max(len(c) - 1, 1)
    vals, vecs = np.linalg.eigh(cov)  # ascending
    order = np.argsort(vals)[::-1]     # descending λ0 >= λ1 >= λ2
    lam = np.maximum(vals[order], 0.0)
    V = vecs[:, order]                 # columns = eigenvectors, 3x3 orthogonal
    l0, l1, l2 = float(lam[0]), float(lam[1]), float(lam[2])
    anisotropy = l0 / max(l2, 1e-30)

    top_close = l0 / max(l1, 1e-30)    # λ0/λ1  小 → 平面歧义
    bottom_close = l1 / max(l2, 1e-30)  # λ1/λ2  小 → 线状歧义

    if top_close < 1.25 and bottom_close < 1.5:
        conf, reason = "LOW", "near_isotropic_or_symmetric (all eigenvalues close; no stable principal frame)"
    elif top_close < 1.25:
        conf, reason = "LOW", "near_planar_degeneracy (λ0≈λ1; in-plane orientation undetermined)"
    elif bottom_close < 1.25:
        conf, reason = "LOW", "near_line_degeneracy (λ1≈λ2; transverse axes undetermined)"
    elif top_close < 1.5 or bottom_close < 1.5:
        conf, reason = "MEDIUM", "partial_axis_degeneracy (one eigenvalue pair close; orientation estimate reduced)"
    else:
        conf, reason = "HIGH", None
    return {
        "eigenvalues": [l0, l1, l2],
        "vectors": V,
        "anisotropy": anisotropy,
        "confidence": conf,
        "ambiguity_reason": reason,
    }


def _rotate_between(V_src: np.ndarray, V_tgt: np.ndarray) -> float:
    """给定两个已对齐符号/排列的主轴 frame，返回相对旋转角（deg）。

    R 把 V_src 的列映射到 V_tgt 的列：R = V_tgt @ V_src.T，
    角度 = arccos((trace(R)-1)/2)，范围 [0,180]。
    """
    R = V_tgt @ V_src.T
    cos_theta = float(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))
    return float(np.degrees(np.arccos(cos_theta)))


def run_pca_orientation_probe(source_ply: str, target_ply: str) -> Dict[str, Any]:
    """PCA Orientation Probe：基于几何的主轴 frame 对比，估计粗旋转量。

    歧义处理（不使用 GT）：
    1) eigenvector sign ambiguity：逐轴贪心符号消歧
       v ← ±v，使 v 与参考 frame（源主轴）的点积最大；
    2) axis permutation：枚举 6 种目标轴排列，取 trace(R) 最大
       （= 相对旋转角最小，几何一致性最高）的组合；
    3) 各向同性/近平面/近细长：直接 LOW confidence，rotation_estimate_deg=null。
    """
    import open3d as o3d
    t0 = time.perf_counter()
    src = np.asarray(o3d.io.read_point_cloud(source_ply).points, dtype=np.float64)
    tgt = np.asarray(o3d.io.read_point_cloud(target_ply).points, dtype=np.float64)

    fs, ft = _pca_frame(src), _pca_frame(tgt)
    conf_s, conf_t = fs["confidence"], ft["confidence"]
    V_s, V_t = fs["vectors"], ft["vectors"]

    ambiguity = conf_s == "LOW" or conf_t == "LOW"
    if ambiguity:
        reasons = [r for r, c in ((fs["ambiguity_reason"], conf_s),
                                   (ft["ambiguity_reason"], conf_t)) if c == "LOW"]
        result: Dict[str, Any] = {
            "probe_name": "PCA_ORIENTATION",
            "rotation_estimate_deg": None,
            "orientation_confidence": "LOW",
            "ambiguity_detected": True,
            "ambiguity_reason": "; ".join(reasons) or "ambiguous",
            "source_anisotropy": round(fs["anisotropy"], 4),
            "target_anisotropy": round(ft["anisotropy"], 4),
            "source_eigenvalues": [round(v, 8) for v in fs["eigenvalues"]],
            "target_eigenvalues": [round(v, 8) for v in ft["eigenvalues"]],
            "ambiguity_handling": "per_axis_sign_greedy + permutation_argmax_trace",
            "runtime_s": round(time.perf_counter() - t0, 4),
            "note": "主轴结构不稳定；不得将 rotation_estimate_deg 用于算法选择。",
        }
        return result

    # 至少一侧 MEDIUM 或两侧 HIGH：允许估计，但置信度取两侧较低者
    confidence = "MEDIUM" if ("MEDIUM" in (conf_s, conf_t)) else "HIGH"

    # 排列 + 符号消歧：枚举目标 6 种轴排列，逐轴按源 frame 消歧，取角最小（= trace 最大）
    best_angle, best_axes = None, None
    for perm in itertools.permutations(range(3)):
        V_t_perm = V_t[:, perm]
        # 逐轴贪心符号消歧：使与源 frame 对应轴点积最大（几何一致性最大）
        V_t_signed = np.column_stack([
            np.where(np.dot(V_t_perm[:, j], V_s[:, j]) < 0, -V_t_perm[:, j], V_t_perm[:, j])
            for j in range(3)
        ])
        ang = _rotate_between(V_s, V_t_signed)
        if best_angle is None or ang < best_angle:
            best_angle, best_axes = ang, perm

    result = {
        "probe_name": "PCA_ORIENTATION",
        "rotation_estimate_deg": round(best_angle, 2),
        "orientation_confidence": confidence,
        "ambiguity_detected": False,
        "ambiguity_reason": (
            None if confidence == "HIGH"
            else "partial_axis_degeneracy (one eigenvalue pair close; estimate usable but reduced confidence)"
        ),
        "source_anisotropy": round(fs["anisotropy"], 4),
        "target_anisotropy": round(ft["anisotropy"], 4),
        "source_eigenvalues": [round(v, 8) for v in fs["eigenvalues"]],
        "target_eigenvalues": [round(v, 8) for v in ft["eigenvalues"]],
        "selected_axis_permutation": list(best_axes),
        "ambiguity_handling": "per_axis_sign_greedy + permutation_argmax_trace",
        "runtime_s": round(time.perf_counter() - t0, 4),
        "note": "rotation_estimate_deg 是 PCA 主轴 frame 相对旋转角（0~180°），非逐点配准误差。",
    }
    return result


# ---------------------------------------------------------------------------
# Probe B: Cheap Local ICP Probe
# ---------------------------------------------------------------------------

def _bidirectional_correspondence_support(source: Any, target: Any,
                                          transformation: np.ndarray,
                                          max_correspondence_distance: float
                                          ) -> Dict[str, Any]:
    """Measure symmetric NN support after a candidate transform; no GT or policy."""
    aligned_source = copy.deepcopy(source)
    aligned_source.transform(np.asarray(transformation, dtype=np.float64))
    s2t = np.asarray(aligned_source.compute_point_cloud_distance(target), dtype=np.float64)
    t2s = np.asarray(target.compute_point_cloud_distance(aligned_source), dtype=np.float64)
    threshold = float(max_correspondence_distance)

    def supported_fraction(distances: np.ndarray) -> Optional[float]:
        if distances.size == 0 or not np.all(np.isfinite(distances)):
            return None
        return float(np.mean(distances <= threshold))

    source_support = supported_fraction(s2t)
    target_support = supported_fraction(t2s)
    if source_support is None or target_support is None:
        bidirectional, confidence = None, "LOW"
    else:
        # Harmonic mean penalizes one-sided coverage without interpreting it as a verdict.
        denom = source_support + target_support
        bidirectional = 0.0 if denom == 0.0 else 2.0 * source_support * target_support / denom
        confidence = "HIGH"
    return {
        "source_to_target_support": source_support,
        "target_to_source_support": target_support,
        "bidirectional_support": bidirectional,
        "support_confidence": confidence,
        "support_distance_threshold": threshold,
    }

def run_cheap_local_icp_probe(source_ply: str, target_ply: str,
                              base_scale: float = 0.1,
                              icp_max_corr_scale: float = _CHEAP_ICP_CORR_SCALE,
                              max_iteration: int = _CHEAP_ICP_MAX_ITER
                              ) -> Dict[str, Any]:
    """Cheap Local ICP Probe：identity 初值、固定 5 次迭代、无 Global/SOR 的低成本 ICP。

    回答"当前局部初始化是否已有收敛迹象"。不读 GT，不修改输入点云文件。
    输出只含可观测指标；correspondence_count 在当前 Open3D API 不直接暴露
    逐迭代匹配数时置 null（不伪造）。
    """
    import open3d as o3d
    from agent_tools import _load, _ensure_normals

    max_corr = max(1e-4, float(base_scale) * float(icp_max_corr_scale))
    source = _load(source_ply)
    target = _load(target_ply)
    _ensure_normals(source, search_radius=max_corr * 1.5)
    _ensure_normals(target, search_radius=max_corr * 1.5)

    est = o3d.pipelines.registration.TransformationEstimationPointToPlane()

    # initial fitness/rmse：identity 初值在 ICP 第一次迭代前的对应质量
    #（Open3D 0.20 的 registration_icp 无 0 迭代选项；用 1 次迭代作为 identity
    #   初值的近似 baseline，并在输出中注明）
    t0 = time.perf_counter()
    res_init = o3d.pipelines.registration.registration_icp(
        source, target, max_corr, np.eye(4),
        estimation_method=est,
        criteria=o3d.pipelines.registration.ICPConvergenceCriteria(
            relative_fitness=1e-6, relative_rmse=1e-8, max_iteration=1),
    )
    res_probe = o3d.pipelines.registration.registration_icp(
        source, target, max_corr, np.eye(4),
        estimation_method=est,
        criteria=o3d.pipelines.registration.ICPConvergenceCriteria(
            relative_fitness=1e-6, relative_rmse=1e-8, max_iteration=max_iteration),
    )
    runtime = time.perf_counter() - t0

    T_probe = np.asarray(res_probe.transformation, dtype=np.float64)
    T_init = np.asarray(res_init.transformation, dtype=np.float64)
    support = _bidirectional_correspondence_support(
        source, target, T_probe, max_correspondence_distance=max_corr)

    result: Dict[str, Any] = {
        "probe_name": "CHEAP_LOCAL_ICP",
        "initial_fitness": float(res_init.fitness),
        "probe_fitness": float(res_probe.fitness),
        "initial_rmse": float(res_init.inlier_rmse) if np.isfinite(res_init.inlier_rmse) else None,
        "probe_rmse": float(res_probe.inlier_rmse),
        "fitness_improvement": float(res_probe.fitness - res_init.fitness),
        "correspondence_count": None,  # Open3D API 未直接暴露逐迭代匹配数；不伪造
        "iterations": int(max_iteration),
        "runtime_s": round(float(runtime), 4),
        "transform_delta_magnitude": float(np.linalg.norm(T_probe - T_init)),
        "max_correspondence_distance": float(max_corr),
        **support,
        "note": ("initial_* 为 identity 初值 1 次迭代近似 baseline；probe 固定 "
                  f"{max_iteration} 次迭代，无 Global 初始化，无 SOR。"
                  " 双向 support 是同一距离阈值下的最近邻支持代理，不是真实 overlap。"
                  " 结果只作观察信息，不直接映射算法。"),
    }
    return result


PROBE_DISPATCH: Dict[str, Any] = {
    "PCA_ORIENTATION": run_pca_orientation_probe,
    "CHEAP_LOCAL_ICP": run_cheap_local_icp_probe,
}


def dispatch_probe(probe_name: str, source_ply: str, target_ply: str,
                   base_scale: float = 0.1,
                   param_policy: Optional[Dict[str, Any]] = None
                   ) -> Dict[str, Any]:
    """按 Agnes 请求的 probe_name 分发（白名单校验）。

    - 未请求/未知名字 → 报错（Python 从不自动选择 Probe）
    - CHEAP_LOCAL_ICP 使用固定低成本参数（迭代数/对应距离档位为 Probe 约定，
      不随 Agnes 的正式工具 parameter_policy 变化）
    """
    if probe_name not in PROBE_DISPATCH:
        raise ValueError(
            f"未知 Probe: {probe_name}（合法值: {', '.join(PROBE_DISPATCH)} 或 'NONE'）")
    if probe_name == "PCA_ORIENTATION":
        return run_pca_orientation_probe(source_ply, target_ply)
    return run_cheap_local_icp_probe(source_ply, target_ply, base_scale=base_scale)
