"""合成与真实点云配准数据生成工具。

主用例：完全离线生成可控的 source/target 点云对，支持旋转、平移、噪声、离群点、裁剪退化，
并保存真值变换与元数据；扩展用例：可选使用 Open3D 内置/在线数据集生成真实点云。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\make_data.py
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import open3d as o3d

PY_EXE = r"D:\APP\Anaconda\envs\pointcloud_agh\python.exe"


def _seeded_rng(seed: int) -> np.random.RandomState:
    """设置全局 NumPy 随机种子并返回同一 seed 的 RandomState。"""
    np.random.seed(seed)
    return np.random.RandomState(seed)


@dataclass
class LevelConfig:
    """点云数据生成参数。

    参数说明：
        level: 难度标签，例如 L1。
        n_points: source 采样点数。
        rot_x/y/z_deg: 绕坐标轴旋转角度（度）。
        translation: 目标相对源点的平移向量 [x, y, z]。
        noise_sigma: 高斯噪声标准差；0 表示不加噪。
        outlier_ratio: 包围盒内均匀撒离群点比例；0 表示不撒离群点。
        crop_ratio: 裁剪比例，删除源点云包围盒中指定半空间点；0 表示不裁剪。
        crop_axis: 裁剪轴向，取 "x"、"y" 或 "z"。
        crop_sign: 删除半空间符号，"+z" 表示删除 z 最大侧，"-z" 表示删除 z 最小侧。
        dataset: 真实点云数据集名称；合成数据不使用该字段。
    """

    level: str = "L1"
    n_points: int = 30000
    rot_x_deg: float = 0.0
    rot_y_deg: float = 15.0
    rot_z_deg: float = 0.0
    translation: Tuple[float, float, float] = (0.3, 0.1, 0.2)
    noise_sigma: float = 0.0
    outlier_ratio: float = 0.0
    crop_ratio: float = 0.0
    crop_axis: str = "z"
    crop_sign: str = "+"
    dataset: Optional[str] = None

    @classmethod
    def from_dict(cls, level_config: Dict[str, Any]) -> "LevelConfig":
        """从普通 dict 构造配置，保留未知字段到 meta。"""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in level_config.items() if k in known}
        translation = kwargs.get("translation")
        if isinstance(translation, (list, tuple, np.ndarray)):
            kwargs["translation"] = tuple(float(x) for x in translation)
        return cls(**kwargs)

    def extra_fields(self, level_config: Dict[str, Any]) -> Dict[str, Any]:
        """返回配置 dict 中未进入 dataclass 的额外字段。"""
        known = {f.name for f in self.__dataclass_fields__.values()}
        return {k: v for k, v in level_config.items() if k not in known}


def rotation_matrix(euler_deg: Tuple[float, float, float]) -> np.ndarray:
    """绕 x/y/z 轴的内禀旋转矩阵（R = Rz @ Ry @ Rx）。"""
    ax, ay, az = (np.deg2rad(v) for v in euler_deg)
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def pose_transform(cfg: LevelConfig) -> np.ndarray:
    """构造 4x4 刚体变换矩阵。"""
    t = np.asarray(cfg.translation, dtype=np.float64).reshape(3)
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = rotation_matrix((cfg.rot_x_deg, cfg.rot_y_deg, cfg.rot_z_deg))
    T[:3, 3] = t
    return T


def make_source_pointcloud(cfg: LevelConfig, rng: np.random.RandomState, seed: int) -> o3d.geometry.PointCloud:
    """生成球体+偏移长方体+圆柱拼接体，并采样为原始源点云。"""
    sphere = o3d.geometry.TriangleMesh.create_sphere(radius=0.4)
    box = o3d.geometry.TriangleMesh.create_box(width=0.35, height=0.22, depth=0.18)
    cylinder = o3d.geometry.TriangleMesh.create_cylinder(radius=0.12, height=0.55)
    box.translate([0.42, 0.05, 0.0])
    box.rotate(np.array([[0.96592583, -0.25881905, 0.0], [0.25881905, 0.96592583, 0.0], [0.0, 0.0, 1.0]]))
    cylinder.translate([-0.35, -0.25, 0.0])
    assembly = o3d.geometry.TriangleMesh()
    for m in (sphere, box, cylinder):
        m.compute_vertex_normals()
        assembly += m

    n = max(int(cfg.n_points), 0)
    if n == 0:
        return o3d.geometry.PointCloud()
    pcd = assembly.sample_points_uniformly(number_of_points=n)
    # 颜色不进入配准真值，仅用于可视化；用固定 seed 生成以保证可复现。
    pcd.colors = o3d.utility.Vector3dVector(np.random.RandomState(seed + 101).rand(n, 3))
    return pcd


def _add_outliers(pcd: o3d.geometry.PointCloud, rng: np.random.RandomState, ratio: float) -> o3d.geometry.PointCloud:
    """在点云包围盒内均匀撒离群点。"""
    if ratio <= 0.0:
        return pcd
    pts = np.asarray(pcd.points)
    min_box = np.min(pts, axis=0) - 0.15
    max_box = np.max(pts, axis=0) + 0.15
    n_out = int(round(len(pts) * ratio))
    if n_out > 0:
        outliers = rng.uniform(min_box, max_box, size=(n_out, 3))
        pcd.points = o3d.utility.Vector3dVector(np.vstack([pts, outliers]))
        if pcd.has_colors:
            cols = np.asarray(pcd.colors)
            col_zero = np.zeros((n_out, 3), dtype=np.float64)
            pcd.colors = o3d.utility.Vector3dVector(np.vstack([cols, col_zero]))
    return pcd


def _crop_half_space(pcd: o3d.geometry.PointCloud, cfg: LevelConfig) -> o3d.geometry.PointCloud:
    """删除包围盒指定轴向侧比例，模拟部分重叠。"""
    if cfg.crop_ratio <= 0.0:
        return pcd
    pts = np.asarray(pcd.points)
    axis = int(1 if cfg.crop_axis == "x" else 2 if cfg.crop_axis == "y" else 0)
    span = np.ptp(pts[:, axis])
    if span <= 0.0:
        return pcd
    if cfg.crop_sign == "-":
        threshold = pts[:, axis].max() - span * cfg.crop_ratio
        keep = pts[:, axis] <= threshold
    else:
        threshold = pts[:, axis].min() + span * cfg.crop_ratio
        keep = pts[:, axis] >= threshold
    pcd.points = o3d.utility.Vector3dVector(pts[keep])
    if pcd.has_colors:
        pcd.colors = o3d.utility.Vector3dVector(np.asarray(pcd.colors)[keep])
    return pcd


def _add_noise(pcd: o3d.geometry.PointCloud, rng: np.random.RandomState, sigma: float) -> o3d.geometry.PointCloud:
    """添加高斯噪声。"""
    if sigma <= 0.0:
        return pcd
    pcd.points = o3d.utility.Vector3dVector(
        np.asarray(pcd.points) + rng.normal(0.0, sigma, size=np.asarray(pcd.points).shape)
    )
    return pcd


def _save_pointcloud(pcd: o3d.geometry.PointCloud, path: Path) -> None:
    """保存点云为 PLY，必要时补齐颜色。"""
    if not pcd.has_colors:
        pcd.colors = o3d.utility.Vector3dVector(np.zeros((len(pcd.points), 3)))
    pcd_path = path.with_suffix(".ply")
    pcd_path = path if str(path).endswith(".ply") else pcd_path
    o3d.io.write_point_cloud(str(pcd_path), pcd)


def _make_case_dir(out_dir: str, cfg: LevelConfig, seed: int) -> Path:
    case_dir = Path(out_dir) / cfg.level / f"seed_{seed:03d}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def generate_case(level_config: Dict[str, Any], seed: int, out_dir: str) -> Dict[str, Any]:
    """生成一组 source/target 合成点云、真值变换和 meta 元数据。

    Args:
        level_config: 难度参数 dict，字段同 LevelConfig。
        seed: 随机种子。
        out_dir: 输出根目录，默认项目 data。

    Returns:
        包含 case 路径、真值变换、点数和 meta 路径的 dict。
    """
    cfg = LevelConfig.from_dict(level_config)
    rng = _seeded_rng(seed)

    source = make_source_pointcloud(cfg, rng, seed)
    gt_T = pose_transform(cfg)
    target_points = np.asarray(source.points) @ gt_T[:3, :3].T + gt_T[:3, 3]
    target = o3d.geometry.PointCloud()
    target.points = o3d.utility.Vector3dVector(target_points)
    target.colors = source.colors

    target = _add_outliers(target, rng, cfg.outlier_ratio)
    target = _crop_half_space(target, cfg)
    target = _add_noise(target, rng, cfg.noise_sigma)

    case_dir = _make_case_dir(out_dir, cfg, seed)
    src_ply = case_dir / "source.ply"
    tgt_ply = case_dir / "target.ply"
    gt_npy = case_dir / "gt_transform.npy"
    meta_json = case_dir / "meta.json"
    _save_pointcloud(source, src_ply)
    _save_pointcloud(target, tgt_ply)
    np.save(gt_npy, gt_T)

    meta = {
        "case_type": "synthetic",
        "seed": int(seed),
        "config": {k: v for k, v in asdict(cfg).items() if v is not None},
        "extra_config": cfg.extra_fields(level_config),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_points": len(source.points),
        "target_points": len(target.points),
        "paths": {"source": str(src_ply), "target": str(tgt_ply), "gt_transform": str(gt_npy)},
    }
    meta_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    meta["meta_path"] = str(meta_json)
    meta["case_dir"] = str(case_dir)
    meta["gt_transform"] = gt_T
    return meta


def generate_real_case(dataset_name: str, level_config: Dict[str, Any], seed: int, out_dir: str) -> Optional[Dict[str, Any]]:
    """基于 Open3D 数据集生成真实点云用例；下载失败时返回 None。"""
    cfg = LevelConfig.from_dict(level_config)
    cfg.dataset = dataset_name
    rng = _seeded_rng(seed)
    source = _load_real_source(cfg, rng, seed)
    if source is None:
        return None

    gt_T = pose_transform(cfg)
    target_points = np.asarray(source.points) @ gt_T[:3, :3].T + gt_T[:3, 3]
    target = o3d.geometry.PointCloud()
    target.points = o3d.utility.Vector3dVector(target_points)
    target.colors = source.colors
    target = _add_outliers(target, rng, cfg.outlier_ratio)
    target = _crop_half_space(target, cfg)
    target = _add_noise(target, rng, cfg.noise_sigma)

    case_dir = _make_case_dir(out_dir, cfg, seed)
    src_ply = case_dir / "source.ply"
    tgt_ply = case_dir / "target.ply"
    gt_npy = case_dir / "gt_transform.npy"
    meta_json = case_dir / "meta.json"
    _save_pointcloud(source, src_ply)
    _save_pointcloud(target, tgt_ply)
    np.save(gt_npy, gt_T)
    meta = {
        "case_type": "real",
        "dataset": dataset_name,
        "seed": int(seed),
        "config": {k: v for k, v in asdict(cfg).items() if v is not None},
        "extra_config": cfg.extra_fields(level_config),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_points": len(source.points),
        "target_points": len(target.points),
        "paths": {"source": str(src_ply), "target": str(tgt_ply), "gt_transform": str(gt_npy)},
    }
    meta_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    meta["meta_path"] = str(meta_json)
    meta["case_dir"] = str(case_dir)
    meta["gt_transform"] = gt_T
    return meta


def _load_real_source(cfg: LevelConfig, rng: np.random.RandomState, seed: int) -> Optional[o3d.geometry.PointCloud]:
    """加载真实点云数据并采样到配置点数；失败时安全跳过。"""
    if not cfg.dataset:
        return None
    try:
        if cfg.dataset.lower() in {"bunny", "stanford_bunny", "stanford-bunny"}:
            bunny = o3d.data.BunnyMesh()
            mesh = o3d.io.read_triangle_mesh(bunny.path)
        elif cfg.dataset.lower() in {"ficus", "ficus_tree", "stanford_ficus"}:
            ficus = o3d.data.FicusMesh()
            mesh = o3d.io.read_triangle_mesh(ficus.path)
        else:
            raise ValueError(f"不支持的数据集：{cfg.dataset}，仅支持 bunny/ficus")
        pcd = mesh.sample_points_uniformly(number_of_points=max(int(cfg.n_points), 0))
        pcd.colors = o3d.utility.Vector3dVector(np.tile(np.array([0.5, 0.5, 0.5], dtype=np.float64), (len(pcd.points), 1)))
        return pcd
    except Exception:
        print(f"[warn] 数据集 {cfg.dataset} 加载失败，跳过真实点云用例。")
        return None


def visualize_pair(source_ply: str, target_ply: str, out_png: str, title: str = "before") -> str:
    """保存配准前后可视化对比图。"""
    src = o3d.io.read_point_cloud(source_ply)
    tgt = o3d.io.read_point_cloud(target_ply)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(10, 4.5))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    pts = np.asarray(src.points)
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=0.25, alpha=0.55, label="source")
    ax.set_title(f"{title}: source")
    ax.set_box_aspect((1, 1, 1))

    ax = fig.add_subplot(1, 2, 2, projection="3d")
    pts = np.asarray(tgt.points)
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=0.25, alpha=0.55, label="target")
    ax.set_title(f"{title}: target")
    ax.set_box_aspect((1, 1, 1))
    fig.tight_layout()
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=160)
    plt.close(fig)
    return str(out_png)


def default_l1_configs() -> Dict[str, Dict[str, Any]]:
    """默认 L1 演示配置：3 个 seed，包含旋转、平移、轻微噪声、离群点和裁剪。"""
    base: Dict[str, Any] = {
        "level": "L1",
        "n_points": 30000,
        "rot_x_deg": 5.0,
        "rot_y_deg": 15.0,
        "rot_z_deg": -5.0,
        "translation": [0.3, 0.1, 0.2],
        "noise_sigma": 0.003,
        "outlier_ratio": 0.01,
        "crop_ratio": 0.08,
        "crop_axis": "z",
        "crop_sign": "+",
    }
    return {
        "seed_001": base,
        "seed_002": {**base, "rot_y_deg": 22.0, "translation": [0.45, -0.1, 0.25], "outlier_ratio": 0.02},
        "seed_003": {**base, "rot_x_deg": -10.0, "rot_z_deg": 8.0, "translation": [0.2, 0.4, -0.15], "noise_sigma": 0.006, "crop_ratio": 0.12},
    }


def main() -> int:
    """入口：默认生成 L1 的三个合成 seed，并可视化 seed_001。"""
    root = Path(__file__).resolve().parents[1]
    out_dir = str(root / "data")
    cfgs = default_l1_configs()
    for name, cfg in cfgs.items():
        seed = int(name.split("_")[-1])
        result = generate_case(cfg, seed, out_dir)
        print(f"[ok] generated {result['case_dir']}: src={result['source_points']}, tgt={result['target_points']}")

    sample = generate_case(cfgs["seed_001"], 1, out_dir)
    png = visualize_pair(sample["paths"]["source"], sample["paths"]["target"], str(Path(out_dir) / "L1" / "seed_001" / "visualize_before.png"))
    print(f"[ok] visualization {png}")

    real_result = generate_real_case("bunny", {**cfgs["seed_001"], "dataset": "bunny"}, 101, out_dir)
    if real_result:
        print(f"[ok] generated real case {real_result['case_dir']}")
    else:
        print("[skip] real dataset unavailable; synthetic data remains valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
