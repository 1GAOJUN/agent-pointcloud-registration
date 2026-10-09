# 02_DECISION_SCHEMA — B2A Agnes 决策/评估结构化 Schema

**Phase B2A — Real Agnes Decision Integration**
**创建时间：2026-10-07**

---

## 第一次决策：Agnes 读取 diagnosis + tools，输出 strategy decision

**输入（Python 构造，通过 AGH prompt 发送给 Agnes）：**

```json
{
  "task": "3D point cloud registration strategy selection",
  "diagnosis": {
    "source_point_count": 50000,
    "target_point_count": 50000,
    "source_bbox_diagonal": 0.8457,
    "target_bbox_diagonal": 0.8457,
    "source_median_spacing": 0.011,
    "target_median_spacing": 0.010,
    "density_ratio": 0.91,
    "centroid_distance": 0.376,
    "initial_transform_available": true,
    "sample_size": 5000,
    "sampling_seed": 101,
    "overlap_ratio": "NOT_IMPLEMENTED",
    "noise_level": "NOT_IMPLEMENTED",
    "outlier_level": "NOT_IMPLEMENTED",
    "rotation_magnitude_estimate": "NOT_IMPLEMENTED",
    "base_scale": 0.0339
  },
  "available_tools": [
    {
      "tool_name": "LOCAL_ICP",
      "purpose": "单位阵初值的点到面 ICP。低成本、快。",
      "applicable_conditions": "旋转角度较小、数据干净、source 与 target 重叠高、尺度接近。",
      "adjustable_parameters": ["icp_max_corr_scale"],
      "returned_metrics": ["transform", "fitness", "rmse", "inlier_rmse", "elapsed_s"],
      "known_limitations": "初值只能单位阵；大角度/脏数据/低重叠下发散或局部最优。"
    },
    {
      "tool_name": "GLOBAL_FPFH_RANSAC_ICP",
      "purpose": "统计离群剔除 + FPFH + RANSAC 全局配准，再点到面 ICP。高成本、鲁棒。",
      "applicable_conditions": "大角度、脏数据（噪声/离群）、重叠较低、或 LOCAL_ICP 失败时的补救。",
      "adjustable_parameters": ["global_corr_scale", "icp_max_corr_scale"],
      "returned_metrics": ["transform", "fitness", "rmse", "ransac_fitness", "ransac_rmse", "elapsed_s"],
      "known_limitations": "耗时高；对完全干净且小角度数据可能不必要；对极低重叠仍有限。"
    }
  ],
  "parameter_ranges": {
    "global_corr_scale": {"min": 2.0, "max": 10.0},
    "icp_max_corr_scale": {"min": 0.5, "max": 5.0}
  },
  "prior_attempts": []
}
```

**Agnes 输出（structured JSON）：**

```json
{
  "observation_summary": "源/目标各 50000 点，centroid_distance=0.376 相对 base_scale=0.0339 显著，密度比 0.91 基本均衡，旋转量估计不可用（NOT_IMPLEMENTED）。",
  "information_sufficient": true,
  "candidate_methods": [
    {
      "method": "GLOBAL_FPFH_RANSAC_ICP",
      "pros": "centroid_distance 显著高于 base_scale，提示初值偏移大，需要全局配准提供鲁棒初值",
      "risks": "计算成本高，对纯小角度干净场景可能过度"
    },
    {
      "method": "LOCAL_ICP",
      "pros": "计算成本低、速度快",
      "risks": "centroid_distance 相对 base_scale 较大，identity 初值收敛困难，fitness 可能不足"
    }
  ],
  "selected_method": "GLOBAL_FPFH_RANSAC_ICP",
  "parameter_policy": {
    "global_corr_scale": 5.0,
    "icp_max_corr_scale": 2.0
  },
  "reasoning_summary": "centroid_distance/base_scale ≈ 11.1，初值偏移大，且 rotation_magnitude_estimate 不可用，无法确认小角度，选择 GLOBAL_FPFH_RANSAC_ICP 提供鲁棒初值，参数取中等倍率。",
  "confidence": 0.65
}
```

**Schema 约束（Python guardrail 验证）：**

- `selected_method` ∈ {`"LOCAL_ICP"`, `"GLOBAL_FPFH_RANSAC_ICP"`}
- `parameter_policy.global_corr_scale` ∈ [2.0, 10.0]
- `parameter_policy.icp_max_corr_scale` ∈ [0.5, 5.0]
- `confidence` ∈ [0.0, 1.0]
- 输出 JSON 解析失败 → 返回 error 给 Agnes 重新生成，**不静默 fallback 为 heuristic**

---

## 第二次决策：Agnes 读取 observation，输出 ACCEPT/RETRY/ABORT

**输入（Python 构造）：**

```json
{
  "task": "Registration result assessment: ACCEPT / RETRY / ABORT",
  "current_attempt": {
    "method": "GLOBAL_FPFH_RANSAC_ICP",
    "parameter_policy": {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0},
    "observation": {
      "fitness": 0.97,
      "rmse": 0.0032,
      "ransac_fitness": 0.45,
      "elapsed_s": 8.2,
      "tool_name": "GLOBAL_FPFH_RANSAC_ICP"
    }
  },
  "prior_attempts": [],
  "guardrail_reference": {
    "floor_fitness": 0.3,
    "max_retry_remaining": 3
  }
}
```

**Agnes 输出（structured JSON）：**

```json
{
  "assessment": "fitness=0.97 接近 1.0，说明配准结果收敛良好；ransac_fitness=0.45 表明全局初值匹配点数有限但最终 ICP 精化效果良好。",
  "decision": "ACCEPT",
  "reason": "可观测 fitness 已接近满分，rmse 低于诊断尺度，配准质量可接受。",
  "next_method": null,
  "next_parameter_policy": null,
  "confidence": 0.85
}
```

**Schema 约束：**

- `decision` ∈ {`"ACCEPT"`, `"RETRY"`, `"ABORT"`}
- 若 RETRY：`next_method` 和 `next_parameter_policy` 必填
- `confidence` ∈ [0.0, 1.0]
- Guardrail 覆写：若 `fitness < 0.3` 且 Agnes 输出 `ACCEPT`，强制改为 `RETRY`（guardrail，非 Agnes 决策）

---

## 禁止写入 Agnes prompt 的字段

| 字段 | 理由 |
|---|---|
| `gt_transform` / `gt_transform.npy` | GT 隔离，只在 Evaluator 阶段读取 |
| `rotation_error` / `translation_error` | GT 指标，Agnes 不可见 |
| `L1/L2/L3/L4` 场景标签 | 防止 Agnes 依赖外部标签而非自身判断 |
| 磁盘文件路径 | 匿名化，不含完整路径 |
| 历史正确算法 | 防止 Agnes 直接查答案 |

---

## Agnes 不可见的指标

当前 diagnosis 中的 `rotation_magnitude_estimate = NOT_IMPLEMENTED`，
Agnes 不得假设该字段有有效数值；在 prompt 中该字段值明确为字符串 `"NOT_IMPLEMENTED"`，
Agnes 可据此选择置信度较低的参数策略，这是合规的（基于"信息不足"的专业判断，
不是基于 GT 的判断）。
