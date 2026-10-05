"""L2 大角度场景：朴素 ICP 基线 vs FPFH+RANSAC 全局粗配准+ICP 精化 对照实验。

只读 outputs/ICP/L2 下已有的 source.ply / target.ply / gt_transform.npy，
不重新生成数据；不修改任何已有核心文件。
适配 Open3D 0.20 API（RegistrationResult.inlier_rmse 取代 .rmse）。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\test_l2_global_reg.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

# 复用现有模块（不修改）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import evaluate  # noqa: E402
from algorithms.global_registration import global_registration  # noqa: E402

# 达标阈值（题目要求）
ROT_THR_DEG: float = 5.0
FITNESS_MIN: float = 0.8

# 对照组：与基线一致的朴素 ICP（单位阵初值 + 点到面）
_ICP_DISTANCE_THRESHOLD = 0.04
_ICP_MAX_ITERATION = 100


def _estimate_normals(pcd: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30)
    )
    return pcd


def run_naive_icp(
    source: o3d.geometry.PointCloud,
    target: o3d.geometry.PointCloud,
) -> Dict[str, object]:
    """对照组：单位阵初值的朴素 ICP。"""
    source = _estimate_normals(source)
    target = _estimate_normals(target)
    t0 = time.perf_counter()
    icp = reg.registration_icp(
        source,
        target,
        _ICP_DISTANCE_THRESHOLD,
        np.eye(4),
        estimation_method=reg.TransformationEstimationPointToPlane(),
        criteria=reg.ICPConvergenceCriteria(
            max_iteration=_ICP_MAX_ITERATION,
            relative_fitness=1e-6,
            relative_rmse=1e-6,
        ),
    )
    elapsed = time.perf_counter() - t0
    return {
        "transform": np.asarray(icp.transformation, dtype=np.float64),
        "fitness": float(icp.fitness),
        "rmse": float(icp.inlier_rmse),  # Open3D 0.20 属性名
        "elapsed_sec": elapsed,
    }


def judge_pass(rot_err_deg: float, fitness: float) -> bool:
    """题目达标标准：旋转误差<5° 且 fitness>0.8。"""
    return rot_err_deg < ROT_THR_DEG and fitness > FITNESS_MIN


def main() -> int:
    l2_dir = _PROJECT_ROOT / "outputs" / "ICP" / "L2"
    source_ply = l2_dir / "source.ply"
    target_ply = l2_dir / "target.ply"
    gt_npy = l2_dir / "gt_transform.npy"

    for p in (source_ply, target_ply, gt_npy):
        if not p.exists():
            print(f"[FAIL] 缺少 {p}")
            print("      请先运行 src/run_benchmark.py 生成 outputs/ICP/L2。")
            return 1

    T_gt = evaluate.load_transform(str(gt_npy))

    source = o3d.io.read_point_cloud(str(source_ply))
    target = o3d.io.read_point_cloud(str(target_ply))

    # ① 对照组：朴素 ICP
    naive = run_naive_icp(source, target)
    naive_rot = evaluate.rotation_error_deg(naive["transform"], T_gt)
    naive_trans = evaluate.translation_error(naive["transform"], T_gt)

    # ② 实验组：FPFH+RANSAC+ICP
    exp = global_registration(str(source_ply), str(target_ply))
    exp_rot = evaluate.rotation_error_deg(exp["transform"], T_gt)
    exp_trans = evaluate.translation_error(exp["transform"], T_gt)

    # 汇总
    rows = [
        {
            "name": "朴素ICP（对照组）",
            "rot_err_deg": float(naive_rot),
            "trans_err": float(naive_trans),
            "fitness": float(naive["fitness"]),
            "elapsed_sec": float(naive["elapsed_sec"]),
            "passed": judge_pass(float(naive_rot), float(naive["fitness"])),
        },
        {
            "name": "FPFH+RANSAC+ICP（实验组）",
            "rot_err_deg": float(exp_rot),
            "trans_err": float(exp_trans),
            "fitness": float(exp["fitness"]),
            "elapsed_sec": float(exp["elapsed_sec"]),
            "passed": judge_pass(float(exp_rot), float(exp["fitness"])),
        },
    ]

    print("=" * 78)
    print("L2 大角度场景对照实验 · 朴素ICP vs FPFH+RANSAC全局粗配准+ICP精化")
    print(f"数据目录：{l2_dir}")
    print(f"达标标准：旋转误差<{ROT_THR_DEG}° 且 fitness>{FITNESS_MIN}")
    print("=" * 78)
    header = "| 方案 | 旋转误差(°) | 平移误差 | fitness | 耗时(s) | 达标 |"
    sep = "|------|-------------|----------|---------|---------|------|"
    print(header)
    print(sep)
    for r in rows:
        verdict = "PASS" if r["passed"] else "FAIL"
        print(
            f"| {r['name']} | {r['rot_err_deg']:.4f} | {r['trans_err']:.4f} | "
            f"{r['fitness']:.4f} | {r['elapsed_sec']:.2f} | {verdict} |"
        )
    print("=" * 78)

    exp_pass = rows[1]["passed"]
    print(
        f"[{'PASS' if exp_pass else 'FAIL'}] 实验组(L2)："
        f"rot_err={exp_rot:.4f}° (<{ROT_THR_DEG}°)，"
        f"fitness={float(exp['fitness']):.4f} (>{FITNESS_MIN})"
    )

    # 留证：把结果写入 outputs/ICP/L2/ 下 json（新增文件，不碰已有）
    out_json = l2_dir / "l2_global_registration_result.json"
    payload = {
        "case_dir": str(l2_dir),
        "thresholds": {"rot_max_deg": ROT_THR_DEG, "fitness_min": FITNESS_MIN},
        "rows": rows,
        "experiment_passed": exp_pass,
    }
    out_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float),
        encoding="utf-8",
    )
    print(f"[saved] {out_json}")

    return 0 if exp_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
