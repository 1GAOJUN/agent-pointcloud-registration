"""最小点云诊断工具：把 source/target PLY 转成结构化、GT-free 观测。

只计算当前可可靠得到的指标；无可靠实现的项写 NOT_IMPLEMENTED，不伪造。
绝不读取 gt_transform / 场景标签 / level。

说明（Open3D 0.20.0 适配）：
- 本环境 KDTreeFlann.search_vector_3d 对单点 KNN 查询不稳定（RuntimeError），
  因此最近邻中位间距改用 numpy 向量化实现：
  对（可采样后的）点集求每个点的最近邻距离（排除自身），取中位数。
- 若数据量大，用固定 sampling_seed 采样，并在结果中记录 sample_size / sampling_seed。
"""

from __future__ import annotations

import json
from typing import Any, Dict

import numpy as np
import open3d as o3d

K_SPACING = 8          # k-近邻间距统计所用 k
SAMPLE_LIMIT = 5000    # 最近邻间距计算采样点数上限
SAMPLING_SEED = 101    # 固定采样种子，保证可复现


def _bbox_diagonal(pts: np.ndarray) -> float:
    return float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0)))


def _nearest_neighbor_stats(pts: np.ndarray) -> Dict[str, Any]:
    """确定性最近邻距离统计（排除自身），只作 Observation，不作方法选择。"""
    pts = np.ascontiguousarray(pts, dtype=np.float64)
    n = len(pts)
    if n < 2:
        return {
            "sample_size": n,
            "median": None,
            "p90": None,
            "p95": None,
            "mad": None,
            "high_distance_threshold": None,
            "high_distance_ratio_proxy": None,
        }
    if n > SAMPLE_LIMIT:
        rng = np.random.RandomState(SAMPLING_SEED)
        idx = rng.choice(n, size=SAMPLE_LIMIT, replace=False)
        pts = pts[idx]
        n = len(pts)

    dists = np.empty(n, dtype=np.float64)
    block = 512
    for s in range(0, n, block):
        q = pts[s:s + block]            # (m, 3)
        m = q.shape[0]
        d2 = ((q[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)  # (m, n)
        # 把“自身”置为 inf：q 的 j 行对应全局索引 s + j
        d2[np.arange(m), s + np.arange(m)] = np.inf
        dists[s:s + m] = np.sqrt(d2.min(axis=1))
    median = float(np.median(dists))
    mad = float(np.median(np.abs(dists - median)))
    # 1.4826*MAD 是稳健 sigma 估计；高距离比例只是明显稀疏/孤立点代理，不是真实 outlier 标签。
    threshold = float(median + 3.0 * 1.4826 * mad)
    return {
        "sample_size": int(n),
        "median": median,
        "p90": float(np.percentile(dists, 90)),
        "p95": float(np.percentile(dists, 95)),
        "mad": mad,
        "high_distance_threshold": threshold,
        "high_distance_ratio_proxy": float(np.mean(dists > threshold)),
    }


def _nearest_neighbor_distance(pts: np.ndarray) -> float:
    """兼容旧调用：返回稳健 NN 中位间距。"""
    value = _nearest_neighbor_stats(pts)["median"]
    return float(value) if value is not None else float("nan")


def diagnose(source_ply: str, target_ply: str) -> Dict[str, Any]:
    src = o3d.io.read_point_cloud(source_ply)
    tgt = o3d.io.read_point_cloud(target_ply)
    if src is None or tgt is None:
        raise ValueError(f"无法读取点云: {source_ply} / {target_ply}")

    sp = np.asarray(src.points, dtype=np.float64)
    tp = np.asarray(tgt.points, dtype=np.float64)

    src_nn = _nearest_neighbor_stats(sp)
    tgt_nn = _nearest_neighbor_stats(tp)
    src_spacing = float(src_nn["median"]) if src_nn["median"] is not None else float("nan")
    tgt_spacing = float(tgt_nn["median"]) if tgt_nn["median"] is not None else float("nan")

    density_ratio = None
    if (np.isfinite(src_spacing) and np.isfinite(tgt_spacing)
            and src_spacing > 0 and tgt_spacing > 0):
        density_ratio = float(tgt_spacing / src_spacing)  # >1 表示 target 更稀疏

    centroid_distance = float(np.linalg.norm(tp.mean(axis=0) - sp.mean(axis=0)))

    out: Dict[str, Any] = {
        "source_point_count": int(len(sp)),
        "target_point_count": int(len(tp)),
        "source_bbox_diagonal": _bbox_diagonal(sp),
        "target_bbox_diagonal": _bbox_diagonal(tp),
        "source_median_spacing": src_spacing,
        "target_median_spacing": tgt_spacing,
        "density_ratio": density_ratio,
        "point_count_ratio": float(len(tp) / len(sp)) if len(sp) else None,
        "bbox_diagonal_ratio": (
            float(_bbox_diagonal(tp) / _bbox_diagonal(sp))
            if len(sp) and _bbox_diagonal(sp) > 0 else None
        ),
        "nearest_neighbor_distance_stats": {
            "source": src_nn,
            "target": tgt_nn,
            "high_distance_ratio_delta": (
                float(tgt_nn["high_distance_ratio_proxy"] - src_nn["high_distance_ratio_proxy"])
                if (src_nn["high_distance_ratio_proxy"] is not None
                    and tgt_nn["high_distance_ratio_proxy"] is not None)
                else None
            ),
            "interpretation": (
                "Robust within-cloud spacing and isolated-point proxies only; "
                "not a ground-truth noise/outlier estimate and not an algorithm trigger."
            ),
        },
        "centroid_distance": centroid_distance,
        "initial_transform_available": True,
        "sample_size": min(len(sp), SAMPLE_LIMIT),
        "sampling_seed": SAMPLING_SEED,
        # 暂无可靠实现 -> NOT_IMPLEMENTED，不伪造
        "overlap_ratio": "NOT_IMPLEMENTED",
        "noise_level": "NOT_IMPLEMENTED",
        "outlier_level": "NOT_IMPLEMENTED",
        "rotation_magnitude_estimate": "NOT_IMPLEMENTED",
    }

    local_scale = src_spacing if np.isfinite(src_spacing) and src_spacing > 0 else 0.0
    global_scale = _bbox_diagonal(sp) / 50.0
    out["base_scale"] = float(max(local_scale, global_scale))
    return out


def main() -> None:
    import sys
    d = diagnose(sys.argv[1], sys.argv[2])
    print(json.dumps(d, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
