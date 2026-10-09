"""B3B visuals: before.png / after.png / compare.png / metrics_panel.png.

- Same camera (elev/azim) and same coord range for before/after (no exaggeration).
- source = blue, target = red (consistent across all three geometry plots).
- metrics_panel.png uses matplotlib Agg; if that fails, falls back to PIL.
- GT values shown ONLY in metrics_panel (labeled as Independent GT Evaluation),
  NOT in before/after/compare geometry plots.
"""
import json, sys
from pathlib import Path
import numpy as np
import open3d as o3d

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
case = ROOT / "outputs" / "ICP" / "L2" / "L2" / "seed_202"
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
vis_dir = run_dir / "06_VISUALS"
vis_dir.mkdir(parents=True, exist_ok=True)

obs = json.loads((run_dir / "02_AGENT" / "observation_01.json").read_text(encoding="utf-8-sig"))
evalr = json.loads((run_dir / "05_VALIDATION" / "evaluator_result.json").read_text(encoding="utf-8-sig"))
T_est = np.asarray(obs["transform"], dtype=np.float64)

src = o3d.io.read_point_cloud(str(case / "source.ply"))
tgt = o3d.io.read_point_cloud(str(case / "target.ply"))
src_pts = np.asarray(src.points, dtype=np.float64)
tgt_pts = np.asarray(tgt.points, dtype=np.float64)
src_aligned = src_pts @ T_est[:3, :3].T + T_est[:3, 3]

SOURCE_COLOR = [0.2, 0.5, 0.95]
TARGET_COLOR = [0.9, 0.15, 0.15]

# Unified coord range from combined bounds of all three clouds (before, after, target)
all_pts = np.vstack([src_pts, src_aligned, tgt_pts])
center = (all_pts.min(axis=0) + all_pts.max(axis=0)) / 2.0
half = float(np.max(all_pts.max(axis=0) - all_pts.min(axis=0))) * 0.55

ELEV, AZIM = 25, -60


def _sub(ax, pts_a, color_a, label_a, pts_b, color_b, label_b, title):
    ax.scatter(pts_b[:, 0], pts_b[:, 1], pts_b[:, 2], s=1.2, c=[TARGET_COLOR], alpha=0.55, label=label_b)
    ax.scatter(pts_a[:, 0], pts_a[:, 1], pts_a[:, 2], s=1.2, c=[SOURCE_COLOR], alpha=0.55, label=label_a)
    ax.view_init(elev=ELEV, azim=AZIM)
    ax.set_xlim(*[center[0] - half, center[0] + half])
    ax.set_ylim(*[center[1] - half, center[1] + half])
    ax.set_zlim(*[center[2] - half, center[2] + half])
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=8)


def _save_geom(ax_single, out_png, label):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(7, 6), dpi=140)
    fig.clear()
    ax = fig.add_subplot(111, projection="3d")
    _sub(ax, src_pts if label == "before" else src_aligned, SOURCE_COLOR,
         "source" + ("" if label == "before" else " (after registration)"),
         tgt_pts, TARGET_COLOR, "target",
         f"{label.upper()}: source vs target (case_unknown_B)")
    fig.tight_layout()
    fig.savefig(str(out_png), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] {out_png.name}")


for label in ("before", "after"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(7, 6), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    src_show = src_pts if label == "before" else src_aligned
    _sub(ax, src_show, SOURCE_COLOR,
         "source" if label == "before" else "source (after registration)",
         tgt_pts, TARGET_COLOR, "target",
         f"{label.upper()}: source vs target — case_unknown_B")
    fig.tight_layout()
    fig.savefig(str(vis_dir / f"{label}.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] {label}.png")

# compare.png — side by side, same camera + coord range (identical limits both axes)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig = plt.figure(figsize=(14, 6), dpi=140)
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
_sub(ax1, src_pts, SOURCE_COLOR, "source (raw)", tgt_pts, TARGET_COLOR, "target", "BEFORE registration")
_sub(ax2, src_aligned, SOURCE_COLOR, "source (registered)", tgt_pts, TARGET_COLOR, "target", "AFTER registration")
fig.suptitle("B3B case_unknown_B — before / after (GLOBAL_FPFH_RANSAC_ICP)", fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(str(vis_dir / "compare.png"), dpi=140, bbox_inches="tight")
plt.close(fig)
print(f"[ok] compare.png")

# ---------------------------------------------------------------------------
# metrics_panel.png — matplotlib first; PIL fallback if any error
# ---------------------------------------------------------------------------
def _draw_metrics_panel(matplotlib_ok: bool):
    agent_obs = obs
    panel_lines_agent = [
        "AGENT OBSERVABLE METRICS (no GT)",
        f"method: {agent_obs.get('tool_name')}",
        f"fitness: {agent_obs.get('fitness')}",
        f"rmse: {agent_obs.get('rmse')}",
        f"ransac_fitness: {agent_obs.get('ransac_fitness')}",
        f"runtime_s: {agent_obs.get('elapsed_s')}",
        "",
        "INDEPENDENT GT EVALUATION (post-Agent-stop only)",
        f"rotation_error_deg: {evalr.get('rot_err_deg')}",
        f"translation_error: {evalr.get('trans_err')}",
        f"success: {evalr.get('success')}",
        f"rot_thr_deg: {evalr.get('rot_thr_deg')}",
        f"trans_thr: {evalr.get('trans_thr')}",
    ]
    out_png = vis_dir / "metrics_panel.png"

    if matplotlib_ok:
        fig, ax = plt.subplots(figsize=(9, 5), dpi=140)
        ax.axis("off")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        y = 0.97
        for i, line in enumerate(panel_lines_agent):
            color = "navy" if line.startswith("AGENT") else ("darkred" if line.startswith("INDEPENDENT") else "black")
            weight = "bold" if (line.startswith("AGENT") or line.startswith("INDEPENDENT")) else "normal"
            ax.text(0.02, y, line, fontsize=13, color=color, weight=weight, family="monospace",
                    transform=ax.transAxes)
            y -= 0.07
        fig.suptitle("B3B — b3_l2_20261007_seed202_blind01", fontsize=13)
        fig.tight_layout()
        fig.savefig(str(out_png), dpi=140, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"[ok] metrics_panel.png (matplotlib)")
    else:
        from PIL import Image, ImageDraw
        W, H = 720, 400
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        y = 20
        for line in panel_lines_agent:
            color = (0, 0, 128) if line.startswith("AGENT") else ((128, 0, 0) if line.startswith("INDEPENDENT") else (0, 0, 0))
            d.text((10, y), line, fill=color)
            y += 26
        d.text((10, 10), "B3B — b3_l2_20261007_seed202_blind01", fill="black")
        img.save(str(out_png), format="PNG")
        print(f"[ok] metrics_panel.png (PIL fallback)")


try:
    _draw_metrics_panel(matplotlib_ok=True)
except Exception as e:
    print(f"[warn] matplotlib failed ({e}); falling back to PIL")
    _draw_metrics_panel(matplotlib_ok=False)
