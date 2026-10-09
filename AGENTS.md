# AGENTS.md

## 项目

- 名称：**AGH驱动的点云自动配准智能体**。
- 项目路径：`D:\STUDY\darker\agent-pointcloud-registration`
- AGH 路径：`D:\STUDY\darker\agnes-harness`
- Python：`D:\APP\Anaconda\envs\pointcloud_agh\python.exe`

## 职责边界

- Codex 仅作为开发、维护、分析、统计和自动化工具。
- 正式比赛 Agent Run 必须由 Agnes Harness（AGH）组织、执行并调用工具。
- 正式 Run 中，Codex 不得替代模型决定 registration method、Probe、parameter policy 或 `ACCEPT` / `RETRY` / `ABORT`。

## Frozen Evidence 与 Ground Truth

- `outputs/submission_evidence/B3/` 下的 B3A/B3B 正式 Frozen Run 默认只读；不得修改、移动、覆盖或删除。
- 特别保护：`b3_l1_20261007_seed101_blind02`、`b3_l2_20261007_seed202_blind01`。
- 正式 Agent 决策阶段禁止读取 Ground Truth（GT）；只有 Agent 停止后，Independent Evaluator 才可读取 GT。

## Evidence 结构

- 正式层级固定为 **Level → Run → Attempt**，正式输出统一写入 `outputs/submission_evidence/`。
- 禁止在 repository root 创建 `00_INDEX`、`01_AGH`、`02_AGENT`、`03_TOOL_CHAIN`、`04_CONFIG`、`05_VALIDATION`、`06_VISUALS`、`attempts` 等 Run 骨架目录。

## 科研真实性

- 缺失字段写 `UNKNOWN` / `MISSING`，不得猜测或补造。
- 失败 Attempt 必须保留，不得删除。
- 不得因看到 GT 后重新调参并覆盖原正式 Run。
- historical heuristic 与 Real Agnes 证据必须明确区分，不得混称。

## Git 与工作方式

- 未经用户明确要求，不执行 `commit`、`push`、`reset`、`checkout` 或 `rebase`。
- 修改前后检查 `git status` 和 `git diff`，保留并避开用户已有改动。
- 能从仓库自行查明的内容，不要求用户重新粘贴；优先搜索文件、读取 JSON/MD/CSV，并运行必要的只读分析。
- 复杂任务持续执行到验收条件完成或遇到真实 blocker，不逐步停下等待确认。
