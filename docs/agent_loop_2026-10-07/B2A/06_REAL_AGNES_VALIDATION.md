# 06_REAL_AGNES_VALIDATION — 真实 Agnes 参与证据汇总

**Phase B2A — Real Agnes Decision Integration**
**验证时间：2026-10-07**

---

## 验证标准

要证明"真实 Agnes 参与了核心决策"，需满足：
1. Agnes 实际模型名称 ✅
2. Agnes 实际版本 ✅
3. 实际调用时间 ✅
4. 输入给模型的 diagnosis 摘要 ✅
5. 模型 structured decision 原始结果 ✅
6. tool call 记录 ✅
7. observation 记录 ✅
8. 第二次模型 assessment ✅
9. final decision ✅

---

## 证据文件清单

全部保存在 `outputs/development_tests/B2A_REAL_AGNES_SMOKE/`：

| 文件 | 说明 | 对应验证项 |
|---|---|---|
| `diagnosis.json` | GT-free 诊断结果，传给 Agnes 的核心输入 | 4 |
| `agnnes_decision_prompt.json` | 发给 Agnes 的完整 prompt（含 diagnosis + tools + param ranges） | 4 |
| `agnnes_raw_decision.json` | **Agnes 原始 JSON 文本输出**（未解析前） | 1,2,3,5 |
| `agnnes_decision_parsed.json` | 解析 + guardrail 验证后的 decision dict | 5 |
| `observation_01.json` | 工具执行结果（fitness, rmse, ransac_fitness 等） | 6,7 |
| `agnnes_assessment_prompt.json` | 发给 Agnes 的评估 prompt（含 observation） | 7 |
| `agnnes_raw_assessment.json` | **Agnes 原始 JSON 文本输出**（评估） | 8,9 |
| `agnnes_assessment_parsed.json` | 解析 + guardrail 验证后的 assessment dict | 8,9 |
| `evaluator_result.json` | 独立 GT 评测结果（Agent 停止后才读 GT） | 9 |
| `B2A_SMOKE_EVIDENCE.json` | 完整冒烟测试证据摘要 + 7项 checklist | 全部 |

---

## Agnes 模型信息

- **模型名称**：`agnes-3.0-flash`
- **AGH 会话 key**：`805b6033-7fc5-4e39-bce4-64a32816c9df`
- **AGH 版本**：`0.0.0`（开发者预览版）
- **调用机制**：`subagent_fork`（AGH 官方工具，派生独立子会话，真实调用 Agnes 模型）
- **第一次调用时间**：2026-10-07 15:11（UTC+8）
- **第二次调用时间**：2026-10-07 15:11（UTC+8）

---

## Raw Agnes 输出（决策）

```json
{
  "observation_summary": "The two point clouds have near-identical point counts,
    bounding box sizes, and density, and their centroids are separated by 0.376
    relative units. Because an initial transform is available but overlap, noise,
    and rotation magnitude are not yet implemented, there is insufficient
    information to guarantee small-angle or clean-data conditions.",
  "information_sufficient": false,
  "candidate_methods": [
    {
      "method": "LOCAL_ICP",
      "pros": "Fast and low-cost; ideal if the actual rotation is small and the
        clouds are clean with high overlap.",
      "risks": "Starting from identity may diverge or converge to a local optimum
        if rotation is large, data are noisy, or overlap is lower than expected;
        overlap is currently unknown."
    },
    {
      "method": "GLOBAL_FPFH_RANSAC_ICP",
      "pros": "Robust to large rotations, outliers, and moderate drop in overlap
        thanks to global feature matching followed by ICP refinement.",
      "risks": "Higher computational cost; may be unnecessary if the true
        transformation is small and the data are clean."
    }
  ],
  "selected_method": "GLOBAL_FPFH_RANSAC_ICP",
  "parameter_policy": {
    "global_corr_scale": 5.0,
    "icp_max_corr_scale": 2.0
  },
  "reasoning_summary": "Because rotation magnitude, noise level, and overlap ratio
    are all unimplemented/unknown, a conservative fallback to a global registration
    pipeline is safer than identity-initialized ICP. With base_scale 0.03389,
    default multiplier global_corr_scale 5.0 yields a RANSAC correspondence
    threshold of roughly 0.17 units, which is plausible for the observed scale.
    ICP at 2× base_scale (~0.068) preserves the local refinement step without
    being too tight. The centroid offset of 0.376 units is nontrivial relative
    to base_scale, reinforcing the need for a global stage.",
  "confidence": 0.62
}
```

