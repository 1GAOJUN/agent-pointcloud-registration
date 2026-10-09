# B3A_VALIDATION — b3_l1_20261007_seed101_blind02

逐项防作弊/泄漏验证：

| # | 检查项 | 结果 | 依据 |
|---|-------|------|------|
| 1 | GT leakage | PASS | Agnes decision/assessment prompts 不含 gt_transform/rotation_error/translation_error；evaluator_result.json 仅在 Agent 停止后生成 |
| 2 | Level label leakage | PASS | Agnes 输入只见 "case_unknown_A / source_cloud / target_cloud"；meta.json 中的 level="L1" 从未传入 Agnes prompt |
| 3 | Path leakage | PASS | 所有 Agnes prompt 中路径以 "source_cloud (path withheld)" 形式出现；diagnosis.json 不含磁盘路径 |
| 4 | Historical answer leakage | PASS | Agnes 输入不含 B2A/B2B 冒烟结果、heuristic baseline 结果、历史 GLOBAL 成功结果 |
| 5 | Python method selection | PASS | selected_method 来自 agnnes_raw_decision_03.json（subagent_fork 输出），Python 仅 validate + dispatch |
| 6 | Python probe selection | PASS | 每个 probe_observation_NN.json 的 _probe_request.requested_by="agnnes_real"；Python 无自动 Probe 分支 |
| 7 | Python ACCEPT/RETRY selection | PASS | agent_final_assessment.json 来自 agnnes_raw_assessment.json（subagent_fork），Python guardrail 仅检查 floor_fitness=0.3（未触发） |
| 8 | Real Agnes invocation | PASS | 3 次 decision + 1 次 assessment 均经 subagent_fork 调用 agnes-3.0-flash；raw JSON 已落盘 |
| 9 | B2B Active Probe path | PASS | 2 个 Probe 均经 Agnes 请求触发；Python 只做白名单+去重+配额校验 |
| 10 | Freeze manifest integrity | PASS | 所有冻结源文件 SHA-256 与 B3_SYSTEM_FREEZE_MANIFEST.json 一致（生成时核验） |
