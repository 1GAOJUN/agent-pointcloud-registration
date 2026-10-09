# 03_AGENT_GUARDRAILS — B2A Agnes 决策安全约束

**Phase B2A — Real Agnes Decision Integration**
**创建时间：2026-10-07**

---

## 目标

在"让真实 Agnes 做专业决策"的前提下，保留可审计的安全边界。
明确区分：

| 类型 | 执行者 | 性质 |
|---|---|---|
| **deterministic guardrail** | Python | 安全硬边界，文档化，非 Agnes 决策 |
| **Agnes professional judgment** | Agnes LLM | 算法/参数/ACCEPT-RETRY 选择，核心任务证据 |

---

## 一、参数范围 guardrail（Python 侧）

定义于 `src/agnnes_agent.py`：

```python
PARAMETER_RANGE = {
    "global_corr_scale": {"min": 2.0, "max": 10.0},
    "icp_max_corr_scale": {"min": 0.5, "max": 5.0},
}
```

**行为：**
- Agnes 输出的 `parameter_policy` 值超出范围 → **返回 error 给 Agnes 重新选择**
- 不静默 fallback 为 heuristic baseline 的固定值（5.0/2.0）
- 工具层还有下限保护 `max(1e-4, ...)`，双保险

**为什么是 2.0~10.0 和 0.5~5.0？**
- `global_corr_scale` 基于 B1 审计：5.0 是当前 hard branch 的已知有效值，
  范围扩展到 2.0~10.0 覆盖小偏移（2.0）到大偏移（10.0）场景
- `icp_max_corr_scale` 范围 0.5~5.0 覆盖 tight ICP（0.5）到宽松（5.0）场景

---

## 二、fitness 最低可接受边界（deterministic guardrail）

```python
FLOORGUARD_FITNESS = 0.3
```

**行为：**
- 若 Agnes 判断 ACCEPT，但实际 `fitness < 0.3` → 强制改写为 RETRY
- 改写后的 `reason` 字段明确标注 `[GUARDRAIL OVERWRITE]`，保留 Agnes 原始 reason
- 该字段在 assessment JSON 中标记为 `_guardrail_applied: "floor_fitness"`
- 这是 **deterministic guardrail**，不是 Agnes 决策，文档化于此

**为什么 0.3？**
- Open3D ICP fitness 在典型配准场景中，低于 0.3 基本意味着
  对应点极少或局部最优已偏离，继续 RETRY 比 ACCEPT 更安全
- 高于 0.3 的判断完全交给 Agnes（可能 0.4 在某些场景已够）

---

## 三、max_retry 上限（deterministic guardrail）

```python
MAX_RETRY_LIMIT = 3
```

**行为：**
- RETRY 次数超过 3 次后，Python 循环自动停止
- 即使 Agnes 认为还有 RETRY 价值，上限仍强制终止
- 最终 `agent_final_assessment` 由 Python 写入为 `ABORT`（guardrail 决定）

**为什么 3 次？**
- 防止无限循环（每个工具调用耗时 0.1~10s）
- 3 次足够让 Agnes 在两种工具 × 不同参数档位中尝试多种组合

---

## 四、selected_method 白名单（deterministic guardrail）

```python
ALLOWED_METHODS = {"LOCAL_ICP", "GLOBAL_FPFH_RANSAC_ICP"}
```

**行为：**
- Agnes 输出的 `selected_method` 不在白名单 → schema 校验失败，返回 error 重新选择
- 不允许 Agnes 指定未知工具

---

## 五、decision 值白名单（deterministic guardrail）

Agnes 的 assessment `decision` 字段必须为：

```
{"ACCEPT", "RETRY", "ABORT"}
```

超出 → 返回 schema error，不静默 fallback。

---

## 六、offset_proxy 映射隔离（防伪检查）

B1 审计发现的 `offset_proxy >= 3.0 → GLOBAL` 直接映射：

- **保留在**：`heuristic_decide()`（`src/agent_runner.py`，标注 `@deprecated`）
- **禁止进入**：`agnnes_real` 主路径
- 防伪检查（`agnnes_agent.audit_real_agnnes_run()`）会检查主路径里是否仍残留 offset_proxy 映射
  → 若存在，审计返回 FAIL

---

## 七、Agnes 两次调用均须发生（防伪 A/B 检查）

完成 B2A 后，自动验证：

| 检查项 | 操作 | FAIL 条件 |
|---|---|---|
| **A** | 关闭 Agnes 调用，系统能否自行决定 `selected_method`？ | 能 = 说明 Agnes 调用未实际参与，FAIL |
| **B** | 关闭 Agnes 调用，系统能否自行决定 `ACCEPT/RETRY`？ | 能 = FAIL |
| **C** | 主路径是否存在 `offset_proxy >= 3.0 → GLOBAL` 直接映射？ | 存在 = 不得进入 Agent 主路径，FAIL |

实现方式：
- 检查 1/2 通过审计 `agh_run_log.json` 的 `decision_implementation` 字段
- 检查 3 通过 grep `src/agent_runner.py` 主路径（`agnnes_real` 分支）里的 offset_proxy
