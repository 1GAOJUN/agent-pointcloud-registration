# 03_OBSERVATION_GAP — 当前 Agent 可观察信息完整清单与缺口分析

**Phase B1 — 只读审计。**

---

## 完整 Observation 字段清单

来源：`src/agent_diagnose.py` `diagnose()` 返回 dict，
L1/L2 `diagnosis.json` 实际内容核对。

| 字段 | 计算方法 | Agent 可见 | 能反映什么 | 不能反映什么 | 可靠性 |
|---|---|---|---|---|---|
| `source_point_count` | `len(sp)`（读取 PLY 后） | 是 | 点数规模，可判断计算成本预期 | 点云质量、几何形状 | 高（精确值） |
| `target_point_count` | `len(tp)` | 是 | 同上 | 同上 | 高 |
| `source_bbox_diagonal` | `np.linalg.norm(pts.max - pts.min)`，全量点集 | 是 | 全局物体尺度（物体"有多大"） | 局部密度、噪声 | 高（对全量点集精确） |
| `target_bbox_diagonal` | 同上 | 是 | 同上 | 同上 | 高 |
| `source_median_spacing` | numpy 向量化 KNN（K=8，采样上限5000，seed=101）取中位最近邻距离 | 是 | 局部采样尺度（"点与点多密"） | 点云形状、整体大小 | 中（依赖采样种子，对极稀疏或极密区域有偏差） |
| `target_median_spacing` | 同上 | 是 | 同上 | 同上 | 中 |
| `density_ratio` | `target_median_spacing / source_median_spacing` | 是 | 两云相对稀疏程度（>1 target 更稀疏） | 局部密度差异（如部分区域稀疏、部分密集） | 中（中位数是全局统计，对局部变化不敏感） |
| `centroid_distance` | `np.linalg.norm(tp.mean - sp.mean)` | 是 | 质心平移量（全局平移尺度） | 旋转量、局部平移 | 高（质心对全量点精确） |
| `initial_transform_available` | **硬编码 `True`**（`agent_diagnose.py` 第 82 行） | 是 | 无信息量（始终 True） | 无 | **无效（恒真，无区分度）** |
| `sample_size` | `min(len(sp), 5000)` | 是 | 中位间距计算时实际用了多少点 | 无 | 高（记录值） |
| `sampling_seed` | 固定常量 101 | 是 | 可复现性 | 无 | 高（固定值） |
| `overlap_ratio` | **NOT_IMPLEMENTED** | 是（值为字符串 `"NOT_IMPLEMENTED"`） | 无 | 源/目标点云重叠程度 | **缺失（L3/L4 关键）** |
| `noise_level` | **NOT_IMPLEMENTED** | 是（值为字符串） | 无 | 点云噪声幅度 | **缺失（L3 关键）** |
| `outlier_level` | **NOT_IMPLEMENTED** | 是（值为字符串） | 无 | 离群点比例 | **缺失（L3 关键）** |
| `rotation_magnitude_estimate` | **NOT_IMPLEMENTED** | 是（值为字符串） | 无 | 源/目标间粗旋转量 | **缺失（核心缺口，无法区分 Case A vs Case B）** |
| `base_scale` | `max(src_median_spacing, bbox_diagonal/50)`（`agent_diagnose.py` 第 92-94 行） | 是（派生值） | 诊断尺度基准，用于参数倍率 | 本身不是"难度"指标 | 高（确定可计算） |

> 注：`offset_proxy = centroid_distance / base_scale` **不在** `diagnosis.json` 里，
> 而是在 `agnnes_decide` 函数内部临时计算，Agent 可见性存疑（若 Agnes 是 LLM，
> 它只能看到 `diagnosis.json` 里有的字段，`offset_proxy` 不在其中——
> 它只能从 `centroid_distance` 和 `base_scale` 自行推算）。

---

## Case A vs Case B 区分能力

**Case A：小旋转（如 8°）+ 较大平移（centroid_distance ≈ 0.37）**
**Case B：大旋转（如 120°）+ 相似平移（centroid_distance ≈ 0.55）**

| 观察量 | Case A 数值范围 | Case B 数值范围 | 能否区分 |
|---|---|---|---|
| `centroid_distance` | ≈ 0.37 | ≈ 0.55 | **不能可靠区分**（两者都可 > 3× base_scale） |
| `density_ratio` | ≈ 1.0 | ≈ 1.0 | **不能**（干净数据时两者都接近 1） |
| `rotation_magnitude_estimate` | NOT_IMPLEMENTED | NOT_IMPLEMENTED | **缺失** |
| `overlap_ratio` | NOT_IMPLEMENTED | NOT_IMPLEMENTED | **缺失（大旋转时 overlap 显著下降，若实现可区分）** |

**结论：当前 Observation 集合无法可靠区分 Case A 与 Case B。**
根本原因：
1. 没有旋转量估计（`rotation_magnitude_estimate = NOT_IMPLEMENTED`）；
2. 没有重叠率估计（`overlap_ratio = NOT_IMPLEMENTED`）；
3. `centroid_distance` 混合了平移和旋转的质心偏移效应，无法解耦。

**L1 实际是 Case A 的数据（rot 8/-12/10°），但 `agnnes_decide` 的启发式
把 L1 和 L2 都判成了 hard → GLOBAL，L1 的"小角度快速通道"从未被触发。**

---

## 最大 Observation 缺口排序

1. **`rotation_magnitude_estimate`**（最严重）
   - 直接决定 LOCAL_ICP vs GLOBAL 的选择
   - 当前缺失导致两个 case 走同一分支，无法证明 scenario-adaptive 决策

2. **`overlap_ratio`**（L3/L4 必需）
   - 低重叠场景下 GLOBAL 也可能失败，需要重叠率判断

3. **`noise_level` / `outlier_level`**（L3 必需）
   - 脏数据场景参数策略应不同于干净场景

---

## 证据路径

| 项目 | 位置 |
|---|---|
| 完整字段清单（已实现） | `src/agent_diagnose.py` 第 73-94 行 |
| NOT_IMPLEMENTED 字段 | `src/agent_diagnose.py` 第 86-89 行 |
| L2 diagnosis.json 实际值 | `outputs/submission_evidence/L2/runs/l2_20261007_seed202_blind01/02_AGENT/diagnosis.json` |
| L1 diagnosis.json 实际值 | `outputs/submission_evidence/L1/runs/l1_20261007_seed101_run01/02_AGENT/diagnosis.json` |
| offset_proxy 临时计算（不在诊断 JSON 里） | `src/agent_runner.py` 第 51 行 |
