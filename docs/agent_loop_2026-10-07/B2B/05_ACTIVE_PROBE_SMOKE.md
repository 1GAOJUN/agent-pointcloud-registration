# 05_ACTIVE_PROBE_SMOKE — B2B 主动观测冒烟测试记录

**Phase B2B — Active Observation Probe**
执行：2026-10-07
Case：`outputs/ICP/L1/L1/seed_101`（仅开发冒烟，**不进 L1/L2 正式 RUN_INDEX**）
证据目录：`outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/`
脚手架：`tests/_b2b_smoke_scaffold.py`（Python 确定性部分）+ AGH 会话 `subagent_fork`（真实 Agnes 调用）

---

## 冒烟 10 项检查

| # | 检查项 | 结果 |
|---|---|---|
| 1 | Basic diagnosis 进入真实 Agnes | ✅ PASS（`agnnes_decision_prompt_01.json` 含完整 diagnosis，经 `subagent_fork` 发给 agnes-3.0-flash） |
| 2 | Agnes 真实决定是否请求 Probe | ✅ PASS（decision #1：`information_sufficient=false`，非 Python 预设） |
| 3 | requested_probe 来自 Agnes | ✅ PASS（`agnnes_raw_decision_01.json` 原文 `requested_probe="PCA_ORIENTATION"`） |
| 4 | Python 执行对应 Probe | ✅ PASS（白名单校验后 dispatch → `probe_observation_01.json`） |
| 5 | Probe observation 返回 Agnes | ✅ PASS（`agnnes_decision_prompt_03.json` 的 `probes.observations` 含两条 Probe 结果 + `already_executed`） |
| 6 | Agnes 基于新信息产生后续决策 | ✅ PASS（decision #2 看到 PCA LOW 后改请求 CHEAP_LOCAL_ICP；decision #3 看到 ICP probe 后选 LOCAL_ICP） |
| 7 | selected_method 仍来自真实 Agnes | ✅ PASS（`agnnes_raw_decision_03.json`：`LOCAL_ICP`，confidence 0.78） |
| 8 | 参数仍来自真实 Agnes | ✅ PASS（`icp_max_corr_scale=2.5`，guardrail [0.5,5.0] 内，非 Python 注入） |
| 9 | assessment 仍来自真实 Agnes | ✅ PASS（`agnnes_raw_assessment.json`：ACCEPT，confidence 0.9，无 guardrail 覆写） |
| 10 | GT 隔离 PASS | ✅ PASS（全部 `agnnes_*` 文件关键词扫描无 `gt_transform/rotation_error/translation_error/L1/L2`；Evaluator 在 Agent 停止后运行） |

**Smoke Test 总体结果：PASS**

---

## 实际执行轨迹（逐轮）

### Round 1 — Agnes decision #1（`agnnes_raw_decision_01.json`）

Agnes 看到 diagnosis（`rotation_magnitude_estimate=NOT_IMPLEMENTED`），判定信息不足：

```json
{
  "information_sufficient": false,
  "requested_probe": "PCA_ORIENTATION",
  "probe_reason": "rotation_magnitude_estimate is NOT_IMPLEMENTED, which is the main
    uncertainty separating LOCAL_ICP from GLOBAL_FPFH_RANSAC_ICP. PCA_ORIENTATION
    gives a coarse relative orientation at negligible cost...",
  "selected_method": null,
  "confidence": 0.72
}
```

→ Python dispatch → `probe_observation_01.json`

### Probe 1 — PCA_ORIENTATION（真实 L1 seed_101 数据）

```json
{
  "probe_name": "PCA_ORIENTATION",
  "rotation_estimate_deg": null,
  "orientation_confidence": "LOW",
  "ambiguity_detected": true,
  "ambiguity_reason": "near_line_degeneracy (λ1≈λ2; transverse axes undetermined); near_line_degeneracy ...",
  "source_anisotropy": 2.8291,
  "target_anisotropy": 2.8291,
  "source_eigenvalues": [0.1164712, 0.04453601, 0.04116888],
  "target_eigenvalues": [0.1164712, 0.04453601, 0.04116888],
  "runtime_s": 0.0242
}
```

L1 点云主方向结构不稳定（λ1≈λ2），Probe 正确返回 LOW + null，**不伪造角度**。

### Round 2 — Agnes decision #2（`agnnes_raw_decision_02.json`）

Agnes 看到 PCA LOW confidence 后（B2B 原则 §13 的关键能力——识别"不确定"）：

```json
{
  "information_sufficient": false,
  "requested_probe": "CHEAP_LOCAL_ICP",
  "probe_reason": "PCA orientation is LOW confidence and rotation magnitude is unknown;
    a cheap local ICP convergence signal will indicate whether the initial transform is
    already near a local optimum...",
  "selected_method": null,
  "confidence": 0.3
}
```

→ Python dispatch → `probe_observation_02.json`

### Probe 2 — CHEAP_LOCAL_ICP（L1 seed_101）

