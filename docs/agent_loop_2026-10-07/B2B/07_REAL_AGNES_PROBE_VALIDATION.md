# 07_REAL_AGNES_PROBE_VALIDATION — 真实 Agnes Probe 参与证据汇总

**Phase B2B — Active Observation Probe**
验证时间：2026-10-07
证据目录：`outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/`

---

## 验证标准

要证明"真实 Agnes 自主决定调用哪个 Probe、何时停止探测"，需满足：
1. `requested_probe` 字段由 Agnes 模型输出（非 Python 写死）
2. Probe 顺序由 Agnes 决定（Python 不规定 PCA→ICP 固定顺序）
3. Probe 结果确实回灌给 Agnes（观测进入下一轮 prompt）
4. Agnes 基于 Probe 结果改变决策路径
5. 低置信度 Probe 结果被 Agnes 识别为"信息不足"，而非强行使用
6. 关闭 Agnes 调用后，Python 侧无法自行产生 `requested_probe` 值

---

## 证据文件清单（`outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/`）

| 文件 | 说明 | 对应验证项 |
|---|---|---|
| `agnnes_decision_prompt_01.json` | 发给 Agnes 的第 1 轮 prompt（含 Probe 元数据，无观测） | 1, 3 |
| `agnnes_raw_decision_01.json` | **Agnes 原始输出 #1**（`requested_probe=PCA_ORIENTATION`） | 1, 2 |
| `agnnes_decision_01_parsed.json` | 解析 + guardrail 校验后 | 1 |
| `probe_observation_01.json` | Python 执行 PCA probe 的结果（含 `_probe_request.requested_by=agnnes_real`） | 4 |
| `agnnes_decision_prompt_02.json` | 第 2 轮 prompt（含 PCA 观测 + `already_executed=[PCA_ORIENTATION]`） | 3 |
| `agnnes_raw_decision_02.json` | **Agnes 原始输出 #2**（PCA LOW → 改请求 `CHEAP_LOCAL_ICP`） | 2, 5 |
| `probe_observation_02.json` | Python 执行 Cheap ICP probe 的结果 | 4 |
| `agnnes_decision_prompt_03.json` | 第 3 轮 prompt（含两条 Probe 观测 + 配额耗尽说明） | 3 |
| `agnnes_raw_decision_03.json` | **Agnes 原始输出 #3**（`information_sufficient=true, selected_method=LOCAL_ICP`） | 4 |
| `agnnes_decision_03_parsed.json` | 解析 + guardrail 校验（quota=2 已耗尽，校验通过） | 1 |
| `observation_01.json` | 正式 LOCAL_ICP 执行结果（fitness=1.0, rmse≈0） | 4 |
| `agnnes_assessment_prompt.json` | 评估 prompt（含 probe_observations） | 5 |
| `agnnes_raw_assessment.json` | **Agnes 原始评估输出**（ACCEPT, confidence=0.9） | — |
| `evaluator_result.json` | 独立 GT 评测（Agent 停止后才读 GT） | — |
| `B2B_SMOKE_EVIDENCE.json` | 完整冒烟证据摘要 + 10 项 checklist | 全部 |

---

## Agnes 模型信息

- **模型**：`agnes-3.0-flash`（AGH 当前会话模型）
- **调用机制**：AGH 会话 `subagent_fork`（派生独立子会话，真实调用 Agnes 模型）
- **调用次数（本次冒烟）**：decision ×3 + assessment ×1 = 4 次真实 Agnes 调用

---

## 原始 Agnes 输出摘录

### Decision #1（`agnnes_raw_decision_01.json`）

```json
{
  "information_sufficient": false,
  "requested_probe": "PCA_ORIENTATION",
  "probe_reason": "rotation_magnitude_estimate is NOT_IMPLEMENTED, which is the main
    uncertainty separating LOCAL_ICP from GLOBAL_FPFH_RANSAC_ICP. PCA_ORIENTATION gives
    a coarse relative orientation at negligible cost and directly addresses that uncertainty.",
  "selected_method": null,
  "confidence": 0.72
}
```

### Decision #2（`agnnes_raw_decision_02.json`）— 识别 PCA 低置信度

```json
{
  "observation_summary": "PCA_ORIENTATION probe returned LOW confidence with a null rotation
    estimate due to near-line degeneracy (lambda1≈lambda2) on both clouds...",
  "information_sufficient": false,
  "requested_probe": "CHEAP_LOCAL_ICP",
  "probe_reason": "PCA orientation is LOW confidence and rotation magnitude is unknown; a
    cheap local ICP convergence signal will indicate whether the initial transform is already
    near a local optimum...",
  "selected_method": null,
  "confidence": 0.3
}
```

**关键能力（B2B 原则 §13）**：Agnes 看到 `orientation_confidence=LOW` 后没有强行按 PCA
角度选算法，而是识别为"信息仍不足"，转请求第二个 Probe。这正是本轮新增的核心能力。

### Decision #3（`agnnes_raw_decision_03.json`）— 配额耗尽后选正式方法

