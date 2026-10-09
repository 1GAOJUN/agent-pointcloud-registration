# B3A_HANDOFF — Real Agnes + Active Probe / L1 Frozen Blind Validation

**Phase B3A 完成时间**：2026-10-07
**Run ID**：`b3_l1_20261007_seed101_blind02`
**Run Status**：`PASS`

---

## 1. B3 Freeze Manifest 路径

`outputs/submission_evidence/B3/L1/runs/b3_l1_20261007_seed101_blind02/00_INDEX/B3_SYSTEM_FREEZE_MANIFEST.json`

所有冻结源文件 SHA-256 与 B2B 一致（无代码修改）。

---

## 2. 本次 run_id

`b3_l1_20261007_seed101_blind02`

前一个 incident run（`b3_l1_20261007_seed101_blind01`）因 ENV_R1 Open3D DLL 阻塞中止，
不产生正式结果，不计入 RUN_INDEX。

---

## 3. 系统是否被修改

**否。** B3A 全程未修改任何冻结源码（agent_probes / agnnes_agent / agent_tools /
agent_diagnose / agent_evaluator / agent_runner / evaluate）。
新增文件均为 `tests/_b3a_*.py`（辅助脚本，不进入冻结范围）和证据文档。

---

## 4. 正式结果摘要

| 项目 | 值 |
|---|---|
| 匿名 case | case_unknown_A（底层 seed_101，L1） |
| Basic Diagnosis | src=30000pts, tgt=30282pts, base_scale=0.004997, centroid_dist=0.393 |
| Agnes 是否请求 Probe | 是（3 轮决策） |
| Probe 顺序 | PCA_ORIENTATION → CHEAP_LOCAL_ICP（均由 Agnes 自主决定） |
| PCA observation | rot_estimate=16.09°, MEDIUM confidence, partial_axis_degeneracy |
| Cheap ICP observation | fitness=0.0（零对应），transform_delta=0.0 |
| Agnes 正式选择 | **GLOBAL_FPFH_RANSAC_ICP**，global_corr_scale=5.0, icp_max_corr_scale=2.0 |
| Attempt 数量 | 1（无 RETRY） |
| 可观测指标 | fitness=1.0, rmse=0.00142, elapsed_s=287.8 |
| Agent 最终 decision | **ACCEPT**（confidence=0.99） |
| GT rot_err_deg | 0.948°（阈值 5.0° → PASS） |
| GT trans_err | 0.000837（阈值 0.05 → PASS） |
| GT success | **True** |
| Run Status | **PASS** |

---

## 5. Evidence 路径

```
outputs/submission_evidence/B3/L1/runs/b3_l1_20261007_seed101_blind02/
├── 00_INDEX/
│   ├── B3_SYSTEM_FREEZE_MANIFEST.json
│   ├── run_manifest.json
│   ├── metrics_summary.json
│   └── run_summary.md
├── 01_AGH/
│   ├── agnnes_decision_prompt_01/02/03.json
│   ├── agnnes_raw_decision_01/02/03.json
│   ├── agnnes_assessment_prompt.json
│   ├── agnnes_raw_assessment.json
│   └── SCREENSHOT_CHECKLIST.md
├── 02_AGENT/
│   ├── diagnosis.json
│   ├── input_summary.json
│   ├── probe_observation_01.json  (PCA)
│   ├── probe_observation_02.json  (Cheap ICP)
│   ├── agnnes_decision_01/02/03_parsed.json
│   ├── decision_final.json
│   ├── observation_01.json
│   ├── metrics.json
│   ├── agent_assessment_01.json
│   ├── agent_final_assessment.json
│   ├── agnnes_assessment_parsed.json
│   ├── evaluator_result.json
│   └── agh_run_log.json
├── 03_TOOL_CHAIN/
│   ├── tool_call_01.json
│   └── TOOL_CHAIN.md
├── 04_CONFIG/
│   └── parameters.json
├── 05_VALIDATION/
│   └── B3A_VALIDATION.md
├── 06_VISUALS/
│   └── (before/after/compare 由 06_VISUALS 生成脚本填充)
├── attempts/
│   └── attempt_01/
│       ├── decision.json
│       ├── probe_requests.json
│       ├── probe_observations.json
│       ├── parameters.json
│       ├── tool_call.json
│       ├── observation.json
│       ├── assessment.json
│       ├── metrics.json
│       └── attempt_01_summary.json
└── B3A_FROZEN.md
```

