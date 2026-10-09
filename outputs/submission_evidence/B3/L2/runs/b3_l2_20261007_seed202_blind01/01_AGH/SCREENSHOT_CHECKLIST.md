# Screenshot Checklist — b3_l2_20261007_seed202_blind01

人工最值得截图的 5 个 Agnes 交互时刻。不需要截图整轮 Conversation。

| # | 截图时刻 | 文件 | 说明 |
|---|---------|------|------|
| 1 | Agnes 第一次 Probe 请求 | `01_AGH/agnnes_raw_decision_01.json` | `information_sufficient=false`, `requested_probe=PCA_ORIENTATION`, confidence=0.62 |
| 2 | PCA Probe Observation | `02_AGENT/probe_observation_01.json` | `rotation_estimate_deg=null`, `orientation_confidence=LOW`, near_line_degeneracy |
| 3 | Agnes 第二次 Probe 请求 | `01_AGH/agnnes_raw_decision_02.json` | PCA LOW → 仍不足, `requested_probe=CHEAP_LOCAL_ICP`, confidence=0.45 |
| 4 | Agnes 正式 method + parameter_policy | `01_AGH/agnnes_raw_decision_03.json` | `information_sufficient=true`, `selected_method=GLOBAL_FPFH_RANSAC_ICP`, `parameter_policy={global_corr_scale:4.0, icp_max_corr_scale:1.0}`, confidence=0.68 |
| 5 | Agent 最终 ACCEPT/RETRY/ABORT | `01_AGH/agnnes_raw_assessment.json` | `decision=ACCEPT`, confidence=0.97, no guardrail overwrite |

**可选截图（GT Evaluator 结果）：**

| # | 截图时刻 | 文件 | 说明 |
|---|---------|------|------|
| 6 | GT Evaluator（Agent 停止后） | `05_VALIDATION/evaluator_result.json` | `rot_err_deg=0.0`, `trans_err=0.0`, `success=true` |

---

## 注意事项

- 截图 1–5 对应真实 Agnes LLM 调用（subagent_fork），不是 Python heuristic。
- 截图 6（GT Evaluator）仅在 Agent 最终 ACCEPT/ABORT 后读取 GT，不参与任何 Agnes 决策。
- 所有文件路径相对于 run 目录：`outputs/submission_evidence/B3/L2/runs/b3_l2_20261007_seed202_blind01/`
