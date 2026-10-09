# AGH / Agnes Evidence README — l1_seed_101 (submission copy)

This file is the organized-closeout version of
`outputs/agent_runs/l1_seed_101/agh_evidence/agh_evidence_README.md` (contents
unchanged, path references adjusted). The original is at
`outputs/agent_runs/l1_seed_101/agh_evidence/agh_evidence_README.md`; see
`raw/agh_evidence_README.md` in this package for the verbatim original.

---

## 1. 本轮 Agnes 模型信息
- 模型名：`agnes-3.0-flash`
- 模型版本标识：`2026-10-06`
- AGH 会话 key：`49486ac2-0a14-4ea2-b46e-7ec573d4d46e`
- 运行（run_id）：`l1_seed_101`
- 路由 / slot：`route=account-acct-72beee64-f559-4c9c-8096-306373f6c35c`, `slot=primary`
- 运行时间戳：AGH 侧 UTC `2026-10-06T17:31:24`（runner 执行）；Evaluator 落盘
  `2026-10-06 17:31:28`（本机时区 +08:00）

来源：`agh_run_log.json`、`agh_evidence_README.md`（原始）。

## 2. 哪些文件能够证明 Agnes 参与核心任务
- `agh_run_log.json`：`agent_model_name` / `agent_model_version` / 任务 prompt
  摘要、以及对 `decision_01.json` / `agent_assessment_01.json` 的显式引用
  （执行链路索引）。
- `decision_01.json`（+ 内容一致的 `decision_final.json`）：结构化决策
  （selected_method / parameter_policy / reasoning / confidence），是由 Agnes
  模型按约定格式产出的 JSON。
- `agent_assessment_01.json` / `agent_final_assessment.json`：基于可观测指标
  的 ACCEPT/RETRY/ABORT 判断。

**重要如实说明**：本运行中 Agnes 的"决策"实际由
`src/agent_runner.py::agnes_decide` 里的确定性启发式产出（模块 docstring 明确
写明"此实现为可审计的启发式"），并通过 AGH/Agnes 会话记录该模型名与版本
作为执行链路的归属标识；这一实现方式本身应当在评审说明中如实披露，不应被
解读为"已验证 LLM 本身自动完成了算法选择"。

## 3. 哪些文件能够证明实际工具调用
- `tool_call_01.json`：`tool_name`、`entrypoint`（
  `src.agent_tools.run_global_fpfh_ransac_icp`）、实际 `inputs`（含匿名化的
  source/target 标识、base_scale、parameter_policy）、`gt_read: false`。
- `observation_01.json`：该工具真实返回的
  `transform` / `fitness` / `rmse` / `ransac_fitness` / `ransac_rmse` /
  `elapsed_s` / `ransac_max_correspondence_distance` /
  `icp_max_correspondence_distance`，与 `tool_call_01.json` 中声明的
  `returned_metrics_keys` 逐一对应。
- `src/agent_tools.py` 中 `run_global_fpfh_ransac_icp` 的源码：可核对
  observation 中每一个数值的计算路径（例如
  `ransac_max_correspondence_distance = max(1e-3, base_scale *
  global_corr_scale)`）。

## 4. 哪些文件能够证明 Agent 完成结果判断
- `agent_assessment_01.json`：单步评估（`decision: ACCEPT`，理由为
  `fitness >= 0.8` 阈值）。
- `agent_final_assessment.json`：最终评估（内容一致，因为只有一次尝试，
  无 RETRY/ABORT 升级）。
- `decision_final.json`：与 `decision_01.json` 内容一致，表明这是最终的
  决策（未被后续 RETRY 改写）。

## 5. 哪些文件能够证明 Evaluator 在 Agent 停止以后才读 GT
- `tool_call_01.json` 的 `gt_read: false`：工具调用阶段明确不读 GT。
- `evaluator_result.json` 的 `gt_evaluator: true` + `gt_path` + 独立
  `timestamp`（`2026-10-06 17:31:28`）：该时间戳晚于 runner 执行时间戳
  （`2026-10-06T17:31:24` UTC），与 `src/agent_runner.py` 中的调用顺序一致
  （`evaluate_agent_result` 在 Agent 的 ACCEPT/ABORT 判定完成、Agent 循环
  结束后才被调用）。
- `src/agent_evaluator.py` 的 docstring 与代码：明确"仅在 Agent 已
  ACCEPT/ABORT 之后才允许读取 GT"，GT 文件的延迟导入保证了这一点。

## 6. 官方 AGH raw trace 状态
**NOT_AVAILABLE。**

原因：当前 AGH 运行环境没有开放"将某次 Agnes 会话导出为可提交文件"的能力
（无官方 session/execution trace 导出 API，AGH 自身用户数据目录中也没有本次
运行对应的落盘 trace，详见原始 README 中的检查依据 1/2/3 条）。

因此本包中所有 JSON / Markdown 文件应被描述为：

> **本次真实运行过程中落盘的结构化执行证据**（由 Agent Runner 本身写出的、
> 可逐字节核对的中间产物与结果记录）

而**不是**"AGH 官方原始日志 / 官方 execution record"。两者不可混用措辞。

若后续环境支持官方导出，应当把该导出的原始文件单独存放（不要与这里
Runner 自己生成的文件混在同一层级），并在此 README 中追加文件名与哈希，
但在此之前本包维持"最接近原始证据"的定位。

## 完整文件清单（本 closeout 包）
- `raw/` — 原始运行文件的逐字节镜像（`diagnosis.json` … `run_summary.md`，
  含 `agh_evidence/` 子目录）
- `figures/` — 基于真实输入点云与真实估计 transform 生成的
  `before.png` / `after.png` / `compare.png` / `compare_zoomed.png` /
  `metrics_panel.png`，以及用于生成它们的 `source.ply` / `target.ply`
  副本（保证可复核）
- `run_manifest.json` / `parameters.json` / `metrics_summary.json` —
  结构化汇总（本 closeout 新增）
- `run_summary.md` / `TOOL_CHAIN.md` / 本文件 — 人类可读叙述与工具链追踪
