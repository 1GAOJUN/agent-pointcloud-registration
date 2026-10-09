# L2 Evidence Package — README

## 本目录是什么
`outputs/submission_evidence/L2/` 是 L2 关卡（大角度旋转 + 干净数据）的
**证据整理目录**，采用全项目统一的 `Level → Run → Attempt` 结构（见
`outputs/submission_evidence/EVIDENCE_STRUCTURE.md`）。

## 本次 Run
- Run 目录名：`runs/l2_20261007_seed202_blind01/`
- 对应原始 run_id：`l2_20261007_seed202_blind01`
- 状态：**PASS**
- Phase：B0 L2 Frozen Blind Run（无 L2 标签感知，盲测）

## Agnes 模型
- `agnes-3.0-flash`，版本标识 `2026-10-06`
- AGH 会话标识（非敏感）：`70a7413c-5eec-42a1-94a6-7ad866957be9`

## Agent 选择的方法
`GLOBAL_FPFH_RANSAC_ICP`（Agnes 决策基于可观测诊断指标，非场景标签）

## 关键参数（Agent 策略层）
- `global_corr_scale = 5.0`
- `icp_max_corr_scale = 2.0`
- `base_scale = 0.03388506693216584`
- 派生实际阈值：
  - RANSAC max_corr = 0.1694253346608292
  - ICP max_corr = 0.06777013386433169

## Agent 最终判断
`ACCEPT`（可观测 fitness = 1.0 ≥ 0.8 阈值，首次 attempt 即通过）

## GT 最终验证结果（独立 Evaluator）
- rotation_error_deg = 1.7075472925031877e-06 deg
- translation_error = 0.0
- success = **PASS**（阈值 rot < 5.0°，trans < 0.05）
- 工具调用阶段 `gt_read = false`

## 六个子目录证明什么
| 目录 | 证明内容 |
|---|---|
| `00_INDEX/` | `run_manifest.json`、`L2_FROZEN.md`、`REPRODUCE.md`、`git_snapshot.txt`、`L1_L2_COMPARISON.md` |
| `01_AGH/` | `agh_run_log.json`、`diagnosis_input.json`、`SCREENSHOT_CHECKLIST.md` |
| `02_AGENT/` | `diagnosis.json`、`decision_01.json`、`agent_assessment_01.json`、`agent_final_assessment.json`、`decision_final.json` |
| `03_TOOL_CHAIN/` | `tool_call_01.json`、`observation_01.json`、`TOOL_CHAIN.md` |
| `04_CONFIG/` | `parameters.json`、`L2_config_snapshot.yaml` |
| `05_VALIDATION/` | `evaluator_result.json`、`metrics_summary.json`、`run_summary.md`、`PHASE_B0_VALIDATION.md` |
| `06_VISUALS/` | `before.png`、`after.png`、`compare.png`、`metrics_panel.png` |
| `attempts/attempt_01/` | 本次唯一 attempt 的完整文件（无 RETRY，不存在 attempt_02） |

## 原始运行证据路径（保持不变）
`outputs/agent_runs/l2_20261007_seed202_blind01/`

## 匿名 Case 说明
- 本 Run 使用的是 L2 seed_202 case（`outputs/ICP/L2/L2/seed_202/`）
- 但 Agent 决策阶段接收的输入名称为匿名 `source_cloud` / `target_cloud`
- 未向 Agnes Prompt 传递 L2 标签、路径字符串、GT 值或历史成功方法

## 历史对照
参考 L1 参考 Run：`l1_20261007_seed101_run01`（`outputs/submission_evidence/L1/`）
详见 `00_INDEX/L1_L2_COMPARISON.md`。
