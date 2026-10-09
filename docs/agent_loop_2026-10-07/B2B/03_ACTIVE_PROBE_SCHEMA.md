# 03_ACTIVE_PROBE_SCHEMA — B2B 主动观测 Agnes 决策 Schema 扩展

**Phase B2B — Active Observation Probe**
创建：2026-10-07
实现：`src/agnnes_agent.py`（`validate_decision` / `build_decision_prompt` / `build_probe_prompt` / `AgnesDecisionAdapter`）
Probe 层：`src/agent_probes.py`（`PROBE_REGISTRY` / `PROBE_DISPATCH` / `MAX_PROBES_PER_RUN`）

---

## 1. 决策流（B2B 扩展后）

```
Basic Diagnosis（GT-free，Python）
      ↓
Agnes decision #1（信息是否足够？）
      ├─ YES → requested_probe=NONE, selected_method + parameter_policy（正式方法）
      └─ NO  → requested_probe ∈ {PCA_ORIENTATION, CHEAP_LOCAL_ICP}
                  ↓
              Python: validate（白名单 + 去重 + 配额）→ dispatch → Probe Observation
                  ↓
              Agnes decision #2（diagnosis + 全部 Probe 观测 + 工具/参数元数据）
                  ├─ 仍 NO 且配额未耗尽 → 请求另一个 Probe（最多 MAX_PROBES_PER_RUN=2 个不同 Probe）
                  └─ YES → selected_method + parameter_policy
                        ↓
              正式工具执行（LOCAL_ICP / GLOBAL_FPFH_RANSAC_ICP）
                        ↓
              Agnes assessment（ACCEPT / RETRY / ABORT）
                        ↓
              独立 Evaluator（GT 只在此时读取）
```

## 2. Probe 注册

- `PROBE_REGISTRY`（`agent_probes.py`）：Probe 元数据（purpose/returns/cost/limitations），
  注入 decision prompt 的 `probes.available_probes` 字段
- `PROBE_DISPATCH`：`{probe_name: callable}`，仅接受白名单名字，其他 → ValueError
- Probe 是"观测工具"，**不进入** `agent_tools.TOOL_REGISTRY`（正式配准算法候选）
- **Python 不基于任何诊断指标自动选择 Probe**；触发条件唯一：Agnes 输出的 `requested_probe`

## 3. Decision JSON Schema（B2B 扩展）

两种合法形态（`information_sufficient` 布尔 + `requested_probe` 枚举联动）：

### 形态 A：信息充分（直接选正式方法）

```json
{
  "observation_summary": "...",
  "information_sufficient": true,
  "requested_probe": "NONE",
  "candidate_methods": [{"method": "...", "pros": "...", "risks": "..."}],
  "selected_method": "LOCAL_ICP | GLOBAL_FPFH_RANSAC_ICP",
  "parameter_policy": {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0},
  "reasoning_summary": "...",
  "confidence": 0.7
}
```

### 形态 B：信息不足（请求 Probe）

```json
{
  "observation_summary": "...",
  "information_sufficient": false,
  "requested_probe": "PCA_ORIENTATION | CHEAP_LOCAL_ICP",
  "probe_reason": "为什么该 Probe 能补充信息（必填）",
  "selected_method": null,
  "parameter_policy": null,
  "reasoning_summary": "...",
  "confidence": 0.4
}
```

## 4. Guardrail 校验规则（`validate_decision`）

| 规则 | 类型 |
|---|---|
| `requested_probe ∈ {NONE, PCA_ORIENTATION, CHEAP_LOCAL_ICP}` | 白名单（deterministic） |
| 形态 A：`requested_probe=NONE` 且 `selected_method` 必填 | schema |
| 形态 B：`selected_method=null`，`probe_reason` 非空 | schema |
| 不得重复请求已执行的 Probe（`probes_already_run`） | 去重（deterministic） |
| `len(probes_already_run) >= MAX_PROBES_PER_RUN(=2)` → 禁止再请求 | 配额（deterministic） |
| 参数范围（global_corr_scale ∈ [2,10]，icp_max_corr_scale ∈ [0.5,5]） | guardrail（B2A 沿用） |

**顺序由 Agnes 决定，Python 不规定 Probe 顺序（B2B 原则 §12）**：
Python 只允许 `MAX_PROBES_PER_RUN=2` 这一合法配额 guardrail。

## 5. Probe 观测回灌

- Probe 结果（GT-free 可观测指标）写入 `probes.observations` + `probes.already_executed`
  注入下一轮 decision prompt
- 评估 prompt 也附带 `probe_observations` 供 Agnes 评估时参考
- Probe 观测**不含** GT 字段，**不含**磁盘路径，**不含**场景标签

## 6. 防止无限探测

- 配额耗尽后 `validate_decision` 对形态 B 直接返回 schema error
- 冒烟脚手架在配额耗尽轮强制 Agnes 给出 `information_sufficient=true` + 正式方法，
  若仍请求 Probe → 终止并记录（`smoke_stop_report.json`）
