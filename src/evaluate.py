"""刚体配准评测工具。

仅依赖 numpy，用于对 Open3D 配准结果变换矩阵做旋转/平移误差评测，
并提供 case 目录批量评测、结果保存与内置自测留证。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\evaluate.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np


class InvalidTransformError(ValueError):
    """4x4 齐次变换矩阵不合法时抛出。"""


def load_transform(path: str) -> np.ndarray:
    """从 .npy 文件加载 4x4 齐次变换矩阵。

    Args:
        path: npy 文件路径。

    Returns:
        float64 的 4x4 变换矩阵。

    Raises:
        InvalidTransformError: 文件不存在、无法加载、形状错误或非齐次变换。
    """
    p = Path(path)
    if not p.exists():
        raise InvalidTransformError(f"变换文件不存在：{path}")

    M = np.asarray(np.load(p), dtype=np.float64)
    _validate_transform(M, source=str(path))
    return M


def _validate_transform(T: np.ndarray, source: str = "") -> None:
    """校验输入是否为合法 4x4 齐次变换矩阵。

    校验规则：
      1. 形状必须为 (4, 4)。
      2. 旋转部分 R 满足正交性：R.T @ R ≈ I。
      3. 齐次最后一行必须近似为 [0, 0, 0, 1]。

    Args:
        T: 待校验矩阵。
        source: 异常信息来源说明。

    Raises:
        InvalidTransformError: 校验失败时抛出。
    """
    src = f"（来源：{source}）" if source else ""
    if T.shape != (4, 4):
        raise InvalidTransformError(f"变换矩阵形状必须是 4x4，实际为 {T.shape}{src}")

    R = T[:3, :3]
    ortho_err = float(np.max(np.abs(R.T @ R - np.eye(3))))
    if ortho_err > 1e-8:
        raise InvalidTransformError(f"旋转部分不满足正交性，max|R^T R - I| = {ortho_err:.3e}{src}")

    last_row = T[3, :]
    expected_last_row = np.array([0.0, 0.0, 0.0, 1.0])
    if float(np.max(np.abs(last_row - expected_last_row))) > 1e-8:
        raise InvalidTransformError(f"齐次行不符合 [0,0,0,1]，实际为 {last_row}{src}")


def rotation_error_deg(T_est: np.ndarray, T_gt: np.ndarray) -> float:
    """用旋转矩阵迹法计算旋转误差（度）。

    数学公式：
        θ = arccos((tr(R_est^T R_gt) - 1) / 2)

    该公式等价于估计旋转与真值旋转之间的最小相对旋转角。

    Args:
        T_est: 估计的 4x4 变换矩阵。
        T_gt: 真值 4x4 变换矩阵。

    Returns:
        旋转误差，单位：度。

    Raises:
        InvalidTransformError: 输入不是合法 4x4 齐次变换矩阵。
    """
    T_est = np.asarray(T_est, dtype=np.float64)
    T_gt = np.asarray(T_gt, dtype=np.float64)
    _validate_transform(T_est, source="T_est")
    _validate_transform(T_gt, source="T_gt")

    R_est = T_est[:3, :3]
    R_gt = T_gt[:3, :3]

    # 相对旋转：R_rel = R_est^T R_gt
    R_rel = R_est.T @ R_gt
    trace_val = float(np.trace(R_rel))

    # 浮点误差可能导致 trace_val 超出合法范围，需要先截断。
    cos_theta = (trace_val - 1.0) / 2.0
    cos_theta = float(np.clip(cos_theta, -1.0, 1.0))

    theta_rad = float(np.arccos(cos_theta))
    return float(np.rad2deg(theta_rad))


def translation_error(T_est: np.ndarray, T_gt: np.ndarray) -> float:
    """计算平移向量的欧氏距离。

    Args:
        T_est: 估计的 4x4 变换矩阵。
        T_gt: 真值 4x4 变换矩阵。

    Returns:
        平移误差：||t_est - t_gt||_2

    Raises:
        InvalidTransformError: 输入不是合法 4x4 齐次变换矩阵。
    """
    T_est = np.asarray(T_est, dtype=np.float64)
    T_gt = np.asarray(T_gt, dtype=np.float64)
    _validate_transform(T_est, source="T_est")
    _validate_transform(T_gt, source="T_gt")

    t_est = T_est[:3, 3]
    t_gt = T_gt[:3, 3]
    return float(np.linalg.norm(t_est - t_gt))


def judge_success(metrics: Dict[str, Any], rot_thr_deg: float = 5.0, trans_thr: float = 0.05) -> bool:
    """根据双阈值判定配准是否成功。

    Args:
        metrics: 至少包含 rot_err_deg 与 trans_err。
        rot_thr_deg: 旋转误差阈值（度）。
        trans_thr: 平移误差阈值。

    Returns:
        True 当且仅当旋转误差 < 阈值且平移误差 < 阈值。

    Raises:
        KeyError: metrics 缺少必需字段。
    """
    rot_err = float(metrics["rot_err_deg"])
    trans_err = float(metrics["trans_err"])
    return rot_err < rot_thr_deg and trans_err < trans_thr


def evaluate_case(
    result_transform: np.ndarray,
    gt_path: str,
    rot_thr_deg: float = 5.0,
    trans_thr: float = 0.05,
) -> Dict[str, Any]:
    """评测单个 case 的配准结果。

    Args:
        result_transform: 待评测的 4x4 配准结果变换矩阵。
        gt_path: 真值变换矩阵 npy 文件路径。
        rot_thr_deg: 旋转误差阈值。
        trans_thr: 平移误差阈值。

    Returns:
        包含 rot_err_deg、trans_err、success、timestamp、rot_thr_deg、trans_thr、gt_path 的字典。
    """
    T_gt = load_transform(gt_path)
    T_est = np.asarray(result_transform, dtype=np.float64)
    _validate_transform(T_est, source="result_transform")

    rot_err = rotation_error_deg(T_est, T_gt)
    trans_err = translation_error(T_est, T_gt)
    success = judge_success({"rot_err_deg": rot_err, "trans_err": trans_err}, rot_thr_deg, trans_thr)

    return {
        "rot_err_deg": rot_err,
        "trans_err": trans_err,
        "success": success,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "rot_thr_deg": float(rot_thr_deg),
        "trans_thr": float(trans_thr),
        "gt_path": str(gt_path),
    }


def evaluate_case_dir(
    case_dir: str,
    result_transform: np.ndarray,
    rot_thr_deg: float = 5.0,
    trans_thr: float = 0.05,
) -> Dict[str, Any]:
    """适配 make_data.py 生成的 case 目录进行评测。

    要求目录内存在：
      - gt_transform.npy
      - meta.json（若缺失则填充空 meta）

    Args:
        case_dir: case 目录路径。
        result_transform: 待评测变换矩阵。
        rot_thr_deg: 旋转阈值。
        trans_thr: 平移阈值。

    Returns:
        在 evaluate_case 结果基础上追加 case_dir 与 meta。
    """
    cd = Path(case_dir)
    gt_path = cd / "gt_transform.npy"
    meta_path = cd / "meta.json"

    if not gt_path.exists():
        raise InvalidTransformError(f"case 目录缺少真值变换文件：{gt_path}")

    base = evaluate_case(result_transform, str(gt_path), rot_thr_deg, trans_thr)
    base["case_dir"] = str(cd)

    if meta_path.exists():
        base["meta"] = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        base["meta"] = {}

    return base


def save_result(metrics: Dict[str, Any], out_path: str) -> None:
    """将评测结果保存为 JSON。

    Args:
        metrics: 评测结果字典。
        out_path: 输出 JSON 路径。
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    def _default(o: Any) -> Any:
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=_default), encoding="utf-8")


