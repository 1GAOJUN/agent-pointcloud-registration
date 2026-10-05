"""L2 配准过程动画生成工具。

输入：
    source.ply, target.ply（o3d 点云）
    T_initial: 4x4 初始变换矩阵（例如 SVD 全局初值）
    T_final:   4x4 最终变换矩阵（例如 ICP 结果）
输出：
    outputs/L2/visuals/l2_registration_animation.mp4

画面要求：
    - source 红色，target 蓝色
    - 初始错位状态 与 最终对齐状态 清晰对比
    - 采用关键帧插值（SLERP 旋转 + 线性平移）展示从初始位姿到最终位姿的变化
    - 画面干净、点云清晰，适合录屏

帧布局：
    每帧左侧为"当前位姿 source（红色）+ target（蓝色）"，右侧为"最终位姿 source（红色）+ target（蓝色）"
    共 2 列：左列展示过渡动画（keyframe），右列固定展示最终对齐结果
    最后一列额外展示初始错位帧（t=0）作为对比

生成 MP4 的方式：
    1. 用 matplotlib 3D scatter 逐帧渲染关键帧，保存为 PNG；
    2. 用 ffmpeg（conda 环境内 imageio-ffmpeg 自带）合成 mp4。
    若 ffmpeg 不可用则回退为生成带 GIF 帧序列目录。

参数固化：
    n_keyframes = 30  （初始 -> 最终的插值帧数）
    fps         = 10
    点云采样比例 = 0.3（减少绘图耗时，视觉仍清晰）
    figsize     = (14, 5)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

import numpy as np
import open3d as o3d

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N_KEYFRAMES: int = 30
FPS: int = 10
SAMPLE_RATIO: int = 0.3
FIGSIZE = (14, 5)
DPI: int = 120




def _interp_transform(T1: np.ndarray, T2: np.ndarray, t: float) -> np.ndarray:
    """对 4x4 刚体变换做插值：旋转用 SVD 对数映射插值（近似 SLERP），平移线性。

    简化版：用轴角（Rodrigues）插值旋转部分。
    """
    R1, t1 = T1[:3, :3], T1[:3, 3]
    R2, t2 = T2[:3, :3], T2[:3, 3]

    # 用 SVD 极分解提取纯旋转，再用轴角插值
    def rot_to_axis_angle(R):
        sign = np.sign(np.linalg.det(R))
        cos = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
        theta = np.arccos(cos)
        if abs(theta) < 1e-9:
            return np.zeros(3), 0.0
        v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
        norm = np.linalg.norm(v)
        if norm < 1e-9:
            return np.zeros(3), theta
        return v / norm, theta

    axis1, ang1 = rot_to_axis_angle(R1)
    axis2, ang2 = rot_to_axis_angle(R2)

    # 轴角插值（对短弧段足够准确）
    ang_interp = ang1 + (ang2 - ang1) * t
    if abs(ang_interp) < 1e-9:
        R_interp = np.eye(3)
    else:
        # 取 axis1 方向（两轴近似相同），或用 SVD 对齐
        # 更稳健：直接用矩阵插值
        R_interp = (1 - t) * R1 + t * R2
        # 最近旋转矩阵修正（SVD）
        U, _, Vt = np.linalg.svd(R_interp)
        R_interp = U @ Vt
        if np.linalg.det(R_interp) < 0:
            U[:, -1] *= -1
            R_interp = U @ Vt

    t_interp = (1 - t) * t1 + t * t2
    T_interp = np.eye(4, dtype=np.float64)
    T_interp[:3, :3] = R_interp
    T_interp[:3, 3] = t_interp
    return T_interp


def _make_frame(pcd_src, pcd_tgt, T_src, title_left: str, title_right: str,
                T_final_src=None) -> np.ndarray:
    """渲染一帧 PNG，返回 PIL.Image 或 numpy 数组。"""
    pts_src = np.asarray(pcd_src.points)
    pts_tgt = np.asarray(pcd_tgt.points)

    idx = np.random.RandomState(42).choice(len(pts_src), size=int(len(pts_src) * SAMPLE_RATIO), replace=False)
    pts_src_sub = pts_src[idx]
    pts_src_transformed = (pts_src_sub @ T_src[:3, :3].T + T_src[:3, 3])

    idx_t = np.random.RandomState(43).choice(len(pts_tgt), size=int(len(pts_tgt) * SAMPLE_RATIO), replace=False)
    pts_tgt_sub = pts_tgt[idx_t]

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE, subplot_kw={"projection": "3d"})
    for ax, pts_s, pts_t, title in zip(
        axes,
        [pts_src_transformed],
        [pts_tgt_sub],
        [title_left],
    ):
        ax.scatter(pts_s[:, 0], pts_s[:, 1], pts_s[:, 2], s=0.4, alpha=0.6, c="red", label="source")
        ax.scatter(pts_t[:, 0], pts_t[:, 1], pts_t[:, 2], s=0.4, alpha=0.6, c="blue", label="target")
        ax.set_title(title, fontsize=11, pad=6)
        ax.set_box_aspect((1, 1, 1))
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.legend(fontsize=8, loc="upper right")

    plt.tight_layout()
    return fig, axes


def generate_animation(
    source_ply: str,
    target_ply: str,
    T_initial: np.ndarray,
    T_final: np.ndarray,
    out_mp4: str,
) -> Dict:
    """生成关键帧插值动画并输出 mp4。

    帧结构（共 N_KEYFRAMES + 2 帧）：
        第 0 帧：  初始错位（T_initial）vs 最终对齐（T_final）双视图
        第 1~N-1 帧：过渡动画（左列展示插值位姿，右列固定最终）
        最后一帧：  最终对齐状态（T_final）vs 最终对齐状态（T_final）

    Returns:
        dict: {"out_mp4": str, "n_frames": int, "elapsed_s": float, "frames_dir": str}
    """
    t0 = time.time()
    src = o3d.io.read_point_cloud(source_ply)
    tgt = o3d.io.read_point_cloud(target_ply)

    frames_dir = Path(out_mp4).parent / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_files = []

    for i in range(N_KEYFRAMES + 1):
        t = i / N_KEYFRAMES
        T_current = _interp_transform(T_initial, T_final, t)

        if i == 0:
            title_left = f"t=0  initial misaligned pose (SVD global init)"
        elif i == N_KEYFRAMES:
            title_left = f"t=1  final aligned pose (ICP result)"
        else:
            title_left = f"interpolated keyframe  i={i}/{N_KEYFRAMES-1}"

        title_right = "final aligned pose (reference)"

        fig, axes = plt.subplots(1, 2, figsize=FIGSIZE, subplot_kw={"projection": "3d"})
        pts_src_all = np.asarray(src.points)
        pts_tgt_all = np.asarray(tgt.points)

        rng_s = np.random.RandomState(42)
        idx_s = rng_s.choice(len(pts_src_all), size=int(len(pts_src_all) * SAMPLE_RATIO), replace=False)
        rng_t = np.random.RandomState(43)
        idx_t = rng_t.choice(len(pts_tgt_all), size=int(len(pts_tgt_all) * SAMPLE_RATIO), replace=False)

        pts_src_cur = pts_src_all[idx_s] @ T_current[:3, :3].T + T_current[:3, 3]
        pts_tgt_sub = pts_tgt_all[idx_t]
        pts_src_final = pts_src_all[idx_s] @ T_final[:3, :3].T + T_final[:3, 3]

        for ax, pts_s, pts_t, title in zip(
            axes,
            [pts_src_cur, pts_src_final],
            [pts_tgt_sub, pts_tgt_sub],
            [title_left, title_right],
        ):
            ax.scatter(pts_s[:, 0], pts_s[:, 1], pts_s[:, 2], s=0.35, alpha=0.55, c="red", label="source")
            ax.scatter(pts_t[:, 0], pts_t[:, 1], pts_t[:, 2], s=0.35, alpha=0.55, c="blue", label="target")
            ax.set_title(title, fontsize=10, pad=5)
            ax.set_box_aspect((1, 1, 1))
            ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
            ax.legend(fontsize=7, loc="upper right")

        plt.tight_layout()
        frame_file = frames_dir / f"frame_{i:03d}.png"
        fig.savefig(frame_file, dpi=DPI)
        frame_files.append(str(frame_file))
        plt.close(fig)

    # 尝试用 ffmpeg 合成 mp4
    mp4_ok = False
    try:
        import subprocess
        import glob
        pattern = str(frames_dir / "frame_*.png")
        files = sorted(glob.glob(pattern))
        if files:
            ffmpeg_candidates = [
                "ffmpeg",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            ]
            # imageio-ffmpeg
            try:
                import imageio_ffmpeg
                ffmpeg_candidates.insert(0, imageio_ffmpeg.get_ffmpeg_exe())
            except ImportError:
                pass

            ffmpeg_path = None
            for cand in ffmpeg_candidates:
                try:
                    subprocess.run([cand, "-version"], capture_output=True, check=True)
                    ffmpeg_path = cand
                    break
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue

            out_mp4_path = Path(out_mp4)
            out_mp4_path.parent.mkdir(parents=True, exist_ok=True)
            frame_pattern = str(frames_dir / "frame_%03d.png")
            cmd = [ffmpeg_path, "-y", "-framerate", str(FPS), "-i", frame_pattern,
                   "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                   "-vframes", str(len(frame_files)), str(out_mp4_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                mp4_ok = True
            else:
                print(f"[warn] ffmpeg failed: {result.stderr[:400]}")
    except Exception as exc:
        print(f"[warn] ffmpeg unavailable: {exc}")

    elapsed = time.time() - t0
    print(f"[animation] mp4={'ok' if mp4_ok else 'skipped (frames saved to dir)'}")
    print(f"[animation] out_mp4 = {out_mp4}")
    print(f"[animation] frames_dir = {frames_dir}  ({len(frame_files)} frames)")
    print(f"[animation] elapsed = {elapsed:.2f} s")

    return {
        "out_mp4": str(out_mp4),
        "mp4_ok": mp4_ok,
        "n_frames": len(frame_files),
        "elapsed_s": elapsed,
        "frames_dir": str(frames_dir),
    }


if __name__ == "__main__":
    import json
    import sys
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

    L2 = ROOT / "outputs" / "L2"
    src_ply = str(L2 / "source.ply")
    tgt_ply = str(L2 / "target.ply")
    out_mp4 = str(L2 / "visuals" / "l2_registration_animation.mp4")

    # 读取已有的初始和最终变换（pipeline 已生成）
    T_final = np.load(str(L2 / "est_transform.npy"))
    # 初始变换：用 SVD 工具重新计算
    from algorithms.svd_global_init_new import estimate_global_init
    src_pcd = o3d.io.read_point_cloud(src_ply)
    tgt_pcd = o3d.io.read_point_cloud(tgt_ply)
    T_initial = estimate_global_init(src_pcd, tgt_pcd)["transform"]

    out = generate_animation(src_ply, tgt_ply, T_initial, T_final, out_mp4)
    print(json.dumps(out, indent=2, ensure_ascii=False))