```json
{
  "information_sufficient": true,
  "requested_probe": "NONE",
  "selected_method": "LOCAL_ICP",
  "parameter_policy": {"global_corr_scale": null, "icp_max_corr_scale": 2.5},
  "reasoning_summary": "PCA probe is LOW-confidence and null-angle... The 5-iteration cheap
    ICP probe from identity init improved fitness (+0.041)... committing to LOCAL_ICP with a
    slightly widened correspondence scale (2.5× base) balances robustness against the moderate
    misalignment without paying the global cost.",
  "confidence": 0.78
}
```

参数 `icp_max_corr_scale=2.5` 是 Agnes 基于 Cheap ICP Probe 的 `fitness_improvement=+0.041`
与 `transform_delta_magnitude=0.408` 自主选择（guardrail [0.5,5.0] 内），**非 Python 写死**
（B2A 冒烟用的是 2.0，本次 Agnes 根据 Probe 新信息选了不同的档位）。

### Assessment（`agnnes_raw_assessment.json`）

```json
{
  "decision": "ACCEPT",
  "reason": "Fitness 1.0 with rmse at machine precision indicates a fully converged LOCAL_ICP
    from identity init; no observable defect. Prior probe inconclusiveness does not invalidate
    a clean formal result.",
  "confidence": 0.9
}
```

---

## 防伪检查结果（B2B 原则 §19 专项）

| 检查 | 方法 | 结果 |
|---|---|---|
| 删除 Agnes 调用后 Python 是否仍自动选 Probe | grep `src/agent_probes.py` + `src/agnnes_agent.py`，确认无基于 `offset_proxy` / `rotation_estimate` / `fitness` 等诊断指标的 Probe 自动触发分支 | ✅ PASS：Probe 仅由 `agnnes_raw_decision_NN.json` 的 `requested_probe` 字段（经白名单+去重+配额校验）触发 |
| Probe 顺序是否由 Agnes 决定 | 对比 `agnnes_raw_decision_01`（PCA）与 `agnnes_raw_decision_02`（ICP）；`agent_probes.py` 中无顺序约束代码 | ✅ PASS |
| 每个 Probe 观测是否对应 Agnes 请求 | `probe_observation_01/02.json` 的 `_probe_request.requested_by="agnnes_real"` 及对应 round | ✅ PASS（一一对应） |
| 配额耗尽 guardrail | `validate_decision` 在 `len(probes_already_run)>=2` 时拒绝形态 B | ✅ PASS（第 3 轮 Agnes 被迫给正式方法） |
| Python 侧是否存在 `if 指标 > X: 自动跑 Probe` 分支 | grep 全 `src/` 目录 | ✅ 不存在 |

**结论：不存在 Python 自动 Probe 逻辑。**

---

## 与 Heuristic Baseline 的差异

| 决策点 | Heuristic Baseline（`@deprecated`，保留） | B2B 真实 Agnes 路径 |
|---|---|---|
| 信息不足时 | 无此概念（Python 直接 easy/hard 分支选算法） | Agnes 可先调 1–2 个 Probe 补齐观测再决策 |
| Probe 调用 | 无 | 由 Agnes 专业判断触发（本轮：PCA → ICP） |
| 参数策略 | 硬编码 `{global:5.0, icp:2.0}` | Agnes 基于 Probe 观测自由选择（本轮 icp=2.5） |
| LOW 置信度 Probe 结果 | 无（baseline 无 Probe） | Agnes 识别为"仍不足"，转请求另一 Probe |

**Heuristic baseline 路径完全不受 B2B 影响**，仍保留于 `agent_runner.heuristic_decide/assess`（`@deprecated`）。

---

## 不满足的项 / 后续工作

| 项 | 状态 | 说明 |
|---|---|---|
| 正式 L1/L2 盲测（B3） | ❌ 未执行 | 本轮只做开发冒烟，B3 才跑新 Agent 版本 L1/L2 盲测 |
| L2 场景下 Probe 的实际轨迹 | 仅成本 profile 用 L2 数据测过 Cheap ICP wall time（`_cost_profile.json`），未做 L2 全流程冒烟 | L2 大旋转场景的完整 Probe 轨迹验证留给 B3 |
| `correspondence_count` 真实数值 | Open3D 0.20 API 未直接暴露逐迭代匹配数，Probe 输出置 `null`（不伪造） | 未来可换 Open3D 版本或自行统计 |

---

## 验证结论

**真实 Agnes（agnes-3.0-flash）经 AGH `subagent_fork` 自主决定：(1) 信息不足时调用
PCA_ORIENTATION Probe；(2) 看到 PCA 低置信度后改调 CHEAP_LOCAL_ICP Probe；
(3) 配额耗尽后基于两条 Probe 观测 + diagnosis 选 LOCAL_ICP（icp_max_corr_scale=2.5）。
全程 Python 仅做白名单/去重/配额校验与工具调度，无任何自动 Probe 分支。**

**本轮验证的是"Agnes 主动获取观测信息的能力"，不是"Agnes 在 L2/L3/L4 场景的专业判断准确性"——
后者属于 B3 正式盲测。**
