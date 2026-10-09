# B3B_HANDOFF — Real Agnes + Active Probe / L2 Frozen Blind Validation

**Phase B3B 完成时间**：2026-10-07
**Run ID**：`b3_l2_20261007_seed202_blind01`
**Run Status**：`PASS`
**Core Frozen**：`TRUE`（`00_INDEX/B3B_CORE_FROZEN.md` 存在）

---

## 1. B3 Freeze Manifest 路径

`outputs/submission_evidence/B3/L1/runs/b3_l1_20261007_seed101_blind02/00_INDEX/B3_SYSTEM_FREEZE_MANIFEST.json`

所有 9 个冻结源文件 SHA-256 核验一致（`frozen_hash_verified=true`）。

---

## 2. 本次 run_id

`b3_l2_20261007_seed202_blind01`

无 incident run；本次为唯一正式 B3B L2 run。

---

## 3. 系统是否被修改

**否。** B3B 全程未修改任何冻结源码（agent_probes / agnnes_agent / agent_tools /
agent_diagnose / agent_evaluator / agent_runner / evaluate）。
辅助脚本 `tests/_b3b_evaluator.py` 和 `_b3b_preflight.py` 为新增，不进入冻结范围。

---

## 4. 正式结果摘要

| 项目 | 值 |
|---|---|
| 匿名 case | case_unknown_B（底层 seed_202，L2） |
| Basic Diagnosis | src=30000pts, tgt=30000pts, base_scale=0.033885, centroid_dist=0.559 |
| Agnes 是否请求 Probe | 是（2 轮决策） |
| Probe 顺序 | PCA_ORIENTATION → CHEAP_LOCAL_ICP（均由 Agnes 自主决定） |
| PCA observation | rot_estimate=null, LOW confidence, near_line_degeneracy（两 cloud 均触发） |
| Cheap ICP observation | initial_fitness=0.1366, probe_fitness=0.1650, transform_delta=0.2222, 5 iterations |
| Agnes 正式选择 | **GLOBAL_FPFH_RANSAC_ICP**，global_corr_scale=4.0, icp_max_corr_scale=1.0 |
| 实际参数（Python 推导） | ransac_max_corr_dist=0.13554, icp_max_corr_dist=0.033885 |
| Attempt 数量 | 1（无 RETRY） |
| 可观测指标 | fitness=1.0, rmse=1.63e-16, elapsed_s=0.582 |
| Agent 最终 decision | **ACCEPT**（confidence=0.97，无 guardrail overwrite） |
| GT rot_err_deg | 0.0（阈值 5.0° → PASS） |
| GT trans_err | 0.0（阈值 0.05 → PASS） |
| GT success | **true** |
| Run Status | **PASS** |

---

## 5. Evidence 路径

```
outputs/submission_evidence/B3/L2/runs/b3_l2_20261007_seed202_blind01/
├── 00_INDEX/
│   ├── B3B_CORE_STATE.json
│   ├── B3B_CORE_FROZEN.md
│   └── run_manifest.json
├── 01_AGH/
│   ├── agnnes_decision_prompt_01/02.json
│   ├── agnnes_raw_decision_01/02/03.json
│   ├── agnnes_assessment_prompt.json
│   ├── agnnes_raw_assessment.json
│   └── SCREENSHOT_CHECKLIST.md
├── 02_AGENT/
│   ├── diagnosis.json
│   ├── decision_input_snapshot.json
│   ├── input_summary.json
│   ├── probe_observation_01.json  (PCA_ORIENTATION)
│   ├── probe_observation_02.json  (CHEAP_LOCAL_ICP)
│   ├── agnnes_decision_01/02/03_parsed.json
│   ├── agnnes_assessment_parsed.json
│   ├── agent_assessment_01.json
│   ├── agent_final_assessment.json
│   ├── decision_final.json
│   ├── observation_01.json
│   └── metrics.json
├── 03_TOOL_CHAIN/
│   ├── tool_call_01.json
│   └── TOOL_CHAIN.md
├── 04_CONFIG/
│   └── parameters.json
├── 05_VALIDATION/
│   ├── B3B_VALIDATION.md
│   ├── evaluator_result.json
│   ├── metrics_summary.json
│   └── run_summary.md
├── 06_VISUALS/
│   ├── before.png
│   ├── after.png
│   ├── compare.png
│   └── metrics_panel.png
├── attempts/
│   └── attempt_01/
│       ├── agent_assessment_01.json
│       ├── agent_final_assessment.json
│       ├── agnnes_assessment_parsed.json
│       ├── attempt_summary.json
│       ├── evaluator_result.json
│       ├── metrics.json
│       ├── observation_01.json
│       ├── parameters.json
│       └── tool_call_01.json
└── evaluator_result.json  (run-level copy)
```

RUN_INDEX：`outputs/submission_evidence/B3/L2/RUN_INDEX.csv`

---

## 6. B3B Leakage & Integrity Audit

`05_VALIDATION/B3B_VALIDATION.md` 11 项检查全部 PASS：

| 检查项 | 结果 |
|---|---|
| GT 泄漏 | PASS（GT 仅在 stage 8 读取） |
| Level label 泄漏 | PASS（无 L1/L2/L3/L4 出现在 Agnes-visible 文件） |
| Seed 语义泄漏 | PASS（sampling_seed=101 是 frozen 实现常数，非数据生成 seed 202） |
| 磁盘路径泄漏 | PASS |
| 历史结果泄漏 | PASS |
| **B3A 结果泄漏** | **PASS**（B3B 全程未读 B3A 任何文件） |
| Python 自动选法 | PASS（selected_method 来自真实 Agnes） |
| Python 自动 Probe | PASS（probe 顺序由两次独立 Agnes 决策产生） |
| Python 自动 ACCEPT | PASS（guardrail 未覆写） |
| 真实 Agnes 调用 | PASS（4 次 subagent_fork，_implementation=agnnes_real） |
| Freeze 完整性 | PASS |

---

## 7. Transport Incident（B3B Closeout）

核心实验完成后，AGH 会话 transport 中断（客户端热点断开）。
中断发生在 RUN_INDEX.csv 行写入之前；RUN_INDEX 行已在离线恢复中补写。

| 项目 | 状态 |
|---|---|
| B3B 核心实验 | COMPLETE |
| B3B_CORE_FROZEN | COMPLETE（存在） |
| Transport 中断影响 | 仅 RUN_INDEX.csv 行缺失（已补写） |
| Agnes 是否重新调用 | **否** |
| Registration 是否重跑 | **否** |
| GT Evaluator 是否重跑 | **否** |
| Visuals（4 张 PNG） | 未修改，全部存在 |
| B3B Frozen 状态 | 维持 |

详见：`docs/agent_loop_2026-10-07/B3B_NETWORK_TRANSPORT_INCIDENT.md`

---

## 8. 已知限制 / 后续

- L3、L4 正式盲测 case 尚未执行；属后续 B3 扩展轮次。
- `diagnosis.json` 中 `overlap_ratio`、`noise_level`、`outlier_level`、
  `rotation_magnitude_estimate` 均为 `NOT_IMPLEMENTED`（B2B frozen 实现局限，
  非 B3B 缺陷）。
- B3B 单 attempt 一次通过，无 RETRY 路径实际触发。

---

## 9. B3B 启动前提（摘要）

- 使用 B3 freeze manifest（SHA-256 核验），全新 AGH session
- 不得将 B3A L1 实验内容带入 B3B Agnes 上下文（已验证 PASS）
- Open3D 0.20.0 / Python 3.11.16 环境已确认
- L2 seed_202 case 完成；L3/L4 case 待后续轮次
