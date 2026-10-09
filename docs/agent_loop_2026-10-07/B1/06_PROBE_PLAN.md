# 06_PROBE_PLAN — B2 Active Probe 候选分析与最小实现推荐

**Phase B1 — 只读分析，不实现，不修改源码。**

---

## 目标

当前最大 Observation 缺口：
1. `rotation_magnitude_estimate`（NOT_IMPLEMENTED）
2. `overlap_ratio`（NOT_IMPLEMENTED）

这两个缺口导致 L1（小角度）和 L2（大旋转）走了同一个 Python 分支，
无法证明 scenario-adaptive 决策。

B2 目标：用 Active Probe 补齐核心观测，让 Agnes（真实 LLM）真正有足够信息做选择。

---

## Probe A：PCA Orientation Probe

**目标**：估计 source 与 target 之间的粗姿态差异。

### 方法

对 source 和 target 各取 N 点（N≈1000，可复用采样上限），
各做 PCA（特征分解协方差矩阵），得到 3 个主方向（eigenvectors）。
比较两套主方向之间的夹角，估计粗旋转量。

### 必须分析的风险

| 风险 | 影响 | 处理 |
|---|---|---|
| **eigenvector 符号歧义** | 特征向量 `v` 和 `-v` 在 PCA 里等价，直接比较会误判 180° 反转 | 需通过法向量符号或局部几何消歧；或允许 ±  |
| **eigenvector 排列顺序** | 源/目标 PCA 的轴顺序可能不同（如源 x 轴对应目标 y 轴） | 需搜索排列（最多 6 种排列），取夹角最小的一组 |
| **对称物体** | 立方体、圆柱等对称物体 PCA 各向同性，无法区分轴向 | 输出 `orientation_confidence = LOW`，`ambiguity_reason = "symmetric_object"` |
| **特征值接近（各向同性）** | 特征值 λ₁ ≈ λ₂ ≈ λ₃ 时方向不稳定 | 若 λ₁/λ₃ < 1.5（各向同性比），输出 `LOW_CONFIDENCE` |
| **低点数/采样不足** | 点数过少时 PCA 不稳定 | 需 source/target 各 ≥ 200 点，否则 `UNKNOWN` |

### 建议输出结构

```json
{
  "rotation_estimate_deg": 45.2,       // 或 "UNKNOWN"
  "orientation_confidence": "HIGH|MED|LOW",
  "ambiguity_reason": "eigvalue_ratio_too_low | symmetric_object | null",
  "pca_eigenvalue_ratio": 3.7,         // λ₁/λ₃
}
```

### 评价

| 维度 | 评分（1-5） |
|---|---|
| L1/L2 区分价值 | 4（能直接区分小角度 vs 大旋转，但 PCA 精度有限） |
| 实现难度 | 2（numpy.linalg.eigh 即可，代码量小） |
| 代码复用 | 3（`agent_diagnose.py` 已有 numpy 点集处理框架，可插入） |
| 计算成本 | 5（极低成本，O(N) 协方差 + O(1) 特征分解） |
| 稳定性 | 3（对对称物体不稳定，需置信度字段兜底） |
| 可解释性 | 4（输出有 confidence 字段，Agnes 可据此判断可靠性） |
| L3/L4 未来价值 | 3（L3 噪声场景 PCA 稳定性下降，L4 低重叠时 PCA 可能失真） |

---

## Probe B：Cheap Local ICP Probe

**目标**：低成本跑少量 ICP 迭代，判断"identity 初值是否已经足够好"。

### 方法

对 source/target 各做统计离群剔除（SOR）+ 法向量估计，
用 `np.eye(4)` 初值跑 3-5 次 ICP 迭代（`max_iteration = 5`），
记录中间 fitness 和 rmse，判断收敛趋势。

### 必须分析的风险

| 风险 | 影响 | 处理 |
|---|---|---|
| **逻辑循环** | "为了决定要不要跑完整 ICP，先跑了一遍几乎完整 ICP"——若 ICP 本身代价高，Probe 就失去了 cheap 的意义 | ICP 单步本身 O(N×K)，5 次迭代 vs 100 次迭代，Probe 成本约为正式 ICP 的 5%，可接受 |
| **局部最优陷阱** | 大旋转场景下 ICP 从 identity 初值可能收敛到错误局部最优，Probe 结果会误导 | Probe 只输出"趋势"（fitness 是否单调上升、提升量），不直接下结论；Agnes 需结合其他 Probe 判断 |
| **法向量估计误差** | 低密度区域法向量不准，影响 point-to-plane ICP | Probe 结果带 `correspondence_count`（匹配点数）作为可靠性指标 |

### 建议输出结构

```json
{
  "probe_fitness": 0.35,             // 5 次迭代后 fitness
  "probe_rmse": 0.012,
  "correspondence_count": 8420,      // 有效匹配点数
  "improvement": 0.28,              // 相对初始 fitness 提升
  "runtime_s": 0.04,
  "interpretation_hint": "identity init may be sufficient | large rotation suspected"
}
```

### 评价

| 维度 | 评分（1-5） |
|---|---|
| L1/L2 区分价值 | 5（L1 小角度：identity ICP probe 会迅速收敛，L2 大旋转：identity ICP probe 收敛慢/差） |
| 实现难度 | 2（复用 `agent_tools.py` 的 SOR + ICP 代码，只改 `max_iteration=5`） |
| 代码复用 | 4（`run_local_icp` 已有完整 ICP 代码，Probe 可复用其 SOR 和法向量估计部分） |
| 计算成本 | 3（比正式 ICP 便宜约 20 倍，但仍比 PCA Probe 慢） |
| 稳定性 | 4（ICP 结果可重复，不依赖特征匹配稳定性） |
| 可解释性 | 4（`improvement` 和 `correspondence_count` 直观） |
| L3/L4 未来价值 | 4（L3 脏数据时 ICP probe 仍能反映收敛趋势；L4 低重叠时 correspondence_count 低是有效信号） |

