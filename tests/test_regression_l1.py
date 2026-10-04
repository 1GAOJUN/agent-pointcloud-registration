"""回归测试：L1 配置加载 → 跑通数据生成+ICP → 旋转误差在阈值内。

作为后续实验的基准回归，验证 configs/L1.yaml 能完整跑通且达标。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\test_regression_l1.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import make_data   # noqa: E402
import evaluate    # noqa: E402
import run_benchmark  # noqa: E402


def main() -> int:
    cfg_path = _PROJECT_ROOT / "configs" / "L1.yaml"
    if not cfg_path.exists():
        print(f"[FAIL] 缺少 {cfg_path}")
        return 1

    cfg = run_benchmark.load_yaml_config(cfg_path)
    print(f"[加载] L1.yaml: seed={cfg.get('seed')} rot=({cfg.get('rot_x_deg')}, "
          f"{cfg.get('rot_y_deg')}, {cfg.get('rot_z_deg')})")

    # 在临时目录跑一关（不污染 outputs）
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        lv_dir = tmp_root / "L1"
        lv_dir.mkdir()
        rec = run_benchmark.run_level("L1", cfg, tmp_root)

    rot_max = float(cfg.get("thresholds", {}).get("rot_max_deg", 5.0))
    fitness_min = float(cfg.get("thresholds", {}).get("fitness_min", 0.8))
    rot_ok = rec["rot_err_deg"] < rot_max
    fit_ok = rec["fitness"] >= fitness_min
    passed = rec["passed"]

    print(f"[回归] rot_err={rec['rot_err_deg']:.4f}° (<{rot_max}°: {rot_ok})  "
          f"fitness={rec['fitness']:.4f} (>={fitness_min}: {fit_ok})  "
          f"trans_err={rec['trans_err']:.4f}  elapsed={rec['elapsed_sec']:.2f}s")

    if passed:
        print("[PASS] L1 回归通过：配置加载、数据生成、ICP 配准、评测全链路跑通且误差在阈值内。")
        return 0
    else:
        print("[FAIL] L1 回归未通过：请检查数据生成或 ICP 参数。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