def _build_rotation_matrix(az_deg: float, ay_deg: float = 0.0, ax_deg: float = 0.0) -> np.ndarray:
    """构造 3x3 旋转矩阵 R = Rz @ Ry @ Rx。"""
    ax, ay, az = np.deg2rad(ax_deg), np.deg2rad(ay_deg), np.deg2rad(az_deg)
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)

    Rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    Ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    Rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return Rz @ Ry @ Rx


def _build_transform(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """构造 4x4 齐次变换矩阵。"""
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def _run_self_tests() -> Dict[str, Any]:
    """运行全部自测，并返回结果字典。"""
    results: Dict[str, Any] = {}
    tol = 1e-6

    # 1. 单位阵互测
    I = np.eye(4)
    r1 = rotation_error_deg(I, I)
    t1 = translation_error(I, I)
    ok1 = abs(r1 - 0.0) < tol and abs(t1 - 0.0) < tol
    results["identity"] = {
        "rot_err_deg": r1,
        "trans_err": t1,
        "expected_rot_deg": 0.0,
        "expected_trans": 0.0,
        "passed": ok1,
    }

    # 2. 纯旋转 30° 绕 Z
    R30 = _build_rotation_matrix(az_deg=30.0)
    T30 = _build_transform(R30, np.zeros(3))
    r2 = rotation_error_deg(T30, I)
    t2 = translation_error(T30, I)
    ok2 = abs(r2 - 30.0) < tol and abs(t2 - 0.0) < tol
    results["pure_rotation_30_z"] = {
        "rot_err_deg": r2,
        "trans_err": t2,
        "expected_rot_deg": 30.0,
        "expected_trans": 0.0,
        "passed": ok2,
    }

    # 3. 纯平移 [0.5, 0.3, 0.2]
    tv = np.array([0.5, 0.3, 0.2])
    T_trans = _build_transform(np.eye(3), tv)
    r3 = rotation_error_deg(T_trans, I)
    t3 = translation_error(T_trans, I)
    expected_trans3 = float(np.linalg.norm(tv))
    ok3 = abs(r3 - 0.0) < tol and abs(t3 - expected_trans3) < tol
    results["pure_translation"] = {
        "rot_err_deg": r3,
        "trans_err": t3,
        "expected_rot_deg": 0.0,
        "expected_trans": expected_trans3,
        "passed": ok3,
    }

    # 4. 组合变换：绕Z旋转30° + 平移 [0.2, 0.1, 0.3]
    R_comb = _build_rotation_matrix(az_deg=30.0)
    t_comb = np.array([0.2, 0.1, 0.3])
    T_comb = _build_transform(R_comb, t_comb)
    r4 = rotation_error_deg(T_comb, I)
    t4 = translation_error(T_comb, I)
    expected_trans4 = float(np.linalg.norm(t_comb))
    ok4 = abs(r4 - 30.0) < tol and abs(t4 - expected_trans4) < tol
    results["combined"] = {
        "rot_err_deg": r4,
        "trans_err": t4,
        "expected_rot_deg": 30.0,
        "expected_trans": expected_trans4,
        "passed": ok4,
    }

    results["tolerance"] = tol
    results["all_passed"] = all(v["passed"] for v in results.values() if isinstance(v, dict) and "passed" in v)
    return results


def _print_and_save_test_report(results: Dict[str, Any], out_path: Path) -> None:
    """打印自测结果并保存到指定文本文件。"""
    lines = [
        "evaluate.py self test report",
        f"generated_at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
        f"tolerance: {results['tolerance']}",
        "",
    ]
    for name, v in results.items():
        if not isinstance(v, dict) or "passed" not in v:
            continue
        status = "PASS" if v["passed"] else "FAIL"
        lines.append(f"[{status}] {name}")
        lines.append(f"  rot_err_deg = {v['rot_err_deg']:.10f} (expected {v['expected_rot_deg']})")
        lines.append(f"  trans_err   = {v['trans_err']:.10f} (expected {v['expected_trans']})")
        lines.append("")

    lines.append(f"all_passed: {results['all_passed']}")

    text = "\n".join(lines)
    print(text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")


def main() -> int:
    """默认入口：运行自测，并保存评审证据文件。"""
    results = _run_self_tests()
    project_root = Path(__file__).resolve().parents[1]
    out_file = project_root / "outputs" / "evaluate_test.txt"
    _print_and_save_test_report(results, out_file)
    print(f"[saved] {out_file}")
    return 0 if results["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
