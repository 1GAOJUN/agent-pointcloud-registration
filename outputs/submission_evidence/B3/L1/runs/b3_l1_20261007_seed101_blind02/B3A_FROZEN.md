# B3A_FROZEN — 证据冻结声明

**Run ID**: b3_l1_20261007_seed101_blind02
**冻结时间**: 2026-10-07T20:15:00+08:00
**Run Status**: PASS

## 冻结范围

本 Run 产生的全部证据文件自此刻起**不得修改或覆盖**：

- `outputs/submission_evidence/B3/L1/runs/b3_l1_20261007_seed101_blind02/`
  - `00_INDEX/`（freeze manifest, run_manifest, metrics_summary, run_summary）
  - `01_AGH/`（Agnes raw decisions, prompts, assessment, SCREENSHOT_CHECKLIST）
  - `02_AGENT/`（diagnosis, parsed decisions, probe observations, observation, assessment, evaluator, agh_run_log）
  - `03_TOOL_CHAIN/`（tool_call_01, TOOL_CHAIN.md）
  - `04_CONFIG/`（parameters.json）
  - `05_VALIDATION/`（B3A_VALIDATION.md）
  - `06_VISUALS/`
  - `attempts/attempt_01/`（decision, probe_requests, probe_observations, parameters, tool_call, observation, assessment, metrics）
- `outputs/submission_evidence/B3/L1/RUN_INDEX.csv`

## 冻结依据

- B3A 正式盲测完成，Agent 已 ACCEPT，GT Evaluator 已运行
- 系统源码未被修改（SHA-256 与 freeze manifest 一致）
- 所有 Agnes 调用经 subagent_fork（agnes-3.0-flash）真实完成

## B3B 核验要求

B3B 使用相同 frozen 系统跑 L2 时，必须：
1. 重新验证 `00_INDEX/B3_SYSTEM_FREEZE_MANIFEST.json` 中所有 file_hashes_sha256 与当前工作树一致
2. 不得基于 B3A 结果修改任何冻结组件
3. 新 AGH 会话（不复用 B3A session key）
