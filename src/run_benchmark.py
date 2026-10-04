"""批量基准运行器：加载 configs/L*.yaml，逐关执行 数据生成→真值变换→朴素ICP→评测。

红线遵守：只调用现有 make_data.py / evaluate.py 的函数，不修改任何已有文件逻辑。
fitness 指标来自 open3d.pipelines.registration.registration_icp 的 result.fitness，
旋转/平移误差复用 evaluate.py 的 rotation_error_deg / translation_error。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\run_benchmark.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import open3d as o3d
import open3d.pipelines.registration as reg

# 复用现有模块（不修改它们）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import make_data  # noqa: E402
import evaluate   # noqa: E402


# ---------------------------------------------------------------------------
# 极简 YAML 加载器（仅支持本项目 configs 用到的语法子集）
#   - 顶层 key: value 标量（str/int/float/bool）
#   - 列表：多行 "- item"
#   - 嵌套块：key: 后跟缩进的 key: value（仅一层）
# 不依赖 PyYAML（环境未安装），保持 requirements 不变。
# ---------------------------------------------------------------------------


def _parse_scalar(raw: str) -> Any:
    """把 YAML 标量字符串解析为 int/float/bool/str。"""
    raw = raw.strip()
    if raw in ("z", "x", "y"):
        return raw
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def load_yaml_config(path: Path) -> Dict[str, Any]:
    """解析极简 YAML 配置文件为 dict。

    支持的语法：
      key: value          # 标量
      key:                # 嵌套块（一层）
        subkey: value
      key:                # 列表
        - item
        - item
    足以覆盖 configs/L*.yaml 的全部用法。
    """
    data: Dict[str, Any] = {}
    current_block: str | None = None   # 当前所属嵌套块 key
    current_list: str | None = None    # 当前所属列表 key
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        is_list_item = stripped.startswith("- ") or stripped == "-"
        is_kv = ":" in stripped

        if indent == 0:
            current_block = None
            current_list = None
            if is_kv:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if val == "":
                    data[key] = {}
                    current_block = key
                    current_list = None
                else:
                    data[key] = _parse_scalar(val)
                    current_block = None
            else:
                pass
        else:
            if is_list_item:
                # 归入最近设置的空 key（当前列表）
                if current_list is None:
                    # 找到最近设置的空 dict key，转成列表
                    candidates = [k for k in data if isinstance(data[k], dict)]
                    if candidates:
                        current_list = candidates[-1]
                if current_list is not None:
                    if not isinstance(data.get(current_list), list):
                        data[current_list] = []
                    item = stripped[2:].strip() if stripped.startswith("- ") else ""
                    data[current_list].append(_parse_scalar(item))
                continue
            if is_kv:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if current_block is not None and isinstance(data.get(current_block), dict):
                    data[current_block][key] = _parse_scalar(val)
    return data


# ---------------------------------------------------------------------------
# 单个关卡执行
# ---------------------------------------------------------------------------


def _estimate_normals(pcd: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
    """估计法向量（朴素 ICP 点面法需要）。"""
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
    return pcd


def run_level(level_name: str, cfg: Dict[str, Any], out_root: Path) -> Dict[str, Any]:
    """执行单个关卡：数据生成 → ICP → 评测 → 存盘。

    Args:
        level_name: 关卡名，如 L1。
        cfg: 解析后的关卡配置 dict。
        out_root: outputs/ 根目录。

    Returns:
        含 rot_err_deg/trans_err/fitness/耗时/达标 的 dict。
    """
    seed = int(cfg.get("seed", 0))
    thresholds = cfg.get("thresholds", {})
    rot_max = float(thresholds.get("rot_max_deg", 5.0))
    fitness_min = float(thresholds.get("fitness_min", 0.8))

    # 构造 make_data.LevelConfig 可识别的平铺 dict（只用已知字段）
    level_cfg = {k: v for k, v in cfg.items() if k in {
        "level", "n_points", "rot_x_deg", "rot_y_deg", "rot_z_deg",
        "translation", "noise_sigma", "outlier_ratio", "crop_ratio",
        "crop_axis", "crop_sign",
    }}
    level_cfg.setdefault("level", level_name)

    # 1. 数据生成（输出到 outputs/Lx/ 便于人工抽查）
    out_dir = out_root / level_name
    out_dir.mkdir(parents=True, exist_ok=True)
    case = make_data.generate_case(level_cfg, seed, str(out_dir))
    case_dir = Path(case["case_dir"])
    src_ply = case_dir / "source.ply"
    tgt_ply = case_dir / "target.ply"
    gt_npy = case_dir / "gt_transform.npy"
    gt_T = np.asarray(case["gt_transform"], dtype=np.float64)
    # 再存一份扁平到 outputs/Lx/（generate_case 写在 seed_xxx/ 子目录，这里补齐顶层）
    np.save(out_dir / "gt_transform.npy", gt_T)
    meta = {k: v for k, v in case.items() if k != "gt_transform"}
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    # 拷贝输入点云到 outputs/Lx/ 顶层
    (out_dir / "source.ply").write_bytes(src_ply.read_bytes())
    (out_dir / "target.ply").write_bytes(tgt_ply.read_bytes())

    # 2. 读回点云，估计法向量，跑朴素 ICP（单位阵初值，点面法）
    source = o3d.io.read_point_cloud(str(out_dir / "source.ply"))
    target = o3d.io.read_point_cloud(str(out_dir / "target.ply"))
    source = _estimate_normals(source)
    target = _estimate_normals(target)

    t0 = time.perf_counter()
    icp = reg.registration_icp(
        source, target,
        0.04,  # max_correspondence_distance
        np.eye(4),
        estimation_method=reg.TransformationEstimationPointToPlane(),
        criteria=reg.ICPConvergenceCriteria(max_iteration=100, relative_fitness=1e-6, relative_rmse=1e-6),
    )
    elapsed = time.perf_counter() - t0

    est_T = np.asarray(icp.transformation, dtype=np.float64)
    fitness = float(icp.fitness)

    # 3. 评测（复用 evaluate.py）
    T_gt_loaded = evaluate.load_transform(str(out_dir / "gt_transform.npy"))
    rot_err = evaluate.rotation_error_deg(est_T, T_gt_loaded)
    trans_err = evaluate.translation_error(est_T, T_gt_loaded)
    passed = (rot_err < rot_max) and (fitness >= fitness_min)

    record = {
        "level": level_name,
        "seed": seed,
        "rot_err_deg": rot_err,
        "trans_err": trans_err,
        "fitness": fitness,
        "elapsed_sec": elapsed,
        "rot_max_deg": rot_max,
        "fitness_min": fitness_min,
        "passed": passed,
    }
    return record


# ---------------------------------------------------------------------------
# Markdown 汇总
# ---------------------------------------------------------------------------


def format_markdown_table(records: List[Dict[str, Any]]) -> str:
    """把各关结果渲染成 Markdown 表。"""
    header = ("| 关卡 | 旋转误差(°) | 平移误差 | fitness | 耗时(s) | "
              "阈值(rot<° & fitness) | 达标 |")
    sep = "|------|------------|---------|---------|---------|----------------------|------|"
    rows = [header, sep]
    for r in records:
        verdict = "PASS" if r["passed"] else "FAIL"
        rows.append(
            f"| {r['level']} | {r['rot_err_deg']:.4f} | {r['trans_err']:.4f} | "
            f"{r['fitness']:.4f} | {r['elapsed_sec']:.2f} | "
            f"<{r['rot_max_deg']}° & >{r['fitness_min']} | {verdict} |"
        )
    return "\n".join(rows)


def main() -> int:
    root = _PROJECT_ROOT
    cfg_dir = root / "configs"
    out_root = root / "outputs"
    out_root.mkdir(parents=True, exist_ok=True)

    levels = ["L1", "L2", "L3", "L4"]
    records: List[Dict[str, Any]] = []
    for lv in levels:
        cfg_path = cfg_dir / f"{lv}.yaml"
        if not cfg_path.exists():
            print(f"[skip] {cfg_path} not found")
            continue
        cfg = load_yaml_config(cfg_path)
        print(f"\n===== running {lv} =====")
        rec = run_level(lv, cfg, out_root)
        records.append(rec)
        print(f"  rot_err={rec['rot_err_deg']:.4f} deg  trans_err={rec['trans_err']:.4f}  "
              f"fitness={rec['fitness']:.4f}  elapsed={rec['elapsed_sec']:.2f}s  "
              f"passed={rec['passed']}")

    # 写 CSV
    csv_path = out_root / "baseline_results.csv"
    cols = ["level", "seed", "rot_err_deg", "trans_err", "fitness",
            "elapsed_sec", "rot_max_deg", "fitness_min", "passed"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({k: r[k] for k in cols})
    print(f"\n[wrote] {csv_path}")

    # 打印 Markdown 汇总表
    print("\n" + "=" * 60)
    print("## 基准汇总表")
    print(format_markdown_table(records))
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
