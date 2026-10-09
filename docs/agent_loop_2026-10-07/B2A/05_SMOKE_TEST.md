# 05_SMOKE_TEST — B2A 真实 Agnes 冒烟测试记录

**Phase B2A — Real Agnes Decision Integration**
**执行时间：2026-10-07**
**测试 case：L1/seed_101（仅作冒烟测试，不进 L1/L2 正式 RUN_INDEX）**
**保存位置：`outputs/development_tests/B2A_REAL_AGNES_SMOKE/`**

---

## 冒烟测试目的

验证真实 Agnes 决策链路是否完整，**不用于证明 Agnes 在不同场景下的专业决策能力**（那是 L1/L2 正式实验的工作）。

验证清单（7 项）：

| 编号 | 检查项 | 结果 |
|---|---|---|
| 1 | 真实 Agnes 调用确实发生 | ✅ PASS |
| 2 | diagnosis 真实传给 Agnes | ✅ PASS |
| 3 | Agnes 真实输出 structured decision | ✅ PASS |
| 4 | dispatcher 按 Agnes 选择执行 | ✅ PASS |
| 5 | observation 传回 Agnes | ✅ PASS |
| 6 | Agnes 真实输出 ACCEPT/RETRY/ABORT | ✅ PASS |
| 7 | GT 只在最后由 Evaluator 读取 | ✅ PASS |

**Smoke Test 总体结果：PASS**

---

## 执行流程记录

### Step 1 — Diagnosis（Python，GT-free）

输入：`outputs/ICP/L1/L1/seed_101/source.ply` + `target.ply`

```json
{
  "source_point_count": 30000,
  "target_point_count": 30000,
  "density_ratio": 1.0,
  "centroid_distance": 0.3761,
  "base_scale": 0.03389,
  "rotation_magnitude_estimate": "NOT_IMPLEMENTED"
}
```

落盘：`diagnosis.json`

---

### Step 2 — 构造 Decision Prompt

调用 `agnnes_agent.build_decision_prompt(diagnosis, TOOL_REGISTRY, [])`，
生成完整 JSON 输入（不含 GT、场景标签、磁盘路径），落盘：`agnnes_decision_prompt.json`

---

### Step 3 — 真实 Agnes 第一次调用（策略决策）

通过 `subagent_fork`（AGH 官方机制）将 decision prompt 发送给 Agnes 模型，
Agnes 返回原始 JSON 文本，落盘：`agnnes_raw_decision.json`

**Agnes 决策内容摘要：**

```json
{
  "selected_method": "GLOBAL_FPFH_RANSAC_ICP",
  "parameter_policy": {
    "global_corr_scale": 5.0,
    "icp_max_corr_scale": 2.0
  },
  "confidence": 0.62,
  "information_sufficient": false,
  "reasoning_summary": "Because rotation magnitude, noise level, and overlap ratio are
    all unimplemented/unknown, a conservative fallback to a global registration
    pipeline is safer than identity-initialized ICP."
}
```

**B1 审计对比：** B1 中 heuristic hard branch 也选了 `GLOBAL_FPFH_RANSAC_ICP`
（因为 `offset_proxy ≈ 11.1 > 3.0`），但原因完全不同：
- heuristic：Python 固定阈值判断
- 真实 Agnes：LLM 基于"rotation_magnitude_estimate 不可用 → 不确定角度大小 →
  保守选全局"的专业推理

参数 5.0/2.0 的 Agnes 输出与 heuristic 相同是**因为这是 L1 场景下的合理选择，
不是因为 Python 强制注入**（guardrail 范围内，Agnes 自由选择了 5.0/2.0）。

---

### Step 4 — 工具执行（按 Agnes 选择）

```
tool_name = GLOBAL_FPFH_RANSAC_ICP
global_corr_scale = 5.0
icp_max_corr_scale = 2.0
base_scale = 0.03389
```

执行结果落盘：`observation_01.json`

```json
{
  "fitness": 1.0,
  "rmse": 0.0,
  "ransac_fitness": 1.0,
  "elapsed_s": 0.52,
  "tool_name": "GLOBAL_FPFH_RANSAC_ICP"
}
```

**与 Agnes 选择一致性检查：** `tool_name == Agnes selected_method` ✅

---

### Step 5 — 构造 Assessment Prompt

调用 `agnnes_agent.build_assessment_prompt(observation, [], method, policy)`，
生成包含可观测指标的 JSON（不含 GT），落盘：`agnnes_assessment_prompt.json`

---

### Step 6 — 真实 Agnes 第二次调用（评估）

通过 `subagent_fork` 将 assessment prompt 发送给 Agnes 模型，
Agnes 返回原始 JSON 文本，落盘：`agnnes_raw_assessment.json`

**Agnes 评估内容摘要：**

```json
{
  "decision": "ACCEPT",
  "confidence": 0.98,
  "reason": "fitness = 1.0 and rmse = 0.0 represent essentially perfect alignment;
    no plausible retry path could improve on a zero-error result."
}
```

**Guardrail 检查：**
- `fitness=1.0 ≥ FLOORGUARD_FITNESS=0.3` → 无需 guardrail 覆写 ✅
- `decision=ACCEPT` ∈ {ACCEPT, RETRY, ABORT} ✅
- `confidence=0.98` ∈ [0, 1] ✅

---

### Step 7 — 独立 Evaluator（GT 只在此时读取）

调用 evaluator（纯 Python 数学，绕过本环境 numpy BLAS crash），
读取 `gt_transform.npy`，落盘：`evaluator_result.json`

```json
{
  "gt_success": true,
  "rot_err_deg": 0.000001,
  "trans_err": 0.0
}
```

---

## 防伪检查结果

| 检查 | 结果 |
|---|---|
| A. 关闭 Agnes 调用后系统仍能决定 method？ | ❌ 不能（`heuristic_decide` 是独立路径，Agnes 路径需 subagent_fork） |
| B. 关闭 Agnes 调用后系统仍能决定 ACCEPT/RETRY？ | ❌ 不能（`heuristic_assess` 是独立路径） |
| C. 主路径存在 `offset_proxy ≥ 3.0 → GLOBAL` 直接映射？ | ❌ 不存在（该映射只在 `heuristic_decide` 里，不在 Agnes 路径） |

---

## 环境备注

- 本环境的 numpy 2.4.6 BLAS 路径崩溃（`R.T @ R` 触发 SIGSEGV），
  Evaluator 改用纯 Python 浮点数学计算，数值结果有效
- 工具执行层（Open3D ICP）在 conda env `pointcloud_agh` 中正常
- 冒烟测试保存位置：`outputs/development_tests/B2A_REAL_AGNES_SMOKE/`
- **本冒烟测试不属于 L1/L2 正式 RUN_INDEX，不进 submission_evidence**
