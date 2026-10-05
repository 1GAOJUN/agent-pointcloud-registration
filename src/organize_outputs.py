"""整理 outputs/ 目录：按功能归类散落产物。

register_minimal.py（红线，不能改）会把 before.png / after.png 写到 outputs/ 根；
evaluate.py（红线，不能改）会把 evaluate_test.txt 写到 outputs/ 根。
本脚本把这些散落文件收进对应的功能目录：

    outputs/demo_auto_registration/   自动配准 demo 的两张图
    outputs/reports/                  证据文件（csv + txt）

已有功能目录（ICP/、reports/、demo_auto_registration/）会被保留，只移动散落文件，
不删除、不覆盖同名文件（遇到同名会重命名为 xxx_1.png 等）。

运行：
    D:\APP\Anaconda\envs\pointcloud_agh\python.exe src\organize_outputs.py
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

_OUT = Path(__file__).resolve().parents[1] / "outputs"

# 散落文件 -> 目标功能目录
MOVES: Dict[str, str] = {
    "before.png": "demo_auto_registration",
    "after.png": "demo_auto_registration",
    "evaluate_test.txt": "reports",
}


def _unique(dest: Path) -> Path:
    """同名文件不覆盖，自动加序号。"""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    i = 1
    while True:
        cand = dest.with_name(f"{stem}_{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1


def main() -> int:
    moved: List[str] = []
    for fname, subdir in MOVES.items():
        src = _OUT / fname
        if not src.exists():
            continue
        dest_dir = _OUT / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = _unique(dest_dir / fname)
        shutil.move(str(src), str(dest))
        moved.append(f"{fname} -> {subdir}/{dest.name}")

    if not moved:
        print("[organize] 没有需要整理的散落文件（outputs/ 根已干净）。")
    else:
        print("[organize] 已整理：")
        for m in moved:
            print(f"  {m}")

    # 打印整理后的 outputs/ 结构
    print("\n=== outputs/ 当前结构 ===")
    for p in sorted(_OUT.rglob("*")):
        if p.is_dir():
            continue
        print(" ", p.relative_to(_OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
