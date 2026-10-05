"""L2 完整配准流水工具（SVD 全局初值 + 朴素点到面 ICP 精化）。

仅调用两个算法工具文件：
    src/algorithms/svd_global_init_new.py  -> estimate_global_init
    src/algorithms/icp_naive_new.py        -> register

输出（写入 outputs/L2/）：
    est_transform.npy          最终变换矩阵（source -> target）
    l2_registration_result.json  完整结果 JSON（含各阶段指标、评测结果）
    l2_registration_log.txt    人类可读执行日志
运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\l2_pipeline.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import open3d as o3d

# 让相对导入在从项目根目录直接运行时可用
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from algorithms.svd_global_init_new import estimate_global_init
from algorithms.icp_naive_new import register
from evaluate import (
    evaluate_case,
    rotation_error_deg,
    save_result,
    translation_error,
)

L2_DIR = ROOT / "outputs" / "L2"
ROT_THR_DEG = 5.0
FIT_MIN = 0.8


def _rot_err(T1: np.ndarray, T2: np.ndarray) -> float:
    return rotation_error_deg(T1, T2)


def run() -> dict:
    t_start = time.time()
    src = o3d.io.read_point_cloud(str(L2_DIR / "source.ply"))
    tgt = o3d.io.read_point_cloud(str(L2_DIR / "target.ply"))
    T_gt = np.load(str(L2_DIR / "gt_transform.npy"))

    log_lines = [
        "L2 Registration Pipeline Execution Log",
        "=" * 50,
        f"started_at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
        f"source: {L2_DIR / 'source.ply'}",
        f"target: {L2_DIR / 'target.ply'}",
        f"gt:     {L2_DIR / 'gt_transform.npy'}",
        "",
    ]

    # ---- 阶段 1：SVD 全局初值 ----
    svd_out = estimate_global_init(src, tgt)
    T_svd = svd_out["transform"]
    svd_rot_err = _rot_err(T_svd, T_gt)
    log_lines += [
        "[Stage 1] SVD cross-covariance global init",
        f"  fitness(svd) = {svd_out['fitness']:.4f}",
        f"  rmse(svd)    = {svd_out['rmse']:.3e}",
        f"  rot_err vs gt = {svd_rot_err:.6f} deg",
        f"  elapsed     = {svd_out['elapsed_s']:.3f} s",
        "",
    ]

    # ---- 阶段 2：朴素点到面 ICP 精化 ----
    tgt_work = o3d.io.read_point_cloud(str(L2_DIR / "target.ply"))
    icp_out = register(src, tgt_work, T_svd)
    T_est = icp_out["transform"]
    icp_rot_err = _rot_err(T_est, T_gt)
    log_lines += [
        "[Stage 2] Naive point-to-plane ICP refinement (init = SVD global)",
        f"  fitness(icp) = {icp_out['fitness']:.4f}",
        f"  rmse(icp)    = {icp_out['rmse']:.3e}",
        f"  rot_err vs gt = {icp_rot_err:.6f} deg",
        f"  elapsed     = {icp_out['elapsed_s']:.3f} s",
        "",
    ]

    # ---- 阶段 3：评测 ----
    eval_metrics = evaluate_case(T_est, str(L2_DIR / "gt_transform.npy"), rot_thr_deg=ROT_THR_DEG)
    passed_rot = icp_rot_err < ROT_THR_DEG
    passed_fit = icp_out["fitness"] > FIT_MIN
    passed_all = passed_rot and passed_fit
    eval_metrics["rot_thr_deg"] = ROT_THR_DEG
    eval_metrics["fitness_min"] = FIT_MIN
    eval_metrics["final_fitness"] = icp_out["fitness"]
    eval_metrics["final_rmse"] = icp_out["rmse"]
    log_lines += [
        "[Stage 3] Evaluation vs gt_transform.npy",
        f"  rot_err   = {icp_rot_err:.6f} deg  (threshold {ROT_THR_DEG} deg) -> {'PASS' if passed_rot else 'FAIL'}",
        f"  trans_err = {eval_metrics['trans_err']:.6f}  (threshold {eval_metrics['trans_thr']} ) -> {'PASS' if eval_metrics['trans_err'] < eval_metrics['trans_thr'] else 'FAIL'}",
        f"  fitness   = {icp_out['fitness']:.4f}  (min {FIT_MIN}) -> {'PASS' if passed_fit else 'FAIL'}",
        f"  overall success = {passed_all}",
        "",
    ]

    # ---- 保存结果 ----
    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "scene": "L2",
        "source": "outputs/L2/source.ply",
        "target": "outputs/L2/target.ply",
        "gt": "outputs/L2/gt_transform.npy",
        "pipeline": ["svd_global_init_new.estimate_global_init", "icp_naive_new.register"],
        "stage1_svd": {
            "transform": svd_out["transform"].tolist(),
            "fitness": svd_out["fitness"],
            "rmse": svd_out["rmse"],
            "elapsed_s": svd_out["elapsed_s"],
            "rot_err_vs_gt_deg": svd_rot_err,
        },
        "stage2_icp": {
            "transform": icp_out["transform"].tolist(),
            "fitness": icp_out["fitness"],
            "rmse": icp_out["rmse"],
            "elapsed_s": icp_out["elapsed_s"],
            "rot_err_vs_gt_deg": icp_rot_err,
        },
        "evaluation": eval_metrics,
        "passed": passed_all,
        "total_elapsed_s": time.time() - t_start,
    }

    np.save(str(L2_DIR / "est_transform.npy"), T_est)
    save_result(result, str(L2_DIR / "l2_registration_result.json"))
    log_path = L2_DIR / "l2_registration_log.txt"
    log_lines.append(f"total_elapsed_s: {result['total_elapsed_s']:.3f}")
    log_lines.append(f"est_transform saved to: {L2_DIR / 'est_transform.npy'}")
    log_lines.append(f"result json saved to:    {L2_DIR / 'l2_registration_result.json'}")
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    print("\n".join(log_lines))
    print(f"[done] passed_all = {passed_all}")
    return result


if __name__ == "__main__":
    run()
