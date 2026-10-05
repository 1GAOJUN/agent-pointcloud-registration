"""剧情自验：验证 L1 达标、L2 失败（fitness 明显低）。

不修改任何已有逻辑，仅读取 run_benchmark 生成的 CSV 做判定。
若 L2 意外通过，如实报告而不调参。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\verify_story.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    csv_path = _PROJECT_ROOT / "outputs" / "reports" / "baseline_results.csv"
    if not csv_path.exists():
        print("[FAIL] 未找到 outputs/baseline_results.csv，请先运行 src/run_benchmark.py")
        return 1

    rows = {}
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["level"]] = r

    l1 = rows.get("L1")
    l2 = rows.get("L2")
    ok = True

    # L1 必须达标
    if l1 is None:
        print("[FAIL] 缺少 L1 记录")
        ok = False
    else:
        l1_passed = l1["passed"].strip().lower() == "true"
        if l1_passed:
            print(f"[PASS] L1 达标：rot={l1['rot_err_deg']}° fitness={l1['fitness']}")
        else:
            print(f"[FAIL] L1 未达标：rot={l1['rot_err_deg']}° fitness={l1['fitness']}")
            ok = False

    # L2 必须失败（fitness 明显低，< 0.8）
    if l2 is None:
        print("[FAIL] 缺少 L2 记录")
        ok = False
    else:
        l2_fitness = float(l2["fitness"])
        l2_failed = l2["passed"].lower() == "false"
        if l2_failed and l2_fitness < 0.8:
            print(f"[PASS] L2 如预期失败：rot={l2['rot_err_deg']}° fitness={l2_fitness}（大角度朴素 ICP 发散）")
        elif l2_failed:
            print(f"[WARN] L2 失败但 fitness={l2_fitness} 并非明显低，请人工复核")
        else:
            print(f"[WARN] L2 意外通过！rot={l2['rot_err_deg']}° fitness={l2_fitness}，不符合剧情预期，如实上报不调参")
            ok = False

    print("\n=== 剧情自验结论 ===")
    if ok:
        print("PASS：L1 达标且 L2 按预期失败，剧情自洽。")
        return 0
    else:
        print("FAIL：剧情自验未通过，详见上方 [FAIL]/[WARN]。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
