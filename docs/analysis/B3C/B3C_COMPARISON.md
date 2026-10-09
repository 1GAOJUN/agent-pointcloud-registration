# Phase B3C — Frozen Run 对比

## 范围与方法

本报告只比较以下两个已经冻结的正式 Run，不重新运行 Agnes、Probe、Registration 或 Evaluator：

- B3A：`b3_l1_20261007_seed101_blind02`
- B3B：`b3_l2_20261007_seed202_blind01`

所有数值均来自 `outputs/submission_evidence/B3/` 内的现存 Evidence。缺失或未实现字段按原值记录，不推测。Ground Truth 仅用于比较已由 Independent Evaluator 在 Agent 停止后生成的结果。

## 结论摘要

- 两个 Run 的 Basic Diagnosis 明显不同；B3B 整体尺度更大、两云密度几乎一致，B3A 的 target 相对其 source 更稀疏且包围盒扩张更明显。
- 两次 Agnes initial decision 都认为信息不足，先请求 `PCA_ORIENTATION`；两次均由 Real Agnes 产生。
- 两个 Run 都执行 2 个 Probe，顺序均为 `PCA_ORIENTATION → CHEAP_LOCAL_ICP`，但 Observation 明显不同。
- 两个 Run 最终都选择 `GLOBAL_FPFH_RANSAC_ICP`，所以当前证据不支持“跨场景切换 registration method”的强声明。
- Agnes 选择了不同 parameter policy：B3A 为 `5.0 / 2.0`，B3B 为 `4.0 / 1.0`；这支持有限的、Observation-conditioned 参数适应证据。
- 两个 Run 都只有 1 个 Attempt，最终均由 Real Agnes `ACCEPT`，随后 GT Evaluator 判定成功。
- registration 内层计时相差约 `494.425×`。Evidence 可定位差异发生于同一复合工具内部，但不能唯一定位到 SOR、FPFH、RANSAC 或 ICP 中的某一阶段；详见 `B3C_RUNTIME_AUDIT.md`。
- 当前“场景自适应”证据等级：**PRELIMINARY**。

## 1. Basic Diagnosis

来源：各 Run 的 `02_AGENT/diagnosis.json`。

| 字段 | B3A | B3B | 对比 |
|---|---:|---:|---|
| source_point_count | 30000 | 30000 | 相同 |
| target_point_count | 30282 | 30000 | B3A 多 282 点 |
| source_bbox_diagonal | 0.249866780 | 1.694253347 | B3B 更大 |
| target_bbox_diagonal | 0.742714907 | 1.787429645 | B3B 更大 |
| source_median_spacing | 0.001568212 | 0.010847342 | B3B 更大 |
| target_median_spacing | 0.002793177 | 0.010847342 | B3B 更大 |
| density_ratio | 1.781121788 | 1.000000000 | B3A target 相对更稀疏；B3B 基本一致 |
| centroid_distance | 0.393077276 | 0.559145402 | 绝对值 B3B 更大 |
| base_scale | 0.004997336 | 0.033885067 | B3B 为 B3A 的约 6.781× |
| initial_transform_available | true | true | 相同 |
| overlap/noise/outlier/rotation estimate | `NOT_IMPLEMENTED` | `NOT_IMPLEMENTED` | 均未实现，不推测 |

## 2. Agnes initial decision

来源：`01_AGH/agnnes_raw_decision_01.json` 与 `02_AGENT/agnnes_decision_01_parsed.json`。

| 项目 | B3A | B3B |
|---|---|---|
| implementation | `agnnes_real` | `agnnes_real` |
| information_sufficient | false | false |
| requested_probe | `PCA_ORIENTATION` | `PCA_ORIENTATION` |
| selected_method | null | null |
| parameter_policy | null | 两个倍率均为 null |
| confidence | 0.45 | 0.62 |
| 主要判断 | 尺度/密度有差异、质心偏移显著、旋转未知 | 两云尺度/密度匹配、质心偏移非零、旋转未知 |

两次初始决策都没有提前选择方法，而是把旋转不确定性作为首要信息缺口并请求 PCA。B3A 与 B3B 的文字理由随 Diagnosis 改变，但 Probe 类型相同。

## 3–5. Probe 数量、顺序与 Observation

来源：`02_AGENT/probe_observation_01.json`、`probe_observation_02.json`，并由各 Run manifest/summary 交叉核对。

两个 Run 均执行 2 个 Probe，顺序相同：

1. `PCA_ORIENTATION`
2. `CHEAP_LOCAL_ICP`

### PCA_ORIENTATION

| 字段 | B3A | B3B |
|---|---:|---:|
| rotation_estimate_deg | 16.09 | null |
| orientation_confidence | MEDIUM | LOW |
| ambiguity_detected | false | true |
| ambiguity_reason | partial-axis degeneracy | near-line degeneracy；横向轴不确定 |
| source_anisotropy | 3.4494 | 2.8698 |
| target_anisotropy | 2.9739 | 2.8698 |
| runtime_s | 0.0421 | 0.0524 |

B3A 的 PCA 给出可用但置信度受限的 16.09° 主轴框架相对旋转估计。B3B 因退化明确返回 null，并注明不得用该字段做算法选择。该角度不是 GT rotation error，也不是逐点配准误差。

