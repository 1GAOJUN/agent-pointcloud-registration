"""独立 Evaluator：仅在 Agent 已 ACCEPT/ABORT 之后才允许读取 GT。

- 复用 src/evaluate.py 的 rotation_error_deg / translation_error / judge_success。
- 读 gt_transform.npy 计算真实 GT 指标，与 Agent 自身的可观测指标严格区分。
- 机器标识符全为纯 ASCII；显示文本可用中文。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np


def evaluate_agent_result(
    est_transform: np.ndarray,
    gt_npy: str,
    rot_thr_deg: float = 5.0,
    trans_thr: float = 0.05,
) -> Dict[str, Any]:
    """读取 GT，计算最终配准质量的独立评测。仅在 Agent 决策后调用。"""
    # 延迟导入，确保只有真正到评测阶段才接触 GT 文件
    import sys
    src_dir = Path(__file__).resolve().parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from evaluate import (
        load_transform,
        rotation_error_deg,
        translation_error,
        judge_success,
        save_result,
    )

    T_gt = load_transform(gt_npy)
    T_est = np.asarray(est_transform, dtype=np.float64)
    rot_err = rotation_error_deg(T_est, T_gt)
    trans_err = translation_error(T_est, T_gt)
    success = judge_success(
        {"rot_err_deg": rot_err, "trans_err": trans_err}, rot_thr_deg, trans_thr
    )
    return {
        "gt_evaluator": True,
        "note": "GT 仅在此处读取；Agent 决策阶段不可见。",
        "rot_err_deg": float(rot_err),
        "trans_err": float(trans_err),
        "success": bool(success),
        "rot_thr_deg": float(rot_thr_deg),
        "trans_thr": float(trans_thr),
        "gt_path": str(gt_npy),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    }


def save_evaluator_result(metrics: Dict[str, Any], out_path: str) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=lambda o: o.item() if isinstance(o, np.generic) else o.tolist() if isinstance(o, np.ndarray) else o),
        encoding="utf-8",
    )
