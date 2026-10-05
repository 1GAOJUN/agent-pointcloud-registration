"""L2 单场景智能闭环调度器 · 验证脚本。

直接读取 outputs/ICP/L2 下已有的 source.ply / target.ply / gt_transform.npy，
不重新生成数据；一键运行完整闭环，打印结构化过程报告。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\test_closed_loop_l2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 复用现有模块（不修改）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from pipelines.closed_loop_l2 import run_closed_loop, ClosedLoopReport  # noqa: E402


def _bar(passed: bool, width: int = 20) -> str:
    """简单进度条，用于报告美观。"""
    filled = width if passed else 0
    return "█" * filled + "·" * (width - filled)


def render_report(rep: ClosedLoopReport) -> str:
    """把结构化报告渲染成可读终端文本。"""
    lines: list[str] = []
    sep = "=" * 78
    lines.append(sep)
    lines.append("L2 单场景智能闭环调度 · 过程报告")
    lines.append(f"数据目录：{_PROJECT_ROOT / 'outputs' / 'ICP' / 'L2'}")
    lines.append(
        f"达标标准：旋转误差<{rep.thresholds['rot_max_deg']}° 且 "
        f"fitness>{rep.thresholds['fitness_min']}"
    )
    lines.append(sep)

    lines.append("")
    lines.append("[第 1 轮 · 基线测试] 朴素 ICP（单位阵初值）")
    lines.append(_bar(rep.steps[0].passed))
    s1 = rep.steps[0]
    lines.append(f"  旋转误差 = {s1.rot_err_deg:.4f}°")
    lines.append(f"  平移误差 = {s1.trans_err:.4f}")
    lines.append(f"  fitness  = {s1.fitness:.4f}")
    lines.append(f"  耗时     = {s1.elapsed_sec:.2f}s")
    lines.append(f"  是否达标 = {'达标' if s1.passed else '未达标'}")

    if rep.switch_strategy:
        lines.append("")
        lines.append("[失败诊断 + 策略切换]")
        lines.append(f"  诊断：{rep.diagnosis}")
        lines.append("  动作：切换 → FPFH+RANSAC 全局粗配准 + ICP 精化")

        lines.append("")
        lines.append("[第 2 轮 · 全局粗配准 + ICP 精化]")
        s2 = rep.steps[1]
        lines.append(_bar(s2.passed))
        lines.append(f"  旋转误差 = {s2.rot_err_deg:.4f}°")
        lines.append(f"  平移误差 = {s2.trans_err:.4f}")
        lines.append(f"  fitness  = {s2.fitness:.4f}")
        lines.append(f"  RANSAC fitness = {s2.detail.split('ransac_fitness=')[1].strip()}")
        lines.append(f"  耗时     = {s2.elapsed_sec:.2f}s")
        lines.append(f"  是否达标 = {'达标' if s2.passed else '未达标'}")
    else:
        lines.append("")
        lines.append("[复验] 基线已达标，无需切换策略")

    lines.append("")
    lines.append("[最终结论]")
    verdict = "PASS" if rep.final_passed else "FAIL"
    lines.append(f"  [{verdict}] 闭环最终达标：{'是' if rep.final_passed else '否'}")
    lines.append(f"  总耗时 = {rep.total_elapsed_sec:.2f}s")
    lines.append(sep)

    # 摘要行
    if rep.switch_strategy:
        s1, s2 = rep.steps[0], rep.steps[1]
        lines.append(
            f"闭环摘要：朴素ICP未达标(rot={s1.rot_err_deg:.1f}°/fit={s1.fitness:.2f}) "
            f"→ 切换全局 → 达标(rot={s2.rot_err_deg:.4f}°/fit={s2.fitness:.2f})"
        )
    else:
        lines.append("闭环摘要：朴素ICP直接达标，未触发策略切换")
    lines.append(sep)
    return "\n".join(lines)


def main() -> int:
    l2_dir = _PROJECT_ROOT / "outputs" / "ICP" / "L2"
    source_ply = str(l2_dir / "source.ply")
    target_ply = str(l2_dir / "target.ply")
    gt_npy = str(l2_dir / "gt_transform.npy")

    for p in (source_ply, target_ply, gt_npy):
        if not Path(p).exists():
            print(f"[FAIL] 缺少 {p}")
            print("      请先运行 src/run_benchmark.py 生成 outputs/ICP/L2。")
            return 1

    rep = run_closed_loop(source_ply, target_ply, gt_npy)
    print(render_report(rep))

    # 留证：写 JSON（新增文件，不碰已有）
    out_json = l2_dir / "l2_closed_loop_result.json"
    out_json.write_text(
        json.dumps(rep.to_dict(), indent=2, ensure_ascii=False, default=float),
        encoding="utf-8",
    )
    print(f"[saved] {out_json}")
    return 0 if rep.final_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
