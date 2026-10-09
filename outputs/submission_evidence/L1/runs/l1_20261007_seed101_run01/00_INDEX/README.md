# L1 Evidence Package — README

## 本目录是什么
`outputs/submission_evidence/L1/` 是 L1 关卡（小角度旋转 + 干净数据）的
**证据整理目录**，采用全项目统一的 `Level → Run → Attempt` 结构（见
`outputs/submission_evidence/EVIDENCE_STRUCTURE.md`）。本目录只含对原始运行
证据的**复制与索引**，不含任何重新运行产生的新结果；所有数字均取自
`outputs/agent_runs/l1_seed_101/`（原始，保持不动）。

## 本次 Run
- Run 目录名：`runs/l1_20261007_seed101_run01/`
- 对应原始 run_id：`l1_seed_101`
- 状态：PASS（见下方"冻结事实"）

## Agnes 模型
- `agnes-3.0-flash`，版本标识 `2026-10-06`
- AGH 会话标识（非敏感）：`agh_session_id`（原字段名 `agh_session_key`，
  本轮已按安全检查规则改名，见 `SECURITY_FIELD_AUDIT.md`）

## Agent 选择的方法
`GLOBAL_FPFH_RANSAC_ICP`

## 关键参数（Agent 策略层）
- `global_corr_scale = 5.0`
- `icp_max_corr_scale = 2.0`
- `base_scale = 0.033892031543267295`（诊断阶段算出）
- 派生实际阈值：RANSAC max_corr = 0.1694601577163365，
  ICP max_corr = 0.06778406308653459（与 `observation_01.json` 实际返回值一致）

## Agent 最终判断
`ACCEPT`（可观测 fitness = 1.0 ≥ 阈值 0.8）

## GT 最终验证结果
- rotation_error_deg = 0.0
- translation_error = 1.3877787807814457e-17
- success = **PASS**（阈值 rot < 5.0°，trans < 0.05）
- 该结果由独立 Evaluator 在 Agent 停止后才读取 GT 得到；工具调用阶段
  `gt_read = false`。

## 六个子目录（`runs/l1_20261007_seed101_run01/` 下）分别证明什么
| 目录 | 证明内容 |
|---|---|
| `00_INDEX/` | 索引、冻结声明（`L1_FROZEN.md`）、可复现信息（`REPRODUCE.md`）、`run_manifest.json`、`git_snapshot.txt`、本 README 所引用的安全审计文件位置 |
| `01_AGH/` | Agnes 模型信息、任务 prompt 摘要、执行链路索引（`agh_run_log.json`）、AGH 官方 raw trace 状态（NOT_AVAILABLE）、会话输入诊断（`diagnosis_input.json`） |
| `02_AGENT/` | Agent 决策本身：`diagnosis.json`、`decision_01.json`、`agent_assessment_01.json`、`agent_final_assessment.json` |
| `03_TOOL_CHAIN/` | 实际工具调用：`tool_call_01.json`（含 `gt_read=false`）、`observation_01.json`（真实返回指标与 transform）、`TOOL_CHAIN.md`（逐步说明） |
| `04_CONFIG/` | 参数三层拆分（`parameters.json`）与 L1 case 配置快照（`L1_config_snapshot.yaml`） |
| `05_VALIDATION/` | 独立 Evaluator 结果（`evaluator_result.json`）、指标汇总（`metrics_summary.json`）、运行总结（`run_summary.md`） |
| `06_VISUALS/` | `before.png` / `after.png` / `compare.png` / `compare_zoomed.png` / `metrics_panel.png`（基于真实点云 + 真实估计 transform 生成，未修改数据） |

## 原始运行证据路径（保持不变）
`outputs/agent_runs/l1_seed_101/`

## Attempt 结构统一规则（未来所有 Level 通用）
本 Run 是**首次成功**，没有发生 RETRY，因此 `runs/l1_20261007_seed101_run01/`
下**只有这一份完整证据，没有、也不会伪造** `attempt_02` 及以后的失败记录。

如果未来的某个 Run 出现多次算法执行 / RETRY，规则如下：
- 在该 Run 目录下新增 `attempts/`，按 `attempt_01/`、`attempt_02/`、
  `attempt_03/` … 保存每一次**真实发生过的**尝试，每份包含：
  decision / parameters / tool call / observation / assessment / metrics /
  visuals（与 `02_AGENT`/`03_TOOL_CHAIN`/`05_VALIDATION`/`06_VISUALS` 对应）。
- **失败 Attempt 不得删除**，必须保留以供回归分析。
- 本轮不新增空的 `attempts/` 占位目录（避免"为了目录好看"而制造结构，
  与 EVIDENCE_STRUCTURE.md 第 4 条一致：没有发生的事就不伪造痕迹）。

## 安全检查
本包已通过安全字段审计（`00_INDEX/SECURITY_FIELD_AUDIT.md`，即
`SECURITY_FIELD_AUDIT.md`，本轮新增）：确认没有任何 API Key / Token /
Secret 进入证据目录或 Git；`session_key` 类字段已按规则改名为
`session_id`（非敏感，保留具体值）。
