# Phase B3C — 场景自适应 Claim Boundary

## 判定

当前“场景自适应”证据等级为：**PRELIMINARY**。

这不是 `NOT_SUPPORTED`，因为两个正式 Frozen Run 确实展示了：

- 不同的 Basic Diagnosis；
- 不同的 PCA 与 Cheap Local ICP Observation；
- Real Agnes 对 Observation 的不同解释；
- 不同的 parameter policy（B3A `5.0/2.0`，B3B `4.0/1.0`）；
- 两组参数均被实际工具采用并成功完成独立 GT 验证。

但也不能判定为 `SUPPORTED`，因为样本和行为覆盖仍不足。

## 现在可以说的结论

1. **两个正式盲测 Run 均由 Real Agnes 经 AGH 产生决策。** Raw/parsed decision 与 assessment 证据均存在，`_implementation=agnnes_real`。
2. **系统能根据不同 Observation 调整参数倍率。** 两条 Run 的 parameter policy 不同，且实际距离阈值由各自 `base_scale × multiplier` 导出。
3. **系统能处理 Probe 不确定性。** B3A PCA 返回 MEDIUM/16.09°；B3B PCA 因退化返回 LOW/null。B3B 没有伪造角度，而是继续请求 Cheap Local ICP。
4. **两个 Run 都在一次 Attempt 后达到 ACCEPT，并通过独立 GT 验证。** 这是两条具体 case 的成功证据。
5. **Agent 决策链不是固定 Python heuristic 的冒充。** Frozen Evidence 将 historical heuristic 与 Real Agnes 分开；B3A/B3B 决策/评估均标记为 Real Agnes。

建议对外表述：

> 在两个正式 Frozen blind Run 中，Real Agnes 根据不同的诊断与 Probe Observation 形成不同推理并选择不同参数策略；两次均调用全局配准工具并通过独立 GT 验证。这构成场景感知参数适应的初步证据。

## 现在不能说的结论

1. **不能说已经证明跨场景自动选择不同 registration method。** 两条 Run 最终都选择 `GLOBAL_FPFH_RANSAC_ICP`。
2. **不能说已证明 RETRY/ABORT 自适应闭环。** 两条 Run 都是单 Attempt、无 RETRY、无 ABORT。
3. **不能说已证明对 L1–L4 或真实世界场景的普遍泛化。** 当前比较只有两个 Frozen case。
4. **不能说不同 parameter policy 导致了性能差异。** 输入几何、尺度和阈值同时变化，没有控制变量或消融。
5. **不能说 B3B 天然比 B3A 快约 494×。** 这是单次复合工具计时，不是重复实验统计；分阶段耗时与 RANSAC 实际迭代数未记录。
6. **不能用 GT 结果反向证明 Agent 决策时知道正确答案。** GT 只在 Agent 停止后由 Evaluator 读取。
7. **不能把 PCA 16.09°解释为 GT rotation error。** 该字段是主轴框架相对旋转估计，且 Evidence 明确给出限制。

## E 阶段需要补齐的证据

要将结论升级为 `SUPPORTED`，至少需要：

- 覆盖更多冻结场景与 seed，包括能合理触发 `LOCAL_ICP`、不同全局策略或 `ABORT` 的 case；
- 每类场景进行重复独立 Run，报告成功率、策略分布和置信区间，而不是单次结果；
- 展示真实 RETRY：保留失败 Attempt，并验证下一轮决策确实使用前一 Attempt 的 Observation；
- 做受控消融：Real Agnes adaptive policy 对比固定 policy、historical heuristic 与无 Probe 路径；
- 固定或记录随机状态，记录 RANSAC 实际迭代数/停止原因；
- 增加 SOR、normal、FPFH、RANSAC、ICP 分阶段耗时与阶段输入规模；
- 对 method choice、parameter choice 与结果之间的因果关系做控制变量实验；
- 预先定义成功阈值、样本集合和统计方案，避免看到 GT 后调整口径。

## 证据边界表

| Claim | 当前等级 | 依据/缺口 |
|---|---|---|
| Real Agnes 参与正式决策 | SUPPORTED（限 B3A/B3B） | 两条 Frozen Run 均有 raw/parsed Evidence |
| Observation-conditioned parameter adaptation | PRELIMINARY | 两 case 参数不同，但无控制实验 |
| Observation-conditioned method switching | NOT_SUPPORTED | 两 case method 相同 |
| Active Probe 顺序由 Agnes 决定 | SUPPORTED（限两条 Run） | raw decisions 与 `_probe_request.requested_by=agnnes_real` |
| RETRY/ABORT 闭环有效 | NOT_SUPPORTED | 无实际 RETRY/ABORT case |
| 跨场景普遍泛化 | NOT_SUPPORTED | 两 case 样本不足 |
| 整体“场景自适应” | **PRELIMINARY** | 有参数与推理差异，但行为覆盖和统计不足 |