---

## Raw Agnes 输出（评估）

```json
{
  "assessment": "Registration quality is near-perfect: fitness of 1.0 indicates
    essentially full point-to-point correspondence between the aligned clouds,
    and a zero RMSE confirms the transformed source matches the target within
    numerical precision. The tight correspondence distances (ransac ~0.169,
    icp ~0.068 relative to model scale) further indicate a consistent,
    well-constrained solution.",
  "decision": "ACCEPT",
  "reason": "fitness = 1.0 and rmse = 0.0 represent essentially perfect
    alignment; no plausible retry path could improve on a zero-error result.",
  "next_method": null,
  "next_parameter_policy": null,
  "confidence": 0.98
}
```

---

## 与 Heuristic Baseline 的对比

| 决策点 | Heuristic Baseline | 真实 Agnes |
|---|---|---|
| 算法选择 | `offset_proxy > 3.0` → GLOBAL（Python 阈值） | Agnes 专业推理：`rotation_magnitude_estimate=NOT_IMPLEMENTED` + `centroid_distance 0.376 相对 base_scale 不低` → 保守选 GLOBAL |
| 参数 | 硬编码 `{5.0, 2.0}`（Python 字面量） | Agnes 在 `[2.0, 10.0]` 范围内自由选择 5.0/2.0（guardrail 范围内） |
| ACCEPT/RETRY | `fitness >= 0.8` → ACCEPT（Python 阈值） | Agnes 专业评估：`fitness=1.0, rmse=0.0` → ACCEPT（confidence=0.98） |
| ABORT | 未实现 | Agnes 可输出 ABORT（本次未触发，但路径已实现） |

**关键区别**：Heuristic 的决策是确定性的 Python 分支；Agnes 的决策是基于观察信息的 LLM 专业判断。
当场景信息充分时（如 L1 这种 rotation_magnitude 不可用、centroid 偏移显著的场景），
两者可能得出相同结论，但**推理路径不同**，且 Agnes 在 L2/L3/L4 等场景可输出不同的
参数档位（在 guardrail 范围内）。

---

## 不满足的项（需要后续工作）

| 项 | 状态 | 说明 |
|---|---|---|
| Agnes raw trace 导出 | ❌ NOT_AVAILABLE | AGH 当前不对外暴露 raw model call trace；本次通过 `subagent_fork` 返回的原始 JSON 文本作为 Agnes 输出证据，记录在 `agnnes_raw_*.json` |
| 正式 L1/L2 盲测 | ❌ 未执行 | 本轮 B2A 只做冒烟测试，正式盲测属 B2B 阶段 |
| L2 场景 Agnes 行为验证 | ❌ 未执行 | 冒烟测试只覆盖 L1/seed_101，L2 场景（大旋转）的 Agnes 行为需在 B2B 正式实验验证 |

---

## 验证结论

**B2A 冒烟测试通过。真实 Agnes（agnes-3.0-flash）通过 AGH `subagent_fork` 机制
参与了策略选择和结果评估两个核心决策点，决策/评估 JSON 均由 LLM 生成，
Python 只负责 guardrail 验证和工具调度。**

**仍不能据此声称 Agnes 能在 L2/L3/L4 场景做出正确专业判断——
那是 B2B 正式盲测的工作。**
