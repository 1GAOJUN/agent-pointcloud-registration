# 01_PCA_PROBE — PCA Orientation Probe 设计说明

**Phase B2B — Active Observation Probe**
创建：2026-10-07
实现文件：`src/agent_probes.py`（`run_pca_orientation_probe`）

---

## 1. 定位

Probe A 是 Agnes 可自主调用的**观测工具**，不是配准算法，
因此注册在 `agent_probes.PROBE_REGISTRY`（独立于 `agent_tools.TOOL_REGISTRY` 的正式配准工具列表）。

回答的问题：**source 与 target 的粗姿态差异有多大？主轴结构是否稳定到可以给出角度？**

绝不读 GT（`gt_transform` / `rotation_error` / `translation_error` / 场景标签）。

## 2. 算法

1. 各取 min(N, 1000) 点（`np.random.RandomState(seed=101)`，与 `agent_diagnose` 采样风格一致）
2. 去均值 → 协方差 `C = (c.T @ c)/(n-1)` → `np.linalg.eigh` → 特征值降序
   `λ0 ≥ λ1 ≥ λ2`，特征向量 `V`（3×3 正交，列向量）
3. 各向异性 `anisotropy = λ0/λ2`
4. 稳定性分级（纯几何判据，不用 GT）：
   - `λ0/λ1 < 1.25 且 λ1/λ2 < 1.5` → **LOW**，`near_isotropic_or_symmetric`
   - `λ0/λ1 < 1.25` → **LOW**，`near_planar_degeneracy`（平面内取向不确定）
   - `λ1/λ2 < 1.25` → **LOW**，`near_line_degeneracy`（横向两轴不确定）
   - 仅一对特征值比 < 1.5 → **MEDIUM**，`partial_axis_degeneracy`
   - 否则 → **HIGH**
5. rotation_estimate（仅当两侧均非 LOW）：
   - 枚举目标侧 6 种轴排列 × 逐轴贪心符号消歧（`v ← ±v` 使与源 frame 对应轴点积最大）
   - 取 `|trace(R)|` 最大（= 相对旋转角最小，几何一致性最高）的组合
   - 角度 = `arccos((trace(V_tgt·V_src^T)-1)/2)`，范围 [0, 180°]
   - 记录方法：`ambiguity_handling = "per_axis_sign_greedy + permutation_argmax_trace"`
6. 任一侧 LOW → `rotation_estimate_deg = null`，`orientation_confidence = LOW`

## 3. 输出 Schema

```json
{
  "probe_name": "PCA_ORIENTATION",
  "rotation_estimate_deg": 45.0,           // 或 null（LOW 时）
  "orientation_confidence": "HIGH|MEDIUM|LOW",
  "ambiguity_detected": false,
  "ambiguity_reason": null,               // LOW 时给文字原因
  "source_anisotropy": 2.83,
  "target_anisotropy": 2.83,
  "source_eigenvalues": [0.11647, 0.04454, 0.04117],
  "target_eigenvalues": [...],
  "selected_axis_permutation": [0, 1, 2], // 仅估计成功时
  "ambiguity_handling": "per_axis_sign_greedy + permutation_argmax_trace",
  "runtime_s": 0.026,
  "note": "角度是 PCA 主轴 frame 相对旋转（0~180°），非逐点配准误差"
}
```

## 4. 实测

| Case | 结果 |
|---|---|
| 构造椭球（1,0.4,0.15 各向异性）绕 z 旋转 45° | `rotation_estimate_deg=45.0, HIGH`（精确命中） |
| 球壳（近各向同性） vs 椭球 / 球壳 vs 球壳 | `null, LOW, near_isotropic_or_symmetric`（不伪造角度） |
| L1 seed_101（真实数据，30k 点） | `null, LOW, near_line_degeneracy`（λ1≈λ2，横向轴不确定）— 见 05 smoke |

## 5. 成本

numpy 3×3 `eigh` + 1000 点采样，实测 wall < 10 ms；与正式 ICP（秒级）相比近零成本。

## 6. 禁止事项

- 不得把输出角度映射成 `rotation > 30° → GLOBAL` 之类的固定 heuristic（那是 Agnes 的专业判断）
- 不得在 Probe 内读 GT / 场景标签
- LOW confidence 时不得输出数值角度
