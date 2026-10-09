# AGH / Agnes Evidence README — l2_20261007_seed202_blind01

## 1. 本轮 Agnes 模型信息
- 模型名：`agnes-3.0-flash`
- 模型版本标识：`2026-10-06`
- AGH 会话 key：`70a7413c-5eec-42a1-94a6-7ad866957be9`
- run_id：`l2_20261007_seed202_blind01`
- 路由 / slot：`route=account-acct-72beee64-f559-4c9c-8096-306373f6c35c`, `slot=primary`
- 运行时间（runner）：2026-10-07（本地时间 UTC+8，见 `agh_run_log.json` 时间戳）
- Evaluator 落盘时间：见 `evaluator_result.json` 的 `timestamp` 字段

来源：`agh_run_log.json`、`evaluator_result.json`。

## 2. 哪些文件能够证明 Agnes 参与核心任务
- `01_AGH/agh_run_log.json`：`agent_model_name` / `agent_model_version`、任务
  prompt 摘要、对 decision/assessment 文件的显式引用。
- `02_AGENT/decision_01.json`（+ 内容一致的 `decision_final.json`）：结构化
  决策（selected_method / parameter_policy / reasoning / confidence）。
- `02_AGENT/agent_assessment_01.json` / `agent_final_assessment.json`：基于
  可观测指标的 ACCEPT/RETRY/ABORT 判断。

**重要如实说明**（与 L1 相同）：
本运行中 Agnes 的"决策"实际由 `src/agent_runner.py::agnes_decide` 里的确定性
启发式产出（模块 docstring 明确写明"此实现为可审计的启发式"），并通过 AGH/
Agnes 会话记录该模型名与版本作为执行链路的归属标识。这一实现方式本身应当在
评审说明中如实披露，不应被解读为"已验证 LLM 本身自动完成了算法选择"。

## 3. 哪些文件能够证明实际工具调用
- `03_TOOL_CHAIN/tool_call_01.json`：`tool_name=GLOBAL_FPFH_RANSAC_ICP`、
  `entrypoint=src.agent_tools.run_global_fpfh_ransac_icp`、`inputs`（匿名化
  source/target、base_scale、parameter_policy）、`gt_read: false`。
- `03_TOOL_CHAIN/observation_01.json`：该工具真实返回的
  `transform` / `fitness` / `rmse` / `ransac_fitness` / `ransac_rmse` /
  `elapsed_s` / `ransac_max_correspondence_distance` /
  `icp_max_correspondence_distance`。

## 4. 哪些文件能够证明 Agent 完成结果判断
- `02_AGENT/agent_assessment_01.json`：`decision=ACCEPT`，理由为
  `fitness=1.0000 ≥ 0.8` 阈值。
- `02_AGENT/agent_final_assessment.json`：内容一致（只有一次尝试，无 RETRY）。
- `02_AGENT/decision_final.json`：与 `decision_01.json` 一致。

## 5. 哪些文件能够证明 Evaluator 在 Agent 停止以后才读 GT
- `03_TOOL_CHAIN/tool_call_01.json` 的 `gt_read: false`：工具调用阶段不读 GT。
- `05_VALIDATION/evaluator_result.json` 的 `gt_evaluator: true` +
  `gt_path` + 独立 `timestamp`：时间戳晚于 runner 执行时间戳，与
  `src/agent_runner.py` 中 `evaluate_agent_result` 在 Agent 循环结束后才被
  调用的顺序一致。
- `src/agent_evaluator.py` 的 docstring："仅在 Agent 已 ACCEPT/ABORT 之后
  才允许读取 GT"，GT 文件的延迟导入保证了这一点。

## 6. 官方 AGH raw trace 状态
**NOT_AVAILABLE。**

原因：当前 AGH 运行环境没有开放"将某次 Agnes 会话导出为可提交文件"的能力
（无官方 session/execution trace 导出 API，AGH 自身用户数据目录中也没有本次
运行对应的落盘 trace）。

因此本包中所有 JSON / Markdown 文件应被描述为：

> **本次真实运行过程中落盘的结构化执行证据**（由 Agent Runner 本身写出的、
> 可逐字节核对的中间产物与结果记录）

而**不是**"AGH 官方原始日志 / 官方 execution record"。两者不可混用措辞。

## 完整文件清单（本 closeout 包）
- `01_AGH/`：`agh_run_log.json`、`diagnosis_input.json`、`SCREENSHOT_CHECKLIST.md`、本文件
- `02_AGENT/`：`diagnosis.json`、`decision_01.json`、`agent_assessment_01.json`、
  `agent_final_assessment.json`、`decision_final.json`
- `03_TOOL_CHAIN/`：`tool_call_01.json`、`observation_01.json`、`TOOL_CHAIN.md`
- `04_CONFIG/`：`parameters.json`、`L2_config_snapshot.yaml`
- `05_VALIDATION/`：`evaluator_result.json`、`metrics_summary.json`、
  `run_summary.md`、`PHASE_B0_VALIDATION.md`
- `06_VISUALS/`：`before.png`、`after.png`、`compare.png`、`metrics_panel.png`
- `attempts/attempt_01/`：与 `02_AGENT` / `03_TOOL_CHAIN` / `05_VALIDATION` /
  `06_VISUALS` 对应（本次无 RETRY，只存在 attempt_01）
- `00_INDEX/`：`run_manifest.json`、`L2_FROZEN.md`、`REPRODUCE.md`、
  `git_snapshot.txt`、`L1_L2_COMPARISON.md`