```json
{
  "probe_name": "CHEAP_LOCAL_ICP",
  "initial_fitness": 0.2356,
  "probe_fitness": 0.2764,
  "initial_rmse": 0.03706,
  "probe_rmse": 0.03692,
  "fitness_improvement": 0.0408,
  "correspondence_count": null,
  "iterations": 5,
  "runtime_s": 0.5107,
  "transform_delta_magnitude": 0.4083,
  "max_correspondence_distance": 0.06778
}
```

### Round 3 — Agnes decision #3（`agnnes_raw_decision_03.json`，配额耗尽后）

Agnes 基于两条 Probe 观测 + diagnosis 最终选择正式方法：

```json
{
  "information_sufficient": true,
  "requested_probe": "NONE",
  "selected_method": "LOCAL_ICP",
  "parameter_policy": {"global_corr_scale": null, "icp_max_corr_scale": 2.5},
  "reasoning_summary": "PCA probe is LOW-confidence and null-angle, so no angle-based
    algorithm choice is warranted. The 5-iteration cheap ICP probe from identity init
    improved fitness (+0.041)... committing to LOCAL_ICP with a slightly widened
    correspondence scale (2.5× base)... balances robustness against the moderate
    misalignment without paying the global cost...",
  "confidence": 0.78
}
```

**注意**：正式 LOCAL_ICP 的 `icp_max_corr_scale` 由 Agnes 选 2.5（不是 Probe 的固定 2.0，
也不是 B2A 冒烟的 2.0），证明参数策略确实由 Agnes 基于 Probe 新信息作出，非 Python 写死。

### 工具执行（按 Agnes 选择）

`LOCAL_ICP`，`icp_max_corr_scale=2.5`，`base_scale=0.033892` → `observation_01.json`：
`fitness=1.0, rmse≈2.4e-16, elapsed_s=0.72`

### Agnes assessment（`agnnes_raw_assessment.json`）

```json
{
  "decision": "ACCEPT",
  "reason": "Fitness 1.0 with rmse at machine precision indicates a fully converged
    LOCAL_ICP from identity init; no observable defect. Floor guardrail not triggered.
    Prior probe inconclusiveness does not invalidate a clean formal result.",
  "confidence": 0.9
}
```

Guardrail：`fitness=1.0 ≥ 0.3`，无覆写。

### Evaluator（Agent 停止后才读 GT）

`evaluator_result.json`：`success=true, rot_err_deg=0.0, trans_err≈1.2e-17`

---

## 防伪检查结果（B2B 原则 §19）

| 检查 | 结果 |
|---|---|
| 若删除/禁用真实 Agnes 调用，系统是否仍会自己选择 PCA / CHEAP_LOCAL_ICP？ | **不会。FAIL 条件不成立 → PASS。** `agent_probes.py` 与 `agnnes_agent.py` 中不存在基于诊断指标自动触发 Probe 的代码；Probe 仅在 `agnnes_raw_decision_NN.json`（真实 Agnes 输出）的 `requested_probe` 字段通过白名单+去重+配额校验后 dispatch |
| `probes_requested_by_agnnes` 与 Probe 观测文件一一对应 | ✅ 每个 `probe_observation_NN.json` 含 `_probe_request.requested_by="agnnes_real"` 及对应 round 的 `probe_reason` |
| 顺序是否由 Agnes 决定 | ✅ PCA → CHEAP_LOCAL_ICP 是 Agnes 两轮独立决策的结果（第 1 轮 PCA，第 2 轮 ICP），Python 未规定顺序 |
| 配额（MAX_PROBES_PER_RUN=2）耗尽后行为 | ✅ 第 3 轮 guardrail 强制 `information_sufficient=true`，Agnes 给出 LOCAL_ICP |

---

## 与 B2A 冒烟的差异（能力增量）

| | B2A smoke | B2B smoke |
|---|---|---|
| 信息不足时的行为 | 直接保守选 GLOBAL_FPFH_RANSAC_ICP | 可先调 Probe 补齐信息，再决策 |
| Agnes 是否识别 Probe 低置信度 | 无 Probe | ✅（PCA LOW → 改请求 ICP probe） |
| 参数是否受 Probe 影响 | 否（无 Probe） | ✅（`icp_max_corr_scale` 由 Agnes 基于 ICP probe 选 2.5） |
| 场景适应性 | L1/L2 同一路径 | Probe 观测可让 Agnes 在不同场景走不同决策路径 |

---

## 环境备注

- 本冒烟测试**不属于 L1/L2 正式 RUN_INDEX，不进 submission_evidence**
- 真实 Agnes 调用经 AGH `subagent_fork`（agnes-3.0-flash）；原始文本响应落盘 `agnnes_raw_decision_01/02/03.json` + `agnnes_raw_assessment.json`
- 本次 Agnes 第 3 轮响应前有一次 BOM/前缀文本，`parse_agnnes_decision` 已加强容错（去 BOM + 截取首尾花括号）
- 正式 LOCAL_ICP 与 Cheap ICP Probe 的成本差见 `02_CHEAP_ICP_PROBE.md`（≈16 倍 wall / 20 倍迭代）
