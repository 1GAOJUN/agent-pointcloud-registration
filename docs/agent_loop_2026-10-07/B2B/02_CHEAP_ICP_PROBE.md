# 02_CHEAP_ICP_PROBE — Cheap Local ICP Probe 设计说明

**Phase B2B — Active Observation Probe**
创建：2026-10-07
实现文件：`src/agent_probes.py`（`run_cheap_local_icp_probe`）

---

## 1. 定位

Probe B 回答：**当前局部初始化（identity 初值）是否已经有收敛迹象？**
是"低成本试探"，不是完成配准。注册方式同 Probe A（Agnes 可自主调用的观测工具）。

绝不读 GT；输出只含可观测指标，不含 `rotation_error` / `translation_error` / `gt_transform`。

## 2. 与正式 LOCAL_ICP 的差异（成本设计）

| 维度 | 正式 LOCAL_ICP（`agent_tools.run_local_icp`） | Cheap Local ICP Probe |
|---|---|---|
| ICP 迭代数 | `max_iteration=100` | `max_iteration=5`（固定） |
| Global 初始化 | 无（identity） | 无（identity） |
| SOR 离群剔除 | 无 | 无 |
| 对应距离 | `base_scale × icp_max_corr_scale`（Agnes 可调） | `base_scale × 2.0`（固定，低成本档位） |
| 法向量估计 | 有（`_ensure_normals`） | 有（`_ensure_normals`，成本主体） |
| 目的 | 完成配准 | 仅回答"局部是否已有收敛迹象" |
| 是否偷偷跑完 | 否 | 否 |

**实测成本对比（L2 seed_202，`outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/_cost_profile.json`）：**

| | 正式 ICP | Cheap ICP Probe | 比值 |
|---|---|---|---|
| ICP 迭代 | 100 | 5 | 20× |
| wall（含法向量） | 5.064 s | 0.319 s | ≈16× |
| 总成本占比 | — | ≈6.3% | Probe 满足"明显低于正式 ICP" |

## 3. 输出 Schema

```json
{
  "probe_name": "CHEAP_LOCAL_ICP",
  "initial_fitness": 0.2356,
  "probe_fitness": 0.2764,
  "initial_rmse": 0.03706,
  "probe_rmse": 0.03692,
  "fitness_improvement": 0.0408,
  "correspondence_count": null,
  "iterations": 5,
  "runtime_s": 0.464,
  "transform_delta_magnitude": 0.4083,
  "max_correspondence_distance": 0.0678,
  "note": "..."
}
```

字段说明：
- `initial_*`：identity 初值下 1 次迭代近似 baseline（Open3D 0.20 无 0 迭代选项，文档化注明）
- `correspondence_count`：Open3D `registration_icp` 不直接暴露逐迭代匹配数，置 `null`（不伪造）
- `transform_delta_magnitude`：`‖T_probe − T_init‖`（Frobenius），反映 5 次迭代后的位移幅度
- 禁止字段（不输出）：`rotation_error`、`translation_error`、`gt_transform`

## 4. 成本验证（B2B 完成标准第 4 项）

- 迭代数差：5 vs 100 → **20 倍**
- wall 差：0.32 s vs 5.06 s → **≈16 倍**
- 结论：Probe 成本明显低于正式 ICP（≈6%），不触发 NEEDS_REDESIGN

## 5. 禁止事项

- 不得把 Cheap ICP 做成与正式 `run_local_icp` 完全相同（迭代数必须受限）
- 不得在 Probe 结果到算法之间加固定阈值（如 `fitness_improvement < 0.1 → GLOBAL`）
- 不得读 GT
