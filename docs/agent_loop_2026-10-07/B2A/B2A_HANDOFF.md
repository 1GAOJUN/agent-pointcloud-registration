# B2A_HANDOFF — Real Agnes Decision Integration（一页）

**Phase B2A 完成时间：2026-10-07**
**审计范围**：`src/agent_runner.py`（重命名）、`src/agnnes_agent.py`（新增）、
`outputs/development_tests/B2A_REAL_AGNES_SMOKE/`

---

## B2A 结论

**Phase B2A 完成（COMPLETE），未阻塞。**

核心成果：**真实 Agnes LLM 决策路径已接入，与 heuristic baseline 明确分离。**

- `agnnes_decide` → `heuristic_decide`（`@deprecated`，保留 baseline）
- `agnnes_assess` → `heuristic_assess`（`@deprecated`，保留 baseline）
- 新增 `src/agnnes_agent.py`：Agnes 决策/评估 schema + guardrail 验证 + prompt 构造
- 新增 `run_agent_case(..., agnes_decide_fn=..., agnes_assess_fn=...)` 注入接口
- 冒烟测试通过（`outputs/development_tests/B2A_REAL_AGNES_SMOKE/`）

---

## B2A 真正由 Agnes（LLM）控制什么

| 决策点 | 执行位置 | 说明 |
|---|---|---|
| 算法选择 | `subagent_fork` → Agnes LLM | Agnes 读 diagnosis + tools + param_ranges，输出 `selected_method` |
| 参数倍率 | `subagent_fork` → Agnes LLM | Agnes 在 guardrail 范围内自由选择（非固定 5.0/2.0） |
| ACCEPT/RETRY/ABORT | `subagent_fork` → Agnes LLM | Agnes 读 observation（fitness/rmse），专业判断结果质量 |

---

## B2A 真正由 Python 控制什么

| 决策点 | 执行位置 | 说明 |
|---|---|---|
| Diagnosis 数值计算 | `agent_diagnose.diagnose()` | GT-free，确定性测量 |
| 工具执行（ICP/FPFH） | `agent_tools.run_*()` | 按 Agnes 选择参数执行，不做决策 |
| Guardrail 验证 | `agnnes_agent.validate_*()` | 参数范围、schema 校验，越界返回 error 给 Agnes 重选 |
| 参数下限保护 | `agent_tools.py` `max(1e-4,...)` | 双保险 |
| Retry 次数上限 | `run_agent_case(max_retry=2)` | 防止无限循环 |
| GT 读取 | `agent_evaluator.evaluate_agent_result()` | 只在 Agent 停止后 |

---

## 集成模式

**AGH 外层编排**：
- Python（shell 工具）执行 diagnosis + 工具调用
- AGH 会话（subagent_fork）调用 Agnes 模型做决策/评估
- 两次 LLM 调用的原始输出落盘 `agnnes_raw_decision.json` / `agnnes_raw_assessment.json`

**理由**：AGH Python runtime（`packages/runtime-python`）未实现（spike-gated），
无官方 Python Agnes client，只有 AGH 会话层可访问真实 Agnes 模型。

---

## Heuristic Baseline 保留说明

`heuristic_decide()` / `heuristic_assess()` 保留在 `src/agent_runner.py` 中，
标注 `@deprecated`，仅用于：
- 消融对照实验（B2B 之后）
- 工具链回归测试
- 与真实 Agnes 路径的 A/B 对比

**不得作为"Agnes 参与核心决策"的证据。**

---

## 下一步（B2B 入口）

B2B 进入 Probe 实现阶段：
1. 实现 Probe A（PCA Orientation）和 Probe B（Cheap ICP Probe）
2. 注册为 Agnes 可调用的工具
3. 更新 runner 支持 Agnes 调用 Probe 的循环
4. 在 L2/L3/L4 场景跑正式盲测，验证 Agnes 专业判断的场景适应性

**B2A 到真实 Agnes 决策接通为止，Probe 属 B2B。**

---

## B2A 禁止事项

- 不得修改 L1/L2 Frozen 证据包
- 不得将 heuristic baseline 结果用于"Agnes 参与"证明
- 不得跳过 guardrail 验证直接执行 Agnes 参数
- 不得在 Agnes prompt 中传入 GT / 场景标签 / 磁盘路径

---

## 必须读取的文件（B2B 入口）

1. `docs/agent_loop_2026-10-07/B2A/B2A_HANDOFF.md`（本文件）
2. `docs/agent_loop_2026-10-07/B2A/03_AGENT_GUARDRAILS.md`（guardrail 常量与规则）
3. `src/agnnes_agent.py`（新增 Agnes 决策模块）
4. `src/agent_runner.py`（runner 注入接口，注意 `heuristic_decide` 已 `@deprecated`）
5. `outputs/development_tests/B2A_REAL_AGNES_SMOKE/`（冒烟测试证据）
