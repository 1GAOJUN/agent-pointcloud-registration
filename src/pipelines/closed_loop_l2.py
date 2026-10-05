"""L2 单场景智能闭环调度器。

流程：朴素 ICP 初测 → 失败自动诊断 → 切换全局粗配准 + ICP 精化 → 复验达标。
- 仅新增文件，不修改任何已有核心模块（make_data / evaluate /
  algorithms.global_registration）。
- 复用 src/evaluate.py 的评测函数、src/algorithms/global_registration.py 的
  全局配准方案，不重复实现逻辑。
- 阈值硬编码，与基准实验（configs/L2.yaml、baseline）保持一致，保证可复现。

运行（直接读 outputs/ICP/L2 已有数据）：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\pipelines\closed_loop_l2.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

# ---------------------------------------------------------------------------
# 复用已有模块（不修改）
# ---------------------------------------------------------------------------
from evaluate import (
    rotation_error_deg,
    translation_error,
    load_transform,
)
from algorithms.global_registration import global_registration

# ---------------------------------------------------------------------------
# 硬编码判定阈值（与 configs/L2.yaml thresholds 及基准实验保持一致）
# ---------------------------------------------------------------------------
ROT_MAX_DEG: float = 5.0
FITNESS_MIN: float = 0.8

# 朴素 ICP（与基线 run_benchmark._estimate_normals + ICP 参数一致）
NAIVE_ICP_DISTANCE_THRESHOLD: float = 0.04
NAIVE_ICP_MAX_ITERATION: int = 100
NAIVE_ICP_NORMAL_RADIUS: float = 0.05
NAIVE_ICP_NORMAL_MAX_NN: int = 30


def _estimate_normals(pcd: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=NAIVE_ICP_NORMAL_RADIUS, max_nn=NAIVE_ICP_NORMAL_MAX_NN
        )
    )
    return pcd


def run_naive_icp(
    source: o3d.geometry.PointCloud,
    target: o3d.geometry.PointCloud,
) -> Dict[str, object]:
    """朴素点到面 ICP：单位阵为初始位姿。"""
    source = _estimate_normals(source)
    target = _estimate_normals(target)
    t0 = time.perf_counter()
    icp = reg.registration_icp(
        source,
        target,
        NAIVE_ICP_DISTANCE_THRESHOLD,
        np.eye(4),
        estimation_method=reg.TransformationEstimationPointToPlane(),
        criteria=reg.ICPConvergenceCriteria(
            max_iteration=NAIVE_ICP_MAX_ITERATION,
            relative_fitness=1e-6,
            relative_rmse=1e-6,
        ),
    )
    elapsed = time.perf_counter() - t0
    return {
        "transform": np.asarray(icp.transformation, dtype=np.float64),
        "fitness": float(icp.fitness),
        "rmse": float(icp.inlier_rmse),
        "elapsed_sec": elapsed,
    }


@dataclass
class StepResult:
    """单步闭环结果（可序列化为 dict / JSON）。"""
    step: str
    strategy: str
    rot_err_deg: float
    trans_err: float
    fitness: float
    elapsed_sec: float
    passed: bool
    detail: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _judge(rot_err_deg: float, fitness: float) -> bool:
    """达标判定：旋转误差<5° 且 fitness>0.8。"""
    return rot_err_deg < ROT_MAX_DEG and fitness > FITNESS_MIN


def _diag_fail_reason(rot_err_deg: float, fitness: float) -> str:
    """失败诊断：将失败归因为「大角度初始位姿偏差」。"""
    if rot_err_deg >= 90.0:
        return (
            f"旋转误差 {rot_err_deg:.2f}° 远超阈值（>{ROT_MAX_DEG}°），"
            f"判定为大角度初始位姿偏差（单位阵初值远离真实变换），朴素 ICP 局部收敛失败。"
        )
    return (
        f"旋转误差 {rot_err_deg:.2f}° / fitness {fitness:.4f} 未达标，"
        f"归因为初始位姿偏差导致局部收敛，需全局粗配准提供更优初值。"
    )


@dataclass
class ClosedLoopReport:
    """完整闭环调度报告。"""
    source_ply: str
    target_ply: str
    gt_path: str
    thresholds: Dict[str, float]
    steps: List[StepResult] = field(default_factory=list)
    diagnosis: str = ""
    final_passed: bool = False
    total_elapsed_sec: float = 0.0
    switch_strategy: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "source_ply": self.source_ply,
            "target_ply": self.target_ply,
            "gt_path": self.gt_path,
            "thresholds": self.thresholds,
            "steps": [s.to_dict() for s in self.steps],
            "diagnosis": self.diagnosis,
            "final_passed": self.final_passed,
            "switch_strategy": self.switch_strategy,
            "total_elapsed_sec": float(self.total_elapsed_sec),
        }


def run_closed_loop(
    source_ply: str,
    target_ply: str,
    gt_path: str,
) -> ClosedLoopReport:
    """执行完整闭环：朴素ICP初测→失败诊断→全局粗配准+ICP精化→复验。

    全程自动，无人工干预；返回结构化报告。
    """
    t_start = time.perf_counter()
    T_gt = load_transform(gt_path)
    source = o3d.io.read_point_cloud(source_ply)
    target = o3d.io.read_point_cloud(target_ply)

    report = ClosedLoopReport(
        source_ply=source_ply,
        target_ply=target_ply,
        gt_path=gt_path,
        thresholds={"rot_max_deg": ROT_MAX_DEG, "fitness_min": FITNESS_MIN},
    )

    # ---- ① 基线测试：朴素 ICP（单位阵初值） ----
    naive = run_naive_icp(source, target)
    naive_rot = rotation_error_deg(naive["transform"], T_gt)
    naive_trans = translation_error(naive["transform"], T_gt)
    naive_pass = _judge(float(naive_rot), float(naive["fitness"]))
    report.steps.append(
        StepResult(
            step="baseline",
            strategy="朴素ICP（单位阵初值）",
            rot_err_deg=float(naive_rot),
            trans_err=float(naive_trans),
            fitness=float(naive["fitness"]),
            elapsed_sec=float(naive["elapsed_sec"]),
            passed=naive_pass,
            detail=f"rot_err={naive_rot:.4f}° trans_err={naive_trans:.4f} "
                   f"fitness={naive['fitness']:.4f}",
        )
    )

    if naive_pass:
        # 基线即达标：闭环一步完成（L2 不会发生，但逻辑必须完整）
        report.final_passed = True
        report.total_elapsed_sec = time.perf_counter() - t_start
        return report

    # ---- ②③ 失败诊断 + 切换全局粗配准 + ICP 精化 ----
    report.diagnosis = _diag_fail_reason(float(naive_rot), float(naive["fitness"]))
    report.switch_strategy = True
    exp = global_registration(source_ply, target_ply)
    exp_rot = rotation_error_deg(exp["transform"], T_gt)
    exp_trans = translation_error(exp["transform"], T_gt)
    exp_pass = _judge(float(exp_rot), float(exp["fitness"]))
    report.steps.append(
        StepResult(
            step="global",
            strategy="FPFH+RANSAC全局粗配准 + ICP精化",
            rot_err_deg=float(exp_rot),
            trans_err=float(exp_trans),
            fitness=float(exp["fitness"]),
            elapsed_sec=float(exp["elapsed_sec"]),
            passed=exp_pass,
            detail=f"rot_err={exp_rot:.4f}° trans_err={exp_trans:.4f} "
                   f"fitness={exp['fitness']:.4f} "
                   f"ransac_fitness={exp['ransac_fitness']:.4f}",
        )
    )

    # ---- ④ 复验判定：输出最终结论 ----
    report.final_passed = exp_pass
    report.total_elapsed_sec = time.perf_counter() - t_start
    return report
