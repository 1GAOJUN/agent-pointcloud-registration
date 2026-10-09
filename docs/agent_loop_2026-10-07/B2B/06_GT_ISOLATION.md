# 06_GT_ISOLATION — B2B GT 隔离声明与验证

**Phase B2B — Active Observation Probe**
创建：2026-10-07
继承：B2A `04_GT_ISOLATION.md` 全部规则，本轮扩展 Probe 层

---

## GT 隔离原则（不变）

> `gt_transform.npy` 只在 `agent_evaluator.evaluate_agent_result()` 里读取，
> 该函数在 Agent 循环（含所有 Probe 调用 + 正式工具执行 + assessment）**完全结束后**才被调用。
> Agnes 的三次决策调用（decision #1/#2/#3）与一次评估调用均不接收、不接触 GT 字段。

---

## Agnes 输入白名单（B2B 扩展后合法可见）

| 字段 | 来源 | 合法可见？ |
|---|---|---|
| `diagnosis`（centroid_distance, base_scale, 点云统计量） | `agent_diagnose.diagnose()` | ✅ |
| `available_tools`（LOCAL_ICP / GLOBAL_FPFH_RANSAC_ICP 说明） | `agent_tools.TOOL_REGISTRY` | ✅ |
| `parameter_ranges` | `agnnes_agent.PARAMETER_RANGE` | ✅ |
| `probes.available_probes`（Probe 元数据：purpose/returns/cost/limitations） | `agent_probes.PROBE_REGISTRY` | ✅ |
| `probes.observations`（Probe 的可观测输出，如 `rotation_estimate_deg`、`probe_fitness`） | `agent_probes.run_*_probe` 返回值 | ✅ |
| `probes.already_executed` / `quota_note` | Python loop 维护 | ✅ |
| `observation`（正式工具 fitness/rmse/elapsed_s） | 工具执行结果 | ✅ |

## Agnes 输入黑名单（禁止，B2B 不变）

| 字段 | 来源 | 禁止原因 |
|---|---|---|
| `gt_transform` / `gt_transform.npy` | Evaluator | GT 隔离 |
| `rotation_error` / `translation_error` | Evaluator 计算 | GT 指标 |
| 场景标签 `L1/L2/L3/L4` | 外部元数据 | 防 Agnes 依赖外部标签 |
| 磁盘文件路径 | runner / 冒烟脚手架 | 匿名化 |

**Probe 输出特别说明**：
- `PCA_ORIENTATION` 的 `rotation_estimate_deg` 是 **PCA 主轴 frame 相对旋转**，由纯几何计算得出，
  **不是** `gt_transform` 里的 rotation，也**不是** Evaluator 的 `rotation_error_deg`。
  字段名刻意不同（`rotation_estimate_deg` vs `rotation_error`），避免语义混淆。
- `CHEAP_LOCAL_ICP` 的 `probe_fitness` / `probe_rmse` 是 Open3D `registration_icp` 的
  inlier 统计量，与 GT 无关。

---

## 实现检查点（B2B 新增）

1. `agnnes_agent.build_decision_prompt()` 构造的 JSON 不含黑名单字段 ✅（代码检查 + 冒烟文件扫描）
2. `agnnes_agent.build_assessment_prompt()` 同上 ✅
3. `agent_probes.run_pca_orientation_probe` / `run_cheap_local_icp_probe` 函数体
   只调用 `o3d.io.read_point_cloud(source_ply/target_ply)` 与 `agent_tools._load`，
   无任何 `gt_transform` / `rotation_error` / `translation_error` 引用 ✅（grep 确认）
4. 冒烟证据文件关键词扫描：`gt_transform`、`rotation_error`、`translation_error`、
   `L1`、`L2`、`seed_101`、`seed_202` 在全部 `agnnes_*.json` 中 0 命中 ✅

---

## Evaluator 时序（B2B 扩展）

```
Agent 循环
  ├─ Agnes decision #1（diagnosis + tools + probe 元数据）
  ├─ （若 information_sufficient=false）Python dispatch Probe 1
  ├─ Agnes decision #2（+ Probe 1 观测）
  ├─ （若仍 false）Python dispatch Probe 2
  ├─ Agnes decision #3（+ Probe 2 观测 → 必须给正式方法）
  ├─ 正式工具执行（LOCAL_ICP / GLOBAL_FPFH_RANSAC_ICP）
  ├─ Agnes assessment（ACCEPT / RETRY / ABORT）
  └─ ... RETRY 循环（最多 MAX_RETRY_LIMIT）
↓
Agent 停止
↓
独立 Evaluator 调用
  ├─ 读 gt_transform.npy
  ├─ 计算 rotation_error_deg / translation_error
  └─ 写 evaluator_result.json
```

GT 只在 Evaluator 子图出现，Agent（Agnes + Probe）路径与 Evaluator 之间**没有正向连线**。

---

## 测试结果

- `tests/verify_gt.py`（B1 遗留）仍可通过 ✅
- B2B 冒烟：全部 12 个 `agnnes_*.json`（3 decision prompts + 3 raw decisions + 3 parsed + 1 assessment prompt + 1 raw assessment + 1 parsed）关键词扫描 **0 命中** ✅
- Probe 单元测试 `T3_cheap_icp_no_gt_fields`：Probe 输出无 GT 字段 ✅

**B2B GT 隔离：PASS**
