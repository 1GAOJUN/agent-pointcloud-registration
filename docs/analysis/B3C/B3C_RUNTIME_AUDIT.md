# Phase B3C — Registration Runtime Audit

## 审计问题

为什么 B3A 与 B3B 的 registration runtime 相差很大？

结论必须分三层：已证实的计时事实、代码可确定的统计口径、现有 Evidence 无法唯一确定的内部原因。

## 1. 计时事实

| 口径 | B3A | B3B | 比值 B3A/B3B |
|---|---:|---:|---:|
| `elapsed_s` | 287.8276558 s | 0.5821463 s | 494.424951× |
| `tool_elapsed_s` / `wall_time_s` | 287.8436 s | 0.6020 s | 478.145515× |
| outer − inner | 0.0159442 s | 0.0198537 s | 不适用 |

来源：各 Run 的 `02_AGENT/observation_01.json` 与 `03_TOOL_CHAIN/tool_call_01.json`。

外层与内层只相差约 16–20 ms，因此可以确认：

- 大额差异发生在 `run_global_fpfh_ransac_icp()` 调用内部；
- 不是 Agnes 推理等待造成；
- 不是 Probe 计时造成；
- 不是 GT Evaluator 造成；
- 不是 closeout、visuals 或 Evidence 写盘造成。

## 2. 字段来源与统计口径

### `elapsed_s`

`src/agent_tools.py` 的 `run_global_fpfh_ransac_icp()` 在读取点云之前调用 `time.perf_counter()`，在 ICP 返回之后停止计时。它包含：

1. 读取 source/target PLY；
2. 两云 statistical outlier removal；
3. normal estimation；
4. 选择最多 500 个 key indices；
5. FPFH computation；
6. feature-matching RANSAC；
7. point-to-plane ICP。

因此 `elapsed_s` 是复合 registration tool runtime，不是纯 RANSAC 时间，也不是完整 Agent Run 时间。

### `tool_elapsed_s` 与 `wall_time_s`

`tests/_b3a_run_tool.py` 与 `tests/_b3b_run_tool.py` 在调用整个工具函数之前和之后用 `time.perf_counter()` 包裹，保存为 `tool_elapsed_s`，并复制到 tool-call Evidence 的 `wall_time_s`。两者口径相同，只比 `elapsed_s` 多函数调用和结果整理等微小开销。

### 环境与代码路径

- 两条 Run 均记录 Python 3.11.16、Open3D 0.20.0。
- B3A freeze manifest 对 `src/agent_tools.py` 记录 SHA-256 `8B681CC2...3048`；B3B core state 记录 frozen hash verification 通过。
- 两条 Run 都调用 `src.agent_tools.run_global_fpfh_ransac_icp`。
- Open3D 0.20.0 本地 API 显示，代码未显式传入 criteria 时使用 `RANSACConvergenceCriteria(max_iteration=100000, confidence=0.999)`；代码也未显式传入 checkers。

所以不能用“算法不同”“计时边界不同”或“一个包含 Evaluator”解释差异。

## 3. 已证实的输入与参数差异

| 因素 | B3A | B3B | 事实 |
|---|---:|---:|---|
| source/target points | 30000 / 30282 | 30000 / 30000 | 原始规模接近 |
| density ratio | 1.7811 | 1.0 | 几何/采样分布不同 |
| base_scale | 0.004997336 | 0.033885067 | B3B 约 6.781× |
| global_corr_scale | 5.0 | 4.0 | policy 不同 |
| actual RANSAC distance | 0.024986678 | 0.135540268 | B3B 约 5.425× |
| icp_max_corr_scale | 2.0 | 1.0 | policy 不同 |
| actual ICP distance | 0.009994671 | 0.033885067 | B3B 约 3.390× |
| FPFH radius | `max(base_scale, 0.2)=0.2` | `max(base_scale, 0.2)=0.2` | 相同代码结果 |
| maximum FPFH key indices | 500 | 500 | 上限相同；SOR 后实际可用点数未记录 |

这证明 RANSAC/ICP 收到的点云几何与对应距离阈值不同。特别是 B3A 的实际 RANSAC/ICP 距离更严格，而其 target 采样密度与尺度也更不一致。

## 4. 能否给出唯一原因？

**不能。唯一内部瓶颈字段为 `UNKNOWN`。**

现有工具只记录一个总 `elapsed_s`，没有记录：

- SOR 后 source/target 点数；
- normal estimation、FPFH、RANSAC、ICP 的分阶段耗时；
- mutual filtering 后 correspondence 数；
- RANSAC 实际迭代数、停止原因或随机状态；
- ICP 实际迭代数；
- 同一 case 的重复运行分布。

因此，以下更精确表述不能从 Frozen Evidence 证明：

- “287 秒全部花在 RANSAC”；
- “差异由点数造成”（原始点数实际接近）；
- “差异只由 parameter policy 造成”；
- “B3B 场景在算法意义上必然更快”；
- “`np.random.seed(42)` 保证 Open3D C++ RANSAC 完全确定”。

## 5. 最强可支持解释

可以支持的最强结论是：

> 两条 Run 使用同一复合全局配准工具和相同计时边界。B3A 的约 287.83 s 与 B3B 的约 0.582 s 差异真实发生在该工具内部。两条输入的几何/采样分布不同，并且由不同 base scale 与 Agnes multiplier 导出的实际 RANSAC/ICP 对应距离显著不同；这些差异会改变特征匹配、RANSAC 收敛和 ICP 工作量。但 Frozen Evidence 没有分阶段计时或迭代统计，无法把约 494× 差异唯一归因于某一阶段或某一参数。

这是审计结论，不是性能因果证明。

## 6. E 阶段所需 runtime instrumentation

后续应在新的、非 Frozen Run 中预先加入：

- `load_s`、`sor_s`、`normals_s`、`fpfh_s`、`ransac_s`、`icp_s`；
- SOR 前后点数、key count、mutual correspondence count；
- RANSAC criteria、实际迭代数/停止原因；
- ICP iteration count；
- Python/Open3D/CPU/thread 数与随机状态；
- 每个 case 至少多次独立重复，并报告 median、IQR、min/max；
- 固定 policy 与 adaptive policy 的同 case 对照。

这些新增 instrumentation 只能用于未来 Run，不能回写或重跑当前 B3A/B3B Frozen Evidence。
