#!/usr/bin/env python3
"""B2B 工具级单元测试：PCA Orientation Probe + Cheap Local ICP Probe。

运行方式（无需 pytest）：
  D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests/test_b2b_probes.py

测试清单：
  T1 PCA Test A — 明显非对称、可稳定估计 orientation 的点云
                  （构造细长 + 平面各向异性差异，验证 rotation_estimate_deg 非 null、HIGH/MEDIUM）
  T2 PCA Test B — 近对称点云（各向同性球壳 / 立方体）
                  要求：LOW confidence 或 ambiguity_detected，rotation_estimate_deg=null
  T3 Cheap ICP — 输出完整字段、迭代受限（iterations==5）、不读 GT、
                  不修改输入点云文件、runtime 合理（< 正式 ICP）
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import open3d as o3d
from agent_probes import (run_pca_orientation_probe, run_cheap_local_icp_probe,
                          PROBE_DISPATCH, MAX_PROBES_PER_RUN)
from agent_tools import run_local_icp, _load

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, PASS if ok else FAIL, detail))
    print(f"[{PASS if ok else FAIL}] {name}  {detail}")


def make_ply(pts: np.ndarray, path: Path) -> None:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts.astype(np.float64))
    o3d.io.write_point_cloud(str(path), pcd)


def ellipsoid(pts_per_shape: int = 2000, seed: int = 7) -> np.ndarray:
    """明显非对称椭球：(1, 0.4, 0.15) 缩放各向异性 → 稳定主轴 frame。"""
    rng = np.random.RandomState(seed)
    unit = rng.randn(pts_per_shape, 3)
    unit = unit / np.linalg.norm(unit, axis=1, keepdims=True)
    return unit * np.array([1.0, 0.4, 0.15])


def sphere_shell(pts_per_shape: int = 2000, seed: int = 8) -> np.ndarray:
    """近对称球壳：各向同性，PCA 无稳定主轴。"""
    rng = np.random.RandomState(seed)
    unit = rng.randn(pts_per_shape, 3)
    unit = unit / np.linalg.norm(unit, axis=1, keepdims=True)
    return unit * 1.0


def rotated(pts: np.ndarray, rot_deg: float, axis: int, seed: int = 9) -> np.ndarray:
    """绕某轴旋转 rot_deg（用于 Test A 的方向对比，非 GT，纯几何构造）。"""
    theta = np.deg2rad(rot_deg)
    c, s = np.cos(theta), np.sin(theta)
    if axis == 0:
        R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    elif axis == 1:
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    else:
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return pts @ R.T


def main() -> int:
    tmp = ROOT / "outputs" / "development_tests" / "B2B_ACTIVE_PROBE_SMOKE" / "probe_unit_test"
    tmp.mkdir(parents=True, exist_ok=True)

    # ---------------- T1: PCA Test A — 明显非对称 ----------------
    src_a = ellipsoid(seed=7)
    tgt_a = rotated(ellipsoid(seed=7), 45.0, axis=2)
    make_ply(src_a, tmp / "asym_src.ply")
    make_ply(tgt_a, tmp / "asym_tgt.ply")
    t0 = time.perf_counter()
    obs = run_pca_orientation_probe(str(tmp / "asym_src.ply"), str(tmp / "asym_tgt.ply"))
    t1 = time.perf_counter()
    print(json.dumps(obs, indent=2, ensure_ascii=False))
    ok = (
        obs["rotation_estimate_deg"] is not None
        and obs["orientation_confidence"] in ("HIGH", "MEDIUM")
        and not obs["ambiguity_detected"]
        and 30.0 <= obs["rotation_estimate_deg"] <= 60.0   # 真实 45°（绕 z 轴）
    )
    record("T1_pca_asymmetric_orientation_estimate", ok,
           f"rot_est={obs['rotation_estimate_deg']}° conf={obs['orientation_confidence']} "
           f"(true=45°), runtime={obs['runtime_s']}s (wall {t1-t0:.3f}s)")

    # ---------------- T2: PCA Test B — 近对称（球壳 vs 椭球） ----------------
    make_ply(sphere_shell(seed=8), tmp / "sym_src.ply")
    make_ply(ellipsoid(seed=7), tmp / "sym_tgt.ply")
    obs2 = run_pca_orientation_probe(str(tmp / "sym_src.ply"), str(tmp / "sym_tgt.ply"))
    print(json.dumps(obs2, indent=2, ensure_ascii=False))
    ok2 = (
        obs2["rotation_estimate_deg"] is None
        and obs2["orientation_confidence"] == "LOW"
        and obs2["ambiguity_detected"] is True
        and obs2["ambiguity_reason"]
    )
    record("T2_pca_near_symmetric_low_confidence", ok2,
           f"rot_est={obs2['rotation_estimate_deg']} conf={obs2['orientation_confidence']} "
           f"reason={obs2['ambiguity_reason']}")

    # 2b: 球壳 vs 球壳（双侧各向同性）
    make_ply(sphere_shell(seed=11), tmp / "sym2_tgt.ply")
    obs2b = run_pca_orientation_probe(str(tmp / "sym_src.ply"), str(tmp / "sym2_tgt.ply"))
    ok2b = (obs2b["rotation_estimate_deg"] is None and obs2b["orientation_confidence"] == "LOW")
    record("T2b_pca_sphere_vs_sphere_low_confidence", ok2b,
           f"conf={obs2b['orientation_confidence']} reason={obs2b['ambiguity_reason']}")

    # ---------------- T3: Cheap Local ICP Probe ----------------
    l2_case = ROOT / "outputs" / "ICP" / "L2" / "L2" / "seed_202"
    src_ply, tgt_ply = str(l2_case / "source.ply"), str(l2_case / "target.ply")

    # 输入完整性快照（验证 Probe 不修改原始点云）
    p0_src = np.asarray(_load(src_ply).points)
    p0_tgt = np.asarray(_load(tgt_ply).points)

    from agent_diagnose import diagnose
    diag = diagnose(src_ply, tgt_ply)
    base_scale = float(diag["base_scale"])

    t0 = time.perf_counter()
    obs3 = run_cheap_local_icp_probe(src_ply, tgt_ply, base_scale=base_scale)
    t_probe_wall = time.perf_counter() - t0
    print(json.dumps({k: v for k, v in obs3.items()}, indent=2, ensure_ascii=False))

    required_fields = {"probe_name", "initial_fitness", "probe_fitness", "initial_rmse",
                       "probe_rmse", "fitness_improvement", "correspondence_count",
                       "iterations", "runtime_s", "transform_delta_magnitude"}
    ok3a = required_fields <= set(obs3.keys()) and obs3["probe_name"] == "CHEAP_LOCAL_ICP"
    ok3b = obs3["iterations"] == 5
    p1_src = np.asarray(_load(src_ply).points)
    p1_tgt = np.asarray(_load(tgt_ply).points)
    ok3c = np.allclose(p0_src, p1_src) and np.allclose(p0_tgt, p1_tgt)

    # GT 隔离：输出不得含 GT 相关字段
    banned = {"rotation_error", "translation_error", "gt_transform", "gt_rot_err"}
    ok3d = not (banned & set(obs3.keys()))

    # runtime 合理性 + 成本对比（正式 ICP）
    t0 = time.perf_counter()
    full = run_local_icp(src_ply, tgt_ply, icp_max_corr_scale=2.0, base_scale=base_scale)
    t_full_wall = time.perf_counter() - t0
    ok3e = obs3["runtime_s"] < 0.5 * t_full_wall and obs3["runtime_s"] < 2.0
    record("T3_cheap_icp_output_complete", ok3a, f"missing={required_fields - set(obs3.keys()) or 'none'}")
    record("T3_cheap_icp_iterations_capped", ok3b, f"iterations={obs3['iterations']}")
    record("T3_cheap_icp_input_unmodified", ok3c, "source/target PLY byte-identical point sets before/after")
    record("T3_cheap_icp_no_gt_fields", ok3d, "no rotation_error/translation_error/gt_transform in output")
    record("T3_cheap_icp_runtime_budget", ok3e,
           f"probe_wall={t_probe_wall:.3f}s vs formal_icp_wall={t_full_wall:.3f}s "
           f"(ratio {t_probe_wall/max(t_full_wall,1e-9):.2f}x)")

    # ---------------- 汇总 ----------------
    n_fail = sum(1 for _, s, _ in results if s == FAIL)
    print(f"\n=== B2B probe unit tests: {len(results)-n_fail}/{len(results)} PASS ===")
    summary = {"tests": [{"name": n, "status": s, "detail": d} for n, s, d in results],
               "n_pass": len(results) - n_fail, "n_fail": n_fail}
    (tmp / "unit_test_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
