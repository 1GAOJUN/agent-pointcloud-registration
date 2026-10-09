# REFERENCE RUN — L1

## 当前 L1 参考 Run
`l1_20261007_seed101_run01`

对应原始 run_id：`l1_seed_101`（`outputs/agent_runs/l1_seed_101/`，未修改）
整理后位置：`runs/l1_20261007_seed101_run01/`（本包内）

## 为什么选它作为参考 Run
1. **第一份完整 AGH Agent 闭环证据**：diagnosis → Agnes decision → tool call
   → observation → Agnes assessment → independent GT evaluator，全链路
   文件齐全，可逐步追溯（见 `03_TOOL_CHAIN/TOOL_CHAIN.md`）。
2. **GT 隔离成立**：`tool_call_01.json` 记录 `gt_read=false`；
   `evaluator_result.json` 明确 `gt_evaluator=true`，GT 只在 Agent 停止后
   被读取。
3. **结构化 decision / tool / assessment 完整**：`decision_01.json`、
   `agent_assessment_01.json`、`agent_final_assessment.json`、
   `tool_call_01.json`、`observation_01.json` 均为可机读 JSON，非聊天记录。
4. **专业验证 PASS**：独立 Evaluator 读 GT 得 rotation_error = 0.0°、
   translation_error ≈ 1.39e-17，success = true。
5. **可视化完整**：`before.png` / `after.png` / `compare.png` /
   `compare_zoomed.png` / `metrics_panel.png` 均基于真实输入点云与真实
   估计 transform 生成，未修改数据。

## REFERENCE 的含义与限制
- "REFERENCE" 只表示**这是当前 L1 用于对照 / 回归 / 复现检查的基准**，
  不意味着 L1 关卡被禁止再次运行。
- 以后任何新的 L1 实验（回归测试、bug 修复后的验证、最终复现检查等）：
  - 必须生成**新的 run_id**（例如 `l1_20261008_seed202_run01`，或在 seed
    不变时用 `l1_20261010_seed101_run02` 之类的新序号）
  - 写入 `runs/<新run_id>/`
  - **绝不覆盖、修改或删除** `runs/l1_20261007_seed101_run01/` 与
    `outputs/agent_runs/l1_seed_101/`
- 本参考 Run 的完整冻结声明见
  `runs/l1_20261007_seed101_run01/00_INDEX/L1_FROZEN.md`。

## 冻结事实（再次核对值，以实际文件为准）
- Selected Method：`GLOBAL_FPFH_RANSAC_ICP`
- Agent policy：`global_corr_scale = 5.0`，`icp_max_corr_scale = 2.0`
- `base_scale = 0.033892031543267295`
- 派生：RANSAC correspondence = 0.1694601577163365，
  ICP correspondence = 0.06778406308653459
- Agent Verdict：`ACCEPT`
- Observable：fitness = 1.0000，RMSE = 1.0480573452953922e-16，
  runtime = 0.7089753000000201 s
- Independent GT：rotation error = 0.0 deg，translation error =
  1.3877787807814457e-17，**PASS**
（以上与 `00_INDEX/run_manifest.json`、`03_TOOL_CHAIN/observation_01.json`、
`05_VALIDATION/evaluator_result.json` 实际值逐一核对一致，无冲突。）
