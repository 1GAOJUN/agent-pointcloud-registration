# AGH / Agnes 证据归档 — L1 seed_101 闭环运行

## 官方原始执行记录导出：NOT_AVAILABLE

**结论**：当前 AGH 环境**未提供可导出到仓库的官方会话日志 / execution record /
trace / tool-call history**。因此本目录保存的是“当前可保留的最接近原始证据”，
不是 AGH 官方原始日志，也不是人为重写的伪日志。

**检查依据（可复核）**：
1. 搜索 AGH 工作区（`D:\STUDY\darker\agnes-harness`）内与本次运行相关的
   trace/session/log/record 目录：未发现。工作区内仅有的 `*.jsonl` 全部是
   AGH 代码仓库自带的**测试 fixtures**（`packages/base/fixtures/replay/*`、
   `packages/ai/fixtures/decode/*` 等），与本次 L1 运行无关。
2. 搜索 AGH 运行时用户数据目录（`LOCALAPPDATA` 下 Sapiens/AGH/agnes-harness、
   以及 `%USERPROFILE%\.ags`/`.aghs`/`.agent-pointcloud`）：均不存在。
3. AGH 在本次运行中**没有向文件系统的任何位置写出**一条可追溯的官方会话
   trace。它只在本进程内维护当前会话的 transcript。

**当前会话（本 L1 运行所属会话）的事实信息**：
- 会话 key（AGH 运行时会话标识）：`49486ac2-0a14-4ea2-b46e-7ec573d4d46e`
- 运行（run_id）：`l1_seed_101`
- 实际参与决策的 Agnes 模型名：`agnes-3.0-flash`
- 模型版本标识（记录值）：`2026-10-06`
- 运行时间戳（AGH 侧 UTC）：`2026-10-06T17:31:24`（runner 执行）；
  评测器落盘 `2026-10-06 17:31:28`（本机时区 +08:00）
- 路由 / slot（AGH 运行时上下文）：`route=account-acct-72beee64-f559-4c9c-8096-306373f6c35c`, `slot=primary`

**为什么无法导出官方原始记录**：
- AGH 的官方会话/执行记录保存在 AGH 进程内存与 AGH 自身的服务端存储中，
  本运行环境下**没有开放**“把某次 Agnes 会话导出为文件”的能力或路径，
  且用户数据目录中确认不存在该存储。
- 因此无法在本仓库中放置“AGH 官方原始 execution record / tool-call history”。

## 本目录保留的“最接近原始证据”（非伪造）

以下文件都是**本次 L1 运行实际生成、逐字节拷存**的产物（非事后重写）：

| 文件 | 证明的事实 |
|---|---|
| agh_run_log.json | 实际调用的 Agnes 模型名/版本、运行时间、任务 prompt 摘要、各 decision/observation/assessment 文件引用（执行链路索引） |
| diagnosis_input.json | Agent 收到的诊断输入（GT-free 结构化观测） |
| decision_01.json | Agnes 输出的第一次结构化 decision（selected_method / parameter_policy / reasoning / confidence） |
| tool_call_01.json | 实际 tool call（tool_name、entrypoint、inputs、gt_read=false） |
| observation_01.json | tool 返回的可观测指标（fitness/rmse/elapsed…） |
| agent_assessment_01.json / agent_final_assessment.json | Agnes 基于可观测指标的 ACCEPT/RETRY/ABORT 判断（ACCEPT） |
| evaluator_result.json | 独立 Evaluator 在 Agent 停止后读取 GT 的结果（gt_evaluator=true, success=true） |
| run_summary.md | 运行总结（人类可读） |

## GT 隔离与“Evaluator 晚于 Agent 停止”的顺序证明

- 各 `tool_call_*.json` 均含 `gt_read: false`，且 Agent 的 decision/assessment
  只接收 diagnosis 与可观测指标。
- `evaluator_result.json` 含 `gt_evaluator: true` 与独立 `timestamp`（17:31:28），
  晚于 Agent 最终评估（17:31:24），且 `gt_path` 指向真实 GT 文件；
  即 **GT 只在 Agent 已 ACCEPT 后由独立 Evaluator 读取**，与 runner 执行顺序一致。

## 若要补齐“官方 AGH 证据”（下一步可做，非本轮）
- 在具备 AGH 官方导出能力的环境中，把本次 run 对应的 Agnes 会话
  execution record / tool-call trace 导出为文件，放入本目录，并在此清单追加
  其文件名与哈希；在此之前，本目录保持“最接近原始证据”的定位。
