# 01_AGNES_INTEGRATION — B2A 真实 Agnes 集成方案

**Phase B2A — Real Agnes Decision Integration**
**创建时间：2026-10-07**

---

## 1. 当前官方 AGH 如何真实调用 Agnes？

AGH（Agnes Harness）中 Agnes 模型的调用路径（`packages/ai` 的 AI provider 层 + `packages/sdk` 的 SDK 客户端）：

| 机制 | 说明 | 可用性 |
|---|---|---|
| AGH daemon 内部 agent loop | 当前会话本身通过 AGH daemon 运行，每次 prompt 都是真实 Agnes 调用 | ✅ 已验证 |
| SDK `Session.prompt()` | Node.js/TypeScript 程序化客户端，通过 JSON-RPC 连接 daemon | ✅ 可用 |
| `subagent_fork` | AGH 工具：在当前会话内同步派生子会话，子会话独立调用 Agnes 模型并返回最终文本 | ✅ 本会话可用 |
| `subagent_spawn` | AGH 工具：异步派生子会话，通过 `subagent_collect` 取回结果 | ✅ 本会话可用 |
| Python runtime（`packages/runtime-python`） | AGH 官方 Python 后端，**spike-gated，未实现**（`E_PRESET_UNSUPPORTED`） | ❌ 不可用 |

**关键结论：**
> 在当前 AGH 版本中，让 Agnes 读取结构化 observation 并返回结构化 decision 的
> 官方推荐方式是 **AGH 外层编排**：AGH 会话（或 `subagent_fork` 子会话）
> 本身即决策层；Python 代码通过 `shell` 工具被调用作为确定性执行层。

禁止"Python 脚本内部直接调用 Agnes"，因为：
- `packages/runtime-python` 未实现（spike-gated）
- 无官方 Python Agnes client
- 虚构 API 违反 B2A 规则

---

## 2. 采用哪种集成模式？

**AGH 外层编排模式（AGH orchestration）**

```
AGH 会话（本会话或 subagent_fork）
├─ 读取 diagnosis（来自 Python agent_diagnose）
├─ 构造 structured prompt（agnnes_agent.build_decision_prompt）
├─ 调用 Agnes 模型（subagent_fork / 直接 prompt）
├─ 获取 Agnes 原始文本响应
├─ agnnes_agent.parse_agnnes_decision（guardrail 检查）
├─ shell 工具调用 Python：run_local_icp / run_global_fpfh_ransac_icp
├─ 获取 observation
├─ 构造 assessment prompt（agnnes_agent.build_assessment_prompt）
├─ 再次调用 Agnes 模型
├─ agnnes_agent.parse_agnnes_assessment（guardrail 检查）
└─ 保存证据（outputs/development_tests/B2A_REAL_AGNES_SMOKE/）
```

Python 侧（`src/agnnes_agent.py`）：
- `build_decision_prompt()`：构造发给 Agnes 的 prompt
- `build_assessment_prompt()`：构造评估 prompt
- `parse_agnnes_decision()`：解析 + guardrail 验证
- `parse_agnnes_assessment()`：解析 + guardrail 验证
- `AgnesDecisionAdapter`：封装 AGH 会话的 Agnes 调用，供 runner 注入

---

## 3. 保留 / 废弃的代码

### 保留

| 代码 | 原因 |
|---|---|
| `agent_diagnose.diagnose()` | GT-free 数值诊断，正确 |
| `agent_tools.run_local_icp()` | 工具执行层，GT-free |
| `agent_tools.run_global_fpfh_ransac_icp()` | 工具执行层，GT-free |
| `agent_evaluator.evaluate_agent_result()` | GT 隔离，只读 GT |
| `agent_runner.heuristic_decide()` | B2A 之后重命名，保留为 baseline 对照 |
| `agent_runner.heuristic_assess()` | B2A 之后重命名，保留为 baseline 对照 |

### 废弃（不再用于 Agnes 证明路径）

| 代码 | 原因 |
|---|---|
| `agnnes_decide()`（旧名） | B1 审计确认无 LLM 调用，重命名为 `heuristic_decide()` |
| `agnnes_assess()`（旧名） | B1 审计确认无 LLM 调用，重命名为 `heuristic_assess()` |
| `fitness >= 0.8 → ACCEPT` 直接映射 | 仅保留在 heuristic baseline；Agnes 路径由 LLM 判断 |

---

## 4. 如何保证 decision 真的是 Agnes 输出？

1. 每个 decision/assessment JSON 里包含 `_agnnes_model` 和 `_agnnes_timestamp` 字段
2. `agnnes_raw_response_*.json` 保存 Agnes 的原始文本输出（未解析前的字符串）
3. `subagent_fork` 返回的文本是真实 Agnes 模型生成
4. **防伪验证**：关闭 Agnes 调用（传 `use_agnnes=False`）后，系统仍能用 heuristic 路径产生结果 → 若两路径结果不同，证明 Agnes 路径是独立决策

---

## 5. GT 隔离承诺

- `agnnes_agent.build_decision_prompt()` 不含 `gt_transform` / `rotation_error` / `translation_error` / 场景标签
- Agnes 输入只有：`diagnosis` + `TOOL_REGISTRY` + `PARAMETER_RANGE`
- Evaluator 调用时序不变：Agnes 停止（ACCEPT/ABORT）后才读 GT