RUN_INDEX：`outputs/submission_evidence/B3/L1/RUN_INDEX.csv`

---

## 6. B3B 必须复用的代码/config/hash

以下文件及其 SHA-256（见 freeze manifest）在 B3B 必须保持完全一致：

| 文件 | SHA-256（前 16 位） |
|---|---|
| src/agent_probes.py | B93139892ABB642C |
| src/agnnes_agent.py | A8149C7A651E70E8 |
| src/agent_tools.py | 8B681CC2D3CB0C1F |
| src/agent_diagnose.py | 7C1E089EFBBB52C3 |
| src/agent_evaluator.py | B0A7736FC1E3B134 |
| src/agent_runner.py | C567DA5937E6C459 |
| src/evaluate.py | CAF1FF7AFA5ACEC1 |

**B3B 不得修改以上任何文件。** 若 B3B 需要新 Probe 或参数范围，须先走独立 Phase 修改并重新生成 freeze manifest。

---

## 7. B3B 不得知道的 L1 实验内容范围

B3B 使用 L2/L3/L4 case 时，**不得**将以下 B3A L1 实验信息带入 Agnes 决策上下文：

- L1 seed_101 的 GT 结果（rot_err=0.948°, trans_err=0.000837, success=True）
- L1 seed_101 的 PCA probe 具体数值（rot=16.09° MEDIUM）
- L1 seed_101 的 Cheap ICP probe 结果（fitness=0.0）
- L1 seed_101 的 Agnes 最终选择（GLOBAL_FPFH_RANSAC_ICP）及参数（global=5.0, icp=2.0）
- 任何"L1 应该选 GLOBAL/LOCAL"的先验结论

B3B 只能使用：
- 冻结的系统代码（SHA-256 核验一致）
- 各 case 自己的匿名 diagnosis + probe observations
- 相同的 Agnes 模型（agnes-3.0-flash）+ 相同的 subagent_fork 调用模式

---

## 8. 已知限制 / 后续

- `06_VISUALS/` before.png / after.png / compare.png 已正常生成；metrics_panel.png 因 post-core transport 中断缺失，已在 B3A-R2 离线恢复
- B3A 全程 1 次 RETRY 未发生（Agnes ACCEPT 一次通过），`attempts/attempt_02/` 不存在
- L2/L3/L4 正式盲测属 B3B，本 handoff 不执行

---

## 9. Transport Incident（B3A-R2 Recovery）

B3A 核心实验完成后，Evidence/Visualization Closeout 阶段发生 AGH harness session transport 失败。
核心实验无需重跑。详见：`B3A_TRANSPORT_INCIDENT.md` 和 `B3A_CLOSEOUT_RECOVERED.md`。

| 项目 | 状态 |
|---|---|
| B3A 核心实验 | COMPLETE |
| Transport 中断 | 仅发生在可视化收尾阶段 |
| Agnes 是否重新调用 | **否** |
| Registration 是否重跑 | **否** |
| GT Evaluator 是否重跑 | **否** |
| before/after/compare PNG | 未修改 |
| metrics_panel.png | 离线恢复（B3A-R2） |
| B3A Frozen 状态 | 维持 |

---

## 10. B3B 启动要求（摘要）

- 使用相同 B3 freeze manifest（SHA-256 核验），**全新 AGH session**
- 不得将 B3A L1 实验内容带入 B3B Agnes 上下文
- B3B 启动前确认 Open3D 渲染可用（当前环境存在 BLAS zombie process 干扰）
- 仅 L2/L3/L4 盲测 case；新 Probe 或参数范围变更须先走独立 Phase
