# HEURISTIC_BASELINE_CORRECTION — Phase A / B0 决策归属修正声明

**创建时间：2026-10-07**
**状态：FINAL CORRECTION DECLARATION（不修改任何 Frozen 证据，仅新增声明）**

---

## 修正背景

Phase A 和 Phase B0 中，以下文件曾使用"Agnes Decision / Agnes Assessment"命名：

- `outputs/submission_evidence/L1/*/02_AGENT/agent_decision_01.json`
- `outputs/submission_evidence/L1/*/02_AGENT/agent_assessment_01.json`
- `outputs/submission_evidence/L2/*/02_AGENT/agent_decision_01.json`
- `outputs/submission_evidence/L2/*/02_AGENT/agent_assessment_01.json`
- `src/agent_runner.py` 中的 `agnnes_decide()` / `agnnes_assess()` 函数

B1 审计（`docs/agent_loop_2026-10-07/B1/01_DECISION_AUDIT.md`、
`05_ACCEPT_RETRY_AUDIT.md`、`B1_STATE.json`）确认：

> **上述"Agnes 决策"实际由确定性 Python `if/elif/else` heuristic 执行，
> 未发生任何真实 Agnes LLM 专业决策调用。**

具体事实：
1. `agnnes_decide`：easy/hard branch 由 `offset_proxy < 3.0` 判定，算法/参数均为写死字面量，无 LLM 调用
2. `agnnes_assess`：ACCEPT/RETRY 由 `fitness >= 0.8` 阈值判定，无 LLM 调用，ABORT 路径未实现
3. 参数 `global_corr_scale=5.0`、`icp_max_corr_scale=2.0` 来自 Python 字面量，非模型选择

---

## 修正定义

Phase A / B0 的以下 Run 重新定义为：

```
Heuristic Baseline + Pipeline Prototype
```

**不再定义为**："Agnes 模型自主参与核心决策"的最终证据。

修正理由：B1 审计确认 LLM 决策调用不存在，"Agnes" 在历史证据中
仅为函数名和 JSON 字段标签，不代表模型实际参与。

---

## 仍然有效的用途

这些历史 Run **保留，不删除、不篡改、不覆盖**，仍然可用于：

| 用途 | 说明 |
|---|---|
| 工具链验证 | LOCAL_ICP / GLOBAL_FPFH_RANSAC_ICP 工具执行正确性 |
| GT 隔离验证 | `gt_read: false` 记录，evaluator 时序正确 |
| 算法结果参考 | fitness / rmse / transform 数值（确定性工具输出） |
| Pipeline 回归 | runner 循环结构、证据落盘格式 |
| 消融基线 | B2 真实 Agnes 路径 vs heuristic baseline 的对比参照 |

**不可用于：**

- "Agnes 模型参与核心决策"的最终证明
- 算法选择归因（算法由 Python 决定，非 LLM）
- 参数自适应证明（参数为 Python 字面量，非 LLM 选择）
- ACCEPT/RETRY 决策归因（决策由 Python 阈值，非 LLM）

---

## 代码层修正

| 原函数名 | 修正后名 | 文件 |
|---|---|---|
| `agnnes_decide()` | `heuristic_decide()` | `src/agent_runner.py` |
| `agnnes_assess()` | `heuristic_assess()` | `src/agent_runner.py` |

历史 Frozen 证据包（`outputs/submission_evidence/`）**保持原文件名，不改名**，
仅通过本声明修正其语义归属。

---

## B2A 真实 Agnes 路径

Phase B2A 新增：
- `src/agnnes_agent.py`：Agnes 决策/评估 schema + guardrail 验证
- AGH 外层编排模式：Agnes 通过 AGH 会话（`subagent_fork` 或等价机制）
  读取结构化 diagnosis，输出结构化 JSON decision/assessment
- Python 不再替代 Agent 决定算法/参数/ACCEPT-RETRY

历史 `heuristic_decide()` / `heuristic_assess()` 保留为 baseline 对照路径。

---

**本声明仅新增，不修改任何历史 Frozen 文件。**