### CHEAP_LOCAL_ICP

| 字段 | B3A | B3B |
|---|---:|---:|
| initial_fitness | 0.0 | 0.136566667 |
| probe_fitness | 0.0 | 0.164966667 |
| fitness_improvement | 0.0 | 0.0284 |
| initial_rmse | 0.0 | 0.038933667 |
| probe_rmse | 0.0 | 0.038193119 |
| transform_delta_magnitude | 0.0 | 0.222239556 |
| iterations | 5 | 5 |
| max_correspondence_distance | 0.009994671 | 0.067770134 |
| runtime_s | 0.0662 | 0.4702 |

B3A 的 fitness 与 transform delta 均为 0，但 `correspondence_count` 未记录；B3B 有非零 fitness 和小幅改善，但仍被 Agnes 判断为局部初始化不足。两者都为 Probe Observation，不是正式 Registration 结果。

## 6–7. selected_method、parameter policy 与实际参数

来源：`02_AGENT/decision_final.json`、`04_CONFIG/parameters.json`、`02_AGENT/observation_01.json` 和 `03_TOOL_CHAIN/tool_call_01.json`。

| 项目 | B3A | B3B |
|---|---:|---:|
| selected_method | `GLOBAL_FPFH_RANSAC_ICP` | `GLOBAL_FPFH_RANSAC_ICP` |
| decision confidence | 0.72 | 0.68 |
| global_corr_scale | 5.0 | 4.0 |
| icp_max_corr_scale | 2.0 | 1.0 |
| base_scale | 0.004997336 | 0.033885067 |
| actual RANSAC max correspondence distance | 0.024986678 | 0.135540268 |
| actual ICP max correspondence distance | 0.009994671 | 0.033885067 |

B3A 的 `04_CONFIG/parameters.json` 只保存了舍入后的 `ransac_max_corr=0.024987`，并将通用 `max_correspondence_distance` 留为 null；其实际 ICP 阈值可从 `observation_01.json` 追踪到 `0.009994671187040016`。B3B 的配置 schema 直接保存了两种实际阈值。两者实际阈值都符合 `base_scale × Agnes multiplier`。

## 8. Attempts 与 final assessment

来源：attempt summary、`02_AGENT/agent_final_assessment.json` 和 run manifest/metrics summary。

| 项目 | B3A | B3B |
|---|---:|---:|
| attempt_count | 1 | 1 |
| retry | 否 | 否 |
| final decision | ACCEPT | ACCEPT |
| assessment implementation | `agnnes_real` | `agnnes_real` |
| assessment confidence | 0.99 | 0.97 |
| guardrail overwrite | 无证据显示发生 | 明确未发生 |
| failed attempts | 0 | 0 |

两个 Run 都是一次通过，因此现有正式 Frozen Evidence 没有实际展示 RETRY 后的跨 Attempt 自适应。

## 9. fitness、RMSE 与 runtime

来源：`02_AGENT/observation_01.json`、`metrics.json` 和 `03_TOOL_CHAIN/tool_call_01.json`。

| 字段 | B3A | B3B |
|---|---:|---:|
| fitness | 1.0 | 1.0 |
| RMSE | 0.001423342437 | 1.631289848e-16 |
| RANSAC fitness | 1.0 | 1.0 |
| RANSAC RMSE | 0.002949123617 | 1.965810051e-16 |
| inner elapsed_s | 287.8276558 s | 0.5821463 s |
| outer tool_elapsed_s / wall_time_s | 287.8436 s | 0.6020 s |

`elapsed_s` 是 registration 工具内部复合计时；`tool_elapsed_s`/`wall_time_s` 是调用该工具的外层墙钟计时，不是完整 Agent Run 时间。不能把它们解释为 Agnes 推理、Probe、Evaluator 或整个 Run 的耗时。

## 10. Independent GT evaluation

来源：B3A `02_AGENT/evaluator_result.json`；B3B `05_VALIDATION/evaluator_result.json`。

| 字段 | B3A | B3B |
|---|---:|---:|
| rotation error | 0.948341465° | 0.0° |
| translation error | 0.000836948 | 0.0 |
| success | true | true |
| thresholds | rotation < 5°；translation < 0.05 | rotation < 5°；translation < 0.05 |

GT 结果只说明两条 Frozen Run 在各自 Independent Evaluator 下均成功，不能反向用于解释或改写此前的 Agent 决策。

## Evidence source index

每条 Run 的主要来源均为其自身目录下：

- `02_AGENT/diagnosis.json`
- `01_AGH/agnnes_raw_decision_01.json`
- `02_AGENT/agnnes_decision_01_parsed.json`
- `02_AGENT/probe_observation_01.json`
- `02_AGENT/probe_observation_02.json`
- `02_AGENT/decision_final.json`
- `04_CONFIG/parameters.json`
- `02_AGENT/observation_01.json`
- `02_AGENT/metrics.json`
- `02_AGENT/agent_final_assessment.json`
- `03_TOOL_CHAIN/tool_call_01.json`
- `attempts/attempt_01/`
- 对应的 Independent Evaluator result 与 run manifest/metrics summary
