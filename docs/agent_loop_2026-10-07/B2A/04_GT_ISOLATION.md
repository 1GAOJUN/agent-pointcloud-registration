# 04_GT_ISOLATION — B2A GT 隔离声明与测试

**Phase B2A — Real Agnes Decision Integration**
**创建时间：2026-10-07**

---

## GT 隔离原则（不变）

> `gt_transform.npy` 只在 `agent_evaluator.evaluate_agent_result()` 里读取，
> 该函数在 Agent 循环**完全结束后**才被调用。
> Agnes 的两次调用（decision + assessment）均不接收、不接触 GT 字段。

---

## Agnes 输入白名单（合法可见）

Agnes 两次调用可接收：

| 字段 | 来源 | 合法可见？ |
|---|---|---|
| `diagnosis`（含 centroid_distance, base_scale, 各点云统计量） | `agent_diagnose.diagnose()` | ✅ 是 |
| `TOOL_REGISTRY`（工具说明、可调参数） | `agent_tools.py` | ✅ 是 |
| `PARAMETER_RANGE`（参数倍率上下界） | `agnnes_agent.py` guardrail | ✅ 是 |
| `prior_attempts`（历史 RETRY 记录） | runner 循环维护 | ✅ 是 |
| `observation`（fitness, rmse, ransac_fitness, elapsed_s） | 工具执行结果 | ✅ 是 |

## Agnes 输入黑名单（禁止）

| 字段 | 来源 | 禁止原因 |
|---|---|---|
| `gt_transform` / `gt_transform.npy` | Evaluator | GT 隔离 |
| `rotation_error` / `translation_error` | Evaluator 计算 | GT 指标 |
| 场景标签 `L1`/`L2`/`L3`/`L4` | 外部元数据 | 防止 Agnes 依赖外部标签 |
| 磁盘文件路径 | runner | 匿名化 |
| 历史正确算法 | 外部元数据 | 防止 Agnes 查答案 |

---

## 实现检查点

1. `agnnes_agent.build_decision_prompt()` 构造的 JSON 不包含黑名单字段 ✅（代码检查）
2. `agnnes_agent.build_assessment_prompt()` 构造的 JSON 不包含黑名单字段 ✅（代码检查）
3. `agent_runner.run_agent_case()` 的 Evaluator 调用（步骤 5）在 Agent 循环（步骤 2）结束之后 ✅
4. `tool_call_*.json` 里的 `gt_read: false` 字段 ✅

---

## 测试要求

B2A 完成后须保留并运行现有 GT 隔离测试：

- `tests/verify_gt.py`（现有）
- 新增（B2A 内）：检查 `agnnes_raw_response_*.json` 文本里不含黑名单关键词
  （如 `gt_transform`、`rotation_error`、`L1`、`L2` 等字符串）

---

## Evaluator 时序（不变）

```
Agent 循环（最多 MAX_RETRY_LIMIT 次）
  ├─ Agnes decision 1
  ├─ 工具执行 1
  ├─ Agnes assessment 1
  ├─ Agnes decision 2
  ├─ 工具执行 2
  ├─ Agnes assessment 2
  └─ ... ACCEPT / ABORT / 循环耗尽
↓
Agent 停止
↓
独立 Evaluator 调用
  ├─ 读 gt_transform.npy
  ├─ 计算 rotation_error / translation_error
  └─ 写入 evaluator_result.json
```

GT 只在 Evaluator 子图中出现，Agent（Agnes）路径与 Evaluator 之间**没有正向连线**，
Agnes 不可能读到 GT。
