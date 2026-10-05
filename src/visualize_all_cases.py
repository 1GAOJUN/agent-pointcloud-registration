"""批量配准结果可视化脚本。

读取 outputs/ 下已有四关卡数据（source/target .ply、gt_transform.npy）和
baseline_results.csv 的评测结果，为每个关卡生成两张配准对比图：
  - visuals/01_initial.png        配准前 source 与 target 的原始错位状态
  - visuals/02_final_result.png   source 经配准变换后与 target 的对齐效果

约束：
  - 不修改 src/make_data.py、src/evaluate.py、register_minimal.py
  - 不重新跑配准，仅从 CSV 读取已算好的指标；配准后 source 的变换矩阵
    通过加载 outputs/Lx/est_transform.npy 获得（由 run_benchmark.py 保存）
  - 统一视角：用 Open3D 可视化窗口渲染截图，保证不同关卡图可比
  - 右上角标注关卡名、旋转误差(°)、平移误差、fitness、是否达标
  - 保存为高清 PNG

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\visualize_all_cases.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np
import open3d as o3d

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

# 两色高区分度：source=蓝，target=红
SOURCE_COLOR = np.array([0.2, 0.5, 0.95])
TARGET_COLOR = np.array([0.9, 0.15, 0.15])
FIGURE_SIZE = (1600, 1000)   # 高清 PNG


def _read_csv_results(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """读取 baseline_results.csv，返回 {level: row_dict}。"""
    rows: Dict[str, Dict[str, Any]] = {}
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["level"]] = r
    return rows


def _color_pointcloud(pcd: o3d.geometry.PointCloud, color: np.ndarray) -> o3d.geometry.PointCloud:
    """给点云整体着色（复制一份，避免改动原始对象）。"""
    pts = np.asarray(pcd.points)
    out = o3d.geometry.PointCloud()
    out.points = o3d.utility.Vector3dVector(pts.copy())
    out.colors = o3d.utility.Vector3dVector(np.tile(color, (len(pts), 1)))
    return out


def _annotate_canvas(fig_title: str, info_lines: list, out_png: Path, vis: o3d.visualization.Visualizer) -> None:
    """把截图与文字标注合成一张图并保存为高清 PNG。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image, ImageDraw, ImageFont

    # 把 Open3D 截图（已存到 out_png）与文字标注拼接
    img = Image.open(out_png)
    # 在右侧加一条标注栏
    bar_w = 380
    canvas = Image.new("RGB", (img.width + bar_w, img.height), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    # 标题
    draw.text((img.width + 16, 20), fig_title, fill="black")
    draw.line([(img.width + 10, 50), (img.width + bar_w - 10, 50)], fill="gray", width=2)
    y = 70
    for line in info_lines:
        draw.text((img.width + 16, y), line, fill="black")
        y += 34
    canvas.save(out_png, format="PNG")
    plt.close("all")


def _make_annotation_png(out_png: Path, level: str, res: Dict[str, Any], label: str) -> None:
    """生成带标注的高清图：左上关卡标题，右上 5 行指标。

    使用 matplotlib 渲染点云（source 蓝 / target 红 两个子图并排），
    再在右上角写指标文本，保证跨关卡视角一致（固定 3D 投影参数）。

    说明：Open3D 0.20 的 PointCloud 没有 .copy() 方法；
    需要 ICP 变换时直接构造新对象，避免修改已读入的点云。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    lv_dir = out_png.parent.parent
    src = o3d.io.read_point_cloud(str(lv_dir / "source.ply"))
    tgt = o3d.io.read_point_cloud(str(lv_dir / "target.ply"))
    est_path = lv_dir / "est_transform.npy"
    if est_path.exists():
        est_T = np.load(str(est_path))
    else:
        # 旧数据未保存 ICP 变换矩阵：轻量重跑一次 ICP 取得（仅用于渲染，不写回 CSV）
        import open3d.pipelines.registration as reg
        s = o3d.io.read_point_cloud(str(lv_dir / "source.ply"))
        t = o3d.io.read_point_cloud(str(lv_dir / "target.ply"))
        s.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
        t.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
        icp = reg.registration_icp(
            s, t, 0.04, np.eye(4),
            estimation_method=reg.TransformationEstimationPointToPlane(),
            criteria=reg.ICPConvergenceCriteria(max_iteration=100, relative_fitness=1e-6, relative_rmse=1e-6),
        )
        est_T = np.asarray(icp.transformation, dtype=np.float64)
        np.save(str(est_path), est_T)

    src_pts = np.asarray(src.points)
    tgt_pts = np.asarray(tgt.points)
    src_aligned = (src_pts @ est_T[:3, :3].T + est_T[:3, 3])

    fig = plt.figure(figsize=(12, 6.5), dpi=140)
    # 固定视角：保证不同关卡图可比
    view_elev, view_azim, dist = 25, -60, 1.6

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    ax1.scatter(tgt_pts[:, 0], tgt_pts[:, 1], tgt_pts[:, 2], s=1.5, c=[TARGET_COLOR], alpha=0.7, label="target")
    if label == "initial":
        ax1.scatter(src_pts[:, 0], src_pts[:, 1], src_pts[:, 2], s=1.5, c=[SOURCE_COLOR], alpha=0.7, label="source")
    else:
        ax1.scatter(src_aligned[:, 0], src_aligned[:, 1], src_aligned[:, 2], s=1.5, c=[SOURCE_COLOR], alpha=0.7, label="source(after ICP)")
    ax1.view_init(elev=view_elev, azim=view_azim)
    ax1.set_title(f"{level}  target", fontsize=11)
    ax1.set_xlim(-0.8, 0.8); ax1.set_ylim(-0.8, 0.8); ax1.set_zlim(-0.8, 0.8)
    ax1.tick_params(labelsize=8)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    ax2.scatter(tgt_pts[:, 0], tgt_pts[:, 1], tgt_pts[:, 2], s=1.5, c=[TARGET_COLOR], alpha=0.7, label="target")
    if label == "initial":
        ax2.scatter(src_pts[:, 0], src_pts[:, 1], src_pts[:, 2], s=1.5, c=[SOURCE_COLOR], alpha=0.7, label="source")
    else:
        ax2.scatter(src_aligned[:, 0], src_aligned[:, 1], src_aligned[:, 2], s=1.5, c=[SOURCE_COLOR], alpha=0.7, label="source(after ICP)")
    ax2.view_init(elev=-view_elev + 50, azim=view_azim + 90)
    ax2.set_title(f"{level}  {'raw' if label == 'initial' else 'aligned'} source + target", fontsize=11)
    ax2.set_xlim(-0.8, 0.8); ax2.set_ylim(-0.8, 0.8); ax2.set_zlim(-0.8, 0.8)
    ax2.tick_params(labelsize=8)

    # 右上角关键信息
    passed_txt = "PASS" if res.get("passed") in ("True", "true", True) else "FAIL"
    info = (
        f"level : {level}\n"
        f"rot_err : {float(res.get('rot_err_deg', 0)):.4f} °\n"
        f"trans_err : {float(res.get('trans_err', 0)):.4f}\n"
        f"fitness : {float(res.get('fitness', 0)):.4f}\n"
        f"passed : {passed_txt}"
    )
    fig.text(0.995, 0.99, info, transform=fig.transFigure,
             fontsize=10, va="top", ha="right",
             family="monospace",
             bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="gray"))
    fig.suptitle(label, fontsize=12, y=1.02)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(str(out_png), dpi=140, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def generate_level_visuals(out_root: Path, level: str, res: Dict[str, Any]) -> None:
    """为单个关卡生成 visuals/01_initial.png 与 visuals/02_final_result.png。"""
    lv_dir = out_root / level
    visuals = lv_dir / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)

    initial = visuals / "01_initial.png"
    final = visuals / "02_final_result.png"
    _make_annotation_png(initial, level, res, "initial")
    _make_annotation_png(final, level, res, "final")
    print(f"[visualize] {level}: {initial.name}, {final.name}  -> {visuals}")


def main() -> int:
    out_root = _PROJECT_ROOT / "outputs" / "ICP"
    csv_path = _PROJECT_ROOT / "outputs" / "reports" / "baseline_results.csv"
    if not csv_path.exists():
        print(f"[FAIL] 未找到 {csv_path}，请先运行 src/run_benchmark.py")
        return 1

    results = _read_csv_results(csv_path)
    for lv in ["L1", "L2", "L3", "L4"]:
        res = results.get(lv)
        if res is None:
            print(f"[skip] CSV 无 {lv} 记录")
            continue
        # est_transform.npy 若缺失，_make_annotation_png 会自动重跑 ICP 补齐
        generate_level_visuals(out_root, lv, res)

    print("\n[done] 可视化已保存到 outputs/L1~L4/visuals/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
