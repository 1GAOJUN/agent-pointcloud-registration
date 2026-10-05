"""真值自验：验证保存的真值矩阵是"准尺子"。

两类检查：
  1. 干净关卡（L1/L2：无噪声、无离群点、无裁剪）：
     target = source @ R_gt^T + t_gt，逐点对应。
     把 target 用 gt_T 逆矩阵变回去，应逐点还原 source，误差 ~1e-16（浮点下限）。
  2. 所有关卡（含 L3 噪声 / L4 裁剪）：
     真值矩阵本身必须是合法刚体变换：R 正交、det(R)=1、齐次行 [0,0,0,1]，
     且 inv(gt_T) @ gt_T = I。这证明"尺子"的数学定义无误，
     噪声/裁剪只扰动 target 数据，不改变真值矩阵本身。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\verify_gt.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import open3d as o3d

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))


def _load_meta(case_dir: Path) -> Dict[str, object]:
    p = case_dir / "meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _is_clean(cfg: Dict[str, object]) -> bool:
    """干净 = 无噪声、无离群点、无裁剪。"""
    return (
        float(cfg.get("noise_sigma", 0.0)) == 0.0
        and float(cfg.get("outlier_ratio", 0.0)) == 0.0
        and float(cfg.get("crop_ratio", 0.0)) == 0.0
    )


def verify_rigorous_gt(case_dir: Path) -> Dict[str, float]:
    """所有关卡都做：真值矩阵刚体合法性 + 逆矩阵自洽性。"""
    gt_T = np.load(str(case_dir / "gt_transform.npy")).astype(np.float64)
    R = gt_T[:3, :3]
    ortho_err = float(np.max(np.abs(R.T @ R - np.eye(3))))
    det = float(np.linalg.det(R))
    I4 = np.eye(4)
    inv_roundtrip_err = float(np.max(np.abs(np.linalg.inv(gt_T) @ gt_T - I4)))
    last_row_err = float(np.max(np.abs(gt_T[3, :] - np.array([0.0, 0.0, 0.0, 1.0]))))
    passed = (ortho_err < 1e-9) and (abs(det - 1.0) < 1e-9) \
        and (inv_roundtrip_err < 1e-12) and (last_row_err < 1e-12)
    return {
        "ortho_err": ortho_err, "det": det,
        "inv_roundtrip_err": inv_roundtrip_err,
        "last_row_err": last_row_err, "rigorous_passed": passed,
    }


def verify_pointwise_clean(case_dir: Path) -> Dict[str, float]:
    """仅干净关卡：target 逆变换后逐点还原 source。"""
    src = o3d.io.read_point_cloud(str(case_dir / "source.ply"))
    tgt = o3d.io.read_point_cloud(str(case_dir / "target.ply"))
    gt_T = np.load(str(case_dir / "gt_transform.npy")).astype(np.float64)
    inv_T = np.linalg.inv(gt_T)
    tgt_pts = np.asarray(tgt.points, dtype=np.float64)
    src_pts = np.asarray(src.points, dtype=np.float64)
    ones = np.ones((tgt_pts.shape[0], 1))
    tgt_inv = (np.hstack([tgt_pts, ones]) @ inv_T.T)[:, :3]
    n = min(len(src_pts), len(tgt_inv))
    diff = np.linalg.norm(src_pts[:n] - tgt_inv[:n], axis=1)
    mean_d, max_d = float(np.mean(diff)), float(np.max(diff))
    return {"n_points": n, "mean_dist": mean_d, "max_dist": max_d,
            "clean_passed": max_d < 1e-9}


def main() -> int:
    out_root = _PROJECT_ROOT / "outputs" / "ICP"
    all_ok = True
    print("=== 真值自验：刚体合法性（所有关卡）===")
    for lv in ["L1", "L2", "L3", "L4"]:
        cd = out_root / lv
        if not (cd / "gt_transform.npy").exists():
            print(f"[skip] {lv} 无 gt_transform.npy，先跑 run_benchmark.py")
            continue
        r = verify_rigorous_gt(cd)
        all_ok = all_ok and bool(r["rigorous_passed"])
        print(f"[{lv}] 刚体合法: ortho_err={r['ortho_err']:.2e} det={r['det']:.6f} "
              f"inv_roundtrip={r['inv_roundtrip_err']:.2e} last_row={r['last_row_err']:.2e} "
              f"-> {'PASS' if r['rigorous_passed'] else 'FAIL'}")

    print("\n=== 真值自验：逐点还原（仅干净关卡 L1/L2）===")
    for lv in ["L1", "L2"]:
        cd = out_root / lv
        if not (cd / "source.ply").exists():
            print(f"[skip] {lv} 无 source.ply")
            continue
        meta_cfg = _load_meta(cd).get("config", {})
        r = verify_pointwise_clean(cd)
        all_ok = all_ok and bool(r["clean_passed"])
        print(f"[{lv}] n={r['n_points']} mean_dist={r['mean_dist']:.3e} max_dist={r['max_dist']:.3e} "
              f"-> {'PASS' if r['clean_passed'] else 'FAIL'}")

    print("\n=== 真值自验结论 ===")
    if all_ok:
        print("PASS：所有关卡真值矩阵都是合法刚体变换（R 正交、det=1、inv 自洽）；"
              "干净关卡 L1/L2 逆变换后逐点还原 source（误差 < 1e-9，浮点下限）。"
              "L3/L4 因噪声/裁剪逐点数不同，仅做刚体合法性验证。尺子本身是准的。")
        return 0
    print("FAIL：存在真值矩阵不满足刚体合法性，请复核。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
