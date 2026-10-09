# 05_ACCEPT_RETRY_AUDIT — ACCEPT/RETRY 决策归因审计

**Phase B1 — 只读审计。**

---

## F1. 0.8 阈值在哪里定义

**位置**：`src/agent_runner.py`，`agnnes_assess` 函数签名，第 94 行：

```python
def agnes_assess(observation: Dict[str, Any],
                 pass_fittess: float = 0.8) -> Dict[str, Any]:
```

- 默认参数 `pass_fittess = 0.8`（拼写错误：`fittess`，非 `fitness`，是 Python 参数名，非拼写错误问题）
- 在 `agnnes_assess` 被调用时（`run_agent_case` 第 212 行：`assessment = agnes_assess(obs)`），
  没有传第二个参数，因此始终使用默认值 `0.8`。

**0.8 是写死在函数签名默认参数里的字面量，无配置项，无注释说明来源。**

---

## F2. 是 Python 直接决定 ACCEPT 吗

**是，完全是 Python 阈值判断。**

`agnnes_assess` 逻辑（第 99-113 行）：

```python
fitness = float(observation.get("fitness", 0.0))
if fitness >= pass_fittess:      # fitness >= 0.8
    decision = "ACCEPT"
    reason = f"...fitness={fitness:.4f} 已达阈值 {pass_fittess}..."
else:
    decision = "RETRY"
    reason = f"...fitness={fitness:.4f} 低于阈值 {pass_fittess}，需换工具或参数重跑。"
    nxt = {"reselect_tool": True}
```

**没有调用 Agnes 模型，没有 LLM 判断，是纯 Python `if fitness >= 0.8`。**

注意：当前代码里**没有 ABORT 分支**——只有 ACCEPT 和 RETRY。
若 RETRY 后仍失败，循环跑满 `max_retry=2` 次后自动结束（`run_agent_case` 第 168 行 `for i in range(max_retry + 1)`），
最终判断是最后一次 `agnnes_assess` 的 RETRY，而非 ABORT。

---

## F3. 还是 Agnes 看到 fitness 后决定

**Agnes（LLM）没有参与。**

`agnnes_assess` 是纯 Python 函数，
其输出 `agent_assessment_01.json` 里的 `decision`/`reason` 字符串
是 Python 代码里写死的模板字符串（第 103、107 行），
不是 LLM 生成的自然语言。

L2 证据包里 `agent_assessment_01.json` 的内容：
```json
{
  "result_assessment": "可观测 fitness=1.0000 已达阈值 0.8，判定配准质量可接受。",
  "decision": "ACCEPT",
  "reason": "可观测 fitness=1.0000 已达阈值 0.8，判定配准质量可接受。",
  "next_action": {}
}
```
这条 reason 字符串与 `agnnes_assess` 第 103 行的 f-string 完全一致，
确认是 Python 模板而非 LLM 输出。

---

## F4. 如果 fitness < 0.8，当前系统会发生什么

1. `agnnes_assess` 返回 `decision = "RETRY"`, `next_action = {"reselect_tool": True}`
2. `run_agent_case` 循环继续（`if assessment["decision"] == "ACCEPT": break` 不触发）
3. 下一次迭代进入 RETRY branch（`agnnes_decide` 第 66-75 行）：
   - 切换至另一工具
   - 参数收紧：`icp_max_corr_scale = 1.5`（若选 LOCAL）或 `global_corr_scale = 4.0, icp_max_corr_scale = 1.5`（若选 GLOBAL）
4. 最多再跑 2 次（`max_retry = 2`），共最多 3 次尝试
5. 3 次后循环自动结束，**没有 ABORT 判断**，
   最终 `agent_final_assessment` 是最后一次 `agnnes_assess` 的输出

**风险**：若 3 次都 fitness < 0.8，系统不会输出 ABORT，
而是以最后一次 RETRY 的 assessment 作为"最终判断"，
这与 `EVIDENCE_STRUCTURE.md` 里定义的 ABORT 状态（`ABORT_AGENT`）不符——
当前代码里**没有实现 ABORT 路径**。

---

## F5. Agnes 是否拥有 RETRY / ABORT 真实自由度

**否。**

- RETRY：由 Python `agnnes_assess` 的 `fitness < 0.8` 判断直接触发，Agnes 无决策权
- ABORT：**当前代码未实现 ABORT 路径**，只有 ACCEPT 和 RETRY 两个状态
- 重试次数上限 `max_retry = 2` 是 `run_agent_case` 的函数参数，写死

若未来 Agnes 是真实 LLM，理论上它可以被赋予"判断是否值得 ABORT"的专业决策权，
但当前架构里这个决策是 Python 循环次数耗尽后自然结束，不是 Agnes 判断。

---

## F6. 当前闭环属于哪种类型

**Python 阈值判断 + Python 结构化输出（假装是 Agnes 解释）**

具体来说：

| 决策点 | 真正执行者 | 是否有 LLM 参与 |
|---|---|---|
| 场景难度判断（easy/hard） | Python `agnnes_decide` 第 52 行 | 否 |
| 算法选择 | Python `agnnes_decide` 第 54-64 行 | 否 |
| 参数倍率 | Python `agnnes_decide` 第 56、62、72 行 | 否 |
| ACCEPT/RETRY | Python `agnnes_assess` 第 101-108 行 | 否 |
| ABORT | **未实现** | 否 |
| 最终 transform 质量判断（GT） | Python `evaluate_agent_result` | 否（独立 Evaluator，设计正确） |

**结论：当前闭环是"Python 确定性状态机 + 模仿 Agent 输出结构"，不是真正的 Agent 决策闭环。**

---

## 证据路径

| 项目 | 位置 | 行号 |
|---|---|---|
| 0.8 阈值定义 | `src/agent_runner.py` | 94（函数签名默认参数） |
| ACCEPT 判断 | `src/agent_runner.py` | 101-104 |
| RETRY 判断 | `src/agent_runner.py` | 105-108 |
| ABORT 缺失 | `src/agent_runner.py` | `agnnes_assess` 里没有 ABORT 分支 |
| max_retry 定义 | `src/agent_runner.py` | 138（`run_agent_case` 参数） |
| L2 assessment 实际值 | `outputs/submission_evidence/L2/.../02_AGENT/agent_assessment_01.json` | — |
| L1 assessment 实际值 | `outputs/submission_evidence/L1/.../02_AGENT/agent_assessment_01.json` | — |

---

## 与"真正 Agent 决策"的差距

**最大差距：当前 ACCEPT/RETRY 完全由 Python 阈值（fitness ≥ 0.8）决定，
Agnes 没有任何判断"结果是否值得重试"或"是否应该放弃"的自由度。**
若要实现真正的 Agent 决策，需要：
1. 将 `agnnes_assess` 替换为真实 LLM 调用，让它判断 ACCEPT/RETRY/ABORT；
2. 在 prompt 里给 Agnes fitness 值 + 历史尝试记录，让它自主判断；
3. 在 `run_agent_case` 循环里真正支持 ABORT 终止条件（而非仅 RETRY）。
