# HEURISTIC_BASELINE_CORRECTION_LINK — B2A 引用链接

**Phase B2A 文档，指向 `docs/evidence_log/HEURISTIC_BASELINE_CORRECTION.md`。**

---

## 链接

`docs/evidence_log/HEURISTIC_BASELINE_CORRECTION.md`

---

## 为什么 B2A 需要这个链接

B2A 引入真实 Agnes 决策路径，同时保留 heuristic baseline。
本文件提供修正声明，确保阅读历史证据包的人知道：

- **Phase A / B0 的"Agnes Decision"文件**：实际由确定性 Python heuristic 生成，
  未发生真实 Agnes LLM 调用（B1 审计确认）
- **重新定义**：Heuristic Baseline + Pipeline Prototype
- **仍有效用途**：工具链验证、GT 隔离验证、pipeline 回归、消融基线
- **无效用途**："Agnes 模型参与核心决策"的最终证明

---

## 代码层修正记录

| 原函数名 | B2A 修正后名 | 文件 | 状态 |
|---|---|---|---|
| `agnnes_decide()` | `heuristic_decide()` | `src/agent_runner.py` | @deprecated |
| `agnnes_assess()` | `heuristic_assess()` | `src/agent_runner.py` | @deprecated |

历史 Frozen 证据包（`outputs/submission_evidence/`）保持原文件名，
通过上述修正声明修正语义归属，**不改名、不删除、不覆盖**。

---

## 真实 Agnes 路径入口

- `src/agnnes_agent.py` — schema + guardrail + prompt 构造
- `run_agent_case(..., agnes_decide_fn=..., agnes_assess_fn=...)` — 注入接口
- 真实 Agnes 调用：AGH 会话（subagent_fork 或等价机制）

详见：`docs/agent_loop_2026-10-07/B2A/01_AGNES_INTEGRATION.md`
