# EVIDENCE_STRUCTURE — 全项目证据目录统一规范（L1/L2/L3/L4 通用）

适用于本项目的全部关卡（L1/L2/L3/L4）与全部未来 Run 的正式证据整理。
**本规范不改变任何算法、Prompt、参数、Agent Runner 实现**，只约定证据
如何组织、命名与保存。

## 目录层级：Level → Run → Attempt

```
outputs/submission_evidence/
    EVIDENCE_STRUCTURE.md            # 本文件
    SECURITY_POLICY（内嵌于下方第 7 条规则，不设单独文件）

    L1/
        README.md
        RUN_INDEX.csv
        REFERENCE_RUN.md
        runs/
            l1_YYYYMMDD_seedXXX_runNN/          # 一个唯一 Run ID
                00_INDEX/
                01_AGH/
                02_AGENT/
                03_TOOL_CHAIN/
                04_CONFIG/
                05_VALIDATION/
                06_VISUALS/
                attempts/                        # 仅当该 Run 真实发生过 RETRY/多次尝试
                    attempt_01/
                    attempt_02/
                    attempt_03/
    L2/  L3/  L4/   # 同样结构，未来按 Level 各建一套
```

## 子目录职责（每个 Run 内部固定为同一套）
- `00_INDEX/`：`run_manifest.json`、`REPRODUCE.md`、`L<level>_FROZEN.md`
  （冻结声明）、`git_snapshot.txt`、`SECURITY_FIELD_AUDIT.md`
- `01_AGH/`：`agh_run_log.json`、`diagnosis_input.json`、
  `AGH_EVIDENCE_README.md`、（可选）`screenshots/`（仅放真实截图，
  不放伪造图）
- `02_AGENT/`：`diagnosis.json`、`decision_NN.json`、
  `agent_assessment_NN.json`、`agent_final_assessment.json`
- `03_TOOL_CHAIN/`：`tool_call_NN.json`、`observation_NN.json`、
  `TOOL_CHAIN.md`
- `04_CONFIG/`：`parameters.json`（三层拆分：Agent 决策参数 / 派生实际数值 /
  工具内部默认值或 UNKNOWN）、`L<level>_config_snapshot.yaml`
- `05_VALIDATION/`：`evaluator_result.json`、`metrics_summary.json`
  （严格区分 `agent_observable_metrics` 与 `gt_evaluation_metrics`）、
  `run_summary.md`
- `06_VISUALS/`：`before.png`、`after.png`、`compare.png`、
  `compare_zoomed.png`（如需要）、`metrics_panel.png`
  —— 全部必须基于该 Run 真实输入点云与真实估计 transform 生成，
  不得修改数据夸大效果

## Run 状态（Run status）取值
| 状态 | 含义 |
|---|---|
| `PASS` | 独立 Evaluator 读 GT 后判定 success = true（达到 rot/trans 阈值） |
| `FAIL_VALIDATION` | 工具跑完、Agent 判 ACCEPT 或 ABORT，但 Evaluator 读 GT 后未达阈值 |
| `FAIL_TOOL` | 工具本身报错/无有效输出，Agent 无法得到可观测指标 |
| `ABORT_AGENT` | Agent 主动 ABORT（例如两次 RETRY 后仍不达标，判定放弃） |
| `PARTIAL` | 该 Level 允许多 case，部分 case PASS 部分 FAIL；在 `RUN_INDEX.csv` 里按 case 分行 |

## Attempt 状态（Attempt status）取值
| 状态 | 含义 |
|---|---|
| `ACCEPT` | 该 attempt 的可观测指标达标，Agent 决定停止 |
| `RETRY` | 该 attempt 未达标，Agent 决定换工具/参数再试一次（产生下一个 attempt_NN） |
| `ABORT` | 该 attempt 之后 Agent 判定不再尝试 |
| `TOOL_ERROR` | 该 attempt 的工具调用本身出错，Agent 需要换工具或放弃 |

## 强制规则
1. **唯一 run_id**：每次正式实验（L1/L2/L3/L4 任一）必须生成唯一
   `run_id`，格式建议 `l<level>_<YYYYMMDD>_seed<seed>_run<NN>`
   （`NN` 为同一 seed/日期下的重试序号，从 `01` 起）。
2. **永不覆盖旧 Run**：新的 Run 一律写入新的 `runs/<新run_id>/`；
   旧 Run 目录一旦生成即为只读证据，不得修改、删除或就地"美化"。
   唯一例外：修复本规范/审计发现的新问题（例如漏掉某个应保存文件）时，
   通过新增文件补充，不改动已冻结的核心指标文件。
3. **每次 Retry 生成新 Attempt**：`decision_NN` / `tool_call_NN` /
   `observation_NN` / `agent_assessment_NN` 的 `NN` 与
   `attempts/attempt_NN/` 一一对应；`agent_final_assessment.json`、
   `decision_final.json` 始终指向最后实际发生的那个 Attempt，不额外伪造。
4. **失败结果也必须保存**：`FAIL_VALIDATION` / `FAIL_TOOL` / `ABORT_AGENT`
   的 Run 同样要落盘完整证据（尤其 `observation_NN.json` 的失败指标与
   `agent_assessment_NN.json` 的 RETRY/ABORT 理由），不得因为"结果不好看"
   而删除或跳过保存。
5. **每个 Attempt 保存 5 类信息**：算法（`selected_method`）、参数
   （`parameter_policy` + 派生值）、指标（`observation_NN.json` 内可观测
   字段）、Agent 判断（`agent_assessment_NN.json` 的
   `decision`/`reason`）、图片（`06_VISUALS/`，若该 attempt 产生了
   有效 transform，则生成对应 before/after；`TOOL_ERROR` 类 attempt 可
   没有 after.png，但需在 `05_VALIDATION/` 里用文字说明原因，不留空目录）。
6. **GT 只进入最终 Evaluator**：任何 `decision` / `assessment` / 工具调用
   阶段都不得读取 `gt_transform.npy`；只有 `agent_evaluator.evaluate_agent_result`
   在 Agent 循环完全结束后才允许读 GT（见 `03_TOOL_CHAIN/` 里
   `tool_call_NN.json` 的 `gt_read` 字段，必须为 `false`）。
7. **敏感信息禁令**：任何 API Key、Token、Secret 不得出现在
   `outputs/submission_evidence/` 目录下的任何文件里（包括 README、
   JSON 字段、Git 记录）。`session_key` / `conversation_key` 类字段若经
   确认只是普通非敏感会话标识，应改名为 `session_id` 并保留具体值；
   若无法确认其性质，一律写 `REDACTED`，不保存具体值。每次新增/整理证据包都应
   生成一份 `SECURITY_FIELD_AUDIT.md` 记录本次检查结论。

## 与 Phase 的边界
本规范只管"证据怎么存"，不规定 Phase B/C 是否开始、是否新增关卡。
Phase B 是否启动由用户单独指示，与本文件的生成无关。