---

## Probe C：Feature Matching Probe

**目标**：有限 FPFH 特征匹配质量测试，判断全局配准是否值得尝试。

### 方法

对 source/target 各提取 ≤500 个 FPFH 关键点（复用 `agent_tools.py` 的 FPFH 提取代码），
用暴力匹配或 KDTree 最近邻匹配，统计：
- 匹配点数（`inlier_count`）
- 匹配一致性（`consistency`：匹配角度分布集中度）

### 必须分析的风险

| 风险 | 影响 | 处理 |
|---|---|---|
| **对称/低纹理区域特征质量差** | 特征匹配不稳定，Probe 结果波动大 | 输出 `feature_match_quality` 时用 inlier_ratio 而非绝对数 |
| **特征提取计算成本** | FPFH 计算约 0.5-2s（500 点），Probe 成本中等 | 可接受，比正式 GLOBAL 配准便宜 |
| **低重叠场景匹配点少** | 重叠率低时 inlier 极少，Probe 结果不可靠 | `correspondence_count < 50` 时输出 `LOW_CONFIDENCE` |

### 建议输出结构

```json
{
  "feature_match_quality": 0.72,     // 归一化 inlier 比例
  "candidate_correspondences": 210,
  "consistency": 0.65,               // 角度分布集中度（0-1）
  "confidence": "HIGH|MEDIUM|LOW"
}
```

### 评价

| 维度 | 评分（1-5） |
|---|---|
| L1/L2 区分价值 | 3（FPFH 匹配在干净数据时质量都高，区分 L1 vs L2 的能力弱于 ICP probe） |
| 实现难度 | 2（复用 `agent_tools.py` FPFH 提取代码） |
| 代码复用 | 4 |
| 计算成本 | 3（FPFH 提取约 0.5-2s，可接受） |
| 稳定性 | 3（对称物体特征匹配质量可能波动） |
| 可解释性 | 3 |
| L3/L4 未来价值 | 5（L3 脏数据场景：特征匹配质量直接反映全局配准可行性；L4 低重叠：overlap 信息） |

---

## Probe D：Overlap Estimate

**目标**：估计 source 与 target 的重叠比例（主要用于未来 L4）。

### 方法

对 source 点集做 KDTree，统计有多少 source 点在 target KDTree 的某半径内有近邻
（`radius = k × base_scale`，k≈3），比例即 overlap 估计。

### 评价

| 维度 | 评分（1-5） |
|---|---|
| L1/L2 区分价值 | 2（L1/L2 干净场景 overlap≈1.0，区分度低） |
| 实现难度 | 2（KDTree 已有框架，代码量小） |
| 代码复用 | 3 |
| 计算成本 | 4（O(N log N) KDTree 构建 + O(N) 查询） |
| 稳定性 | 4（overlap 估计对噪声不敏感，鲁棒） |
| 可解释性 | 5（数值直观，"重叠 80%" 易理解） |
| L3/L4 未来价值 | 5（L4 低重叠场景是核心用例） |

**B2 阶段暂不实现**（L1/L2 区分价值低，留待 L4 阶段）。

---

## B2 最小实现推荐

**推荐组合：Probe A（PCA Orientation）+ Probe B（Cheap Local ICP Probe）**

理由：

1. **最小代码量**：
   - Probe A 约 40 行（numpy PCA + 特征值比计算）
   - Probe B 约 50 行（复用 `run_local_icp` 代码，只改 `max_iteration=5`，封装输出）
   - 合计约 90 行，远低于 Probe C + D 的组合

2. **最大信息增益**：
   - Probe A 直接补齐 `rotation_magnitude_estimate`（当前最大缺口）
   - Probe B 提供 identity 初值收敛质量，帮助 Agnes 判断"小角度直接 ICP 是否够用"
   - 两个 Probe 联合：Agnes 可基于"粗旋转量 + ICP 收敛趋势"做出真正有信息量的算法选择

3. **L1/L2 区分能力最强**：
   - L1（8° 小角度）：PCA 估计 ≈ 8°，ICP probe convergence 快 → 倾向 LOCAL_ICP
   - L2（120° 大旋转）：PCA 估计 ≈ 120°，ICP probe convergence 差 → 倾向 GLOBAL

4. **稳定性可控**：
   - Probe A 带 `orientation_confidence` 字段，Agnes 可判断何时不可信
   - Probe B 带 `correspondence_count`，低重叠时可识别

**Probe C 和 Probe D 留给后续阶段**（L3/L4 时再实现）。

---

## 禁止事项（B2 实施时）

- 不得把 Probe 结果写进 `agent_diagnose.py` 的固定诊断字段（Probe 是 Agnes 主动调用的工具，不是诊断的一部分）
- 不得在 Probe 里读 GT
- 不得把 Probe 结果直接映射成算法（"rotation > 30° → GLOBAL" 又变成固定 heuristic，违背 Agent 自主决策目标）
- 不得把 Probe 设计成与正式工具调用完全相同（Probe 必须是 cheap 版本）

---

## 证据路径

| 项目 | 位置 |
|---|---|
| PCA 实现框架参考 | `src/agent_diagnose.py`（numpy 点集处理） |
| ICP 代码复用参考 | `src/agent_tools.py` `run_local_icp` 第 72-105 行 |
| FPFH 代码复用参考 | `src/agent_tools.py` 第 131-141 行 |
| KDTree 参考 | `src/agent_diagnose.py` `_nearest_neighbor_distance` 第 30-51 行 |
