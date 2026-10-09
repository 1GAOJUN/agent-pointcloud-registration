# 01_DECISION_AUDIT — 算法选择归因审计

**Phase B1 — 只读审计，不修改任何源码、Prompt、证据。**

---

## 核心结论

**算法选择归因：C**（Python/规则已经决定算法，Agnes 主要负责解释/结构化输出）

> 当前系统里 **没有任何一个真正的 LLM 决策调用**。
> `agnnes_decide` / `agnnes_assess`（`src/agent_runner.py`）是**纯 Python 启发式**，
> 输出结构模仿"Agnes 决策"，但没有调用 Agnes 模型。
> 所有"Agent 决策"实际上都是由 Python 代码里的固定分支逻辑直接算出来的。

---

## A1. offset_proxy 的准确计算公式

**位置**：`src/agent_runner.py`，`agnnes_decide` 函数，第 51 行：

```python
offset_proxy = centroid / max(base_scale, 1e-9)
```

其中：
- `centroid` = `diagnosis["centroid_distance"]`（`agent_diagnose.py` 第 71 行，
  `np.linalg.norm(tp.mean(axis=0) - sp.mean(axis=0))`）
- `base_scale` = `diagnosis["base_scale"]`（`agent_diagnose.py` 第 94 行，
  `max(src_median_spacing, bbox_diagonal / 50.0)`）

数值（L2 seed_202）：`0.5591 / 0.03389 ≈ 16.5`

数值（L1 seed_101）：`0.3761 / 0.03389 ≈ 11.1`

---

## A2. 阈值 3.0 在哪里定义

**位置**：`src/agent_runner.py`，第 52 行：

```python
easy = offset_proxy < 3.0 and (ratio is None or 0.5 < ratio < 2.0)
```

硬编码为字面量 `3.0`，无注释说明来源，无配置项。
`density_ratio` 范围约束 `0.5 < ratio < 2.0` 也在同一行，同样是字面量。

---

## A3. 是谁执行 `offset_proxy > 3.0` 判断

**答案：纯 Python 代码（`agnnes_decide` 函数）**。

```
agnnes_decide（第 44-90 行）
  offset_proxy = centroid / base_scale   # 第 51 行
  easy = offset_proxy < 3.0 AND ...     # 第 52 行
  if not easy → GLOBAL_FPFH_RANSAC_ICP  # 第 60-64 行
  if easy   → LOCAL_ICP                # 第 54-58 行
```

不是 Prompt 规则，不是 Agnes 模型判断。
`agnnes_decide` 函数内没有任何对 Agnes 模型的调用。
注释明确写着（第 43 行）：
> `# ---- 真实 Agnes 决策（本实现为可审计的启发式，见模块尾说明）----`

即：**这是一个"假装是 Agnes 决策"的 Python 启发式**。

---

## A4. "hard scenario branch" 到底是什么

`agnnes_decide` 里的三个分支：

| 条件 | 分支名 | 结果 |
|---|---|---|
| `not prior_attempts and easy` | easy branch | LOCAL_ICP, policy={icp_max_corr_scale:2.0}, conf=0.7 |
| `not prior_attempts and not easy` | **hard branch** | **GLOBAL_FPFH_RANSAC_ICP**, policy={global_corr_scale:5.0, icp_max_corr_scale:2.0}, conf=0.6 |
| `prior_attempts` 存在（RETRY） | retry branch | 切换另一工具, policy={icp_max_corr_scale:1.5}或{global_corr_scale:4.0,icp_max_corr_scale:1.5}, conf=0.45 |

L1 和 L2 都走的是 **hard branch**（`offset_proxy > 3.0` 或 density_ratio 不在 (0.5, 2.0) 范围内）。
L1 seed_101：`offset_proxy ≈ 11.1`，走 hard branch。
L2 seed_202：`offset_proxy ≈ 16.5`，走 hard branch。
**easy branch 从未被触发过**，因此"小角度场景选 LOCAL_ICP"的路径没有被任何实验覆盖。

---

## A5. 进入 hard branch 后，算法是否已经被程序指定

**是，完全被程序指定。**

hard branch 的 `selected`、`policy`、`reasoning`、`conf` 全部是写死在 `agnnes_decide` 函数体里的字面量：

```python
selected = "GLOBAL_FPFH_RANSAC_ICP"
policy = {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0}
reasoning = "初值偏移大或密度比失衡，判定为较难场景，直接用全局配准兜底。"
conf = 0.6
```

Agnes 模型在此分支内没有任何自由度——不是"选择"，是"被赋值"。

---

## A6. 如果完全删除 Agnes 模型调用，当前 Python 是否仍能决定 GLOBAL_FPFH_RANSAC_ICP

**是，且实际上 Agnes 模型调用根本不存在。**

`agnnes_decide` 就是一个纯 Python 函数，没有调用任何 LLM。
即使把所有"Agnes"相关的字符串都删掉，
L1 和 L2 的算法选择、参数、评估结果都不会有任何变化。
这是整个审计最关键的事实：**"Agent 决策"是 Python 代码，不是 LLM。**

L1 `run_summary.md`（第 32-36 行）也明确承认：
> "this decision was made by a deterministic heuristic standing in for a real Agnes LLM
> call inside `src/agent_runner.py`（module docstring explicitly says '此实现为可审计的启发式'）；
> it is NOT a demonstration that an LLM itself picked this method"

---

## A7. Agnes 真实拥有的选择自由度

**Agnes（LLM）目前拥有 0 选择自由度。**

- 算法选择：Python hard/easy 分支写死
- 参数（5.0/2.0 等）：Python 分支写死
- 评估（ACCEPT/RETRY）：Python 阈值判断写死
- "Agnes" 这个名字在 runner 里只是**函数名和 JSON 字段的标签**，
  实际执行的逻辑是 `if/elif/else`

---

## 归因证据路径

| 问题 | 证据路径 | 行号 |
|---|---|---|
| offset_proxy 公式 | `src/agent_runner.py` | 51 |
| 3.0 阈值 | `src/agent_runner.py` | 52 |
| hard branch 指定算法 | `src/agent_runner.py` | 60-64 |
| 函数注释承认是启发式 | `src/agent_runner.py` | 43 |
| L1 证据包确认无真实 LLM 调用 | `outputs/submission_evidence/L1/.../run_summary.md` | 32-36 |
| base_scale 定义 | `src/agent_diagnose.py` | 92-94 |
| centroid_distance 定义 | `src/agent_diagnose.py` | 71 |

---

## 结论

**当前算法选择 = C：Python/规则已决定算法，所谓 Agnes 决策是纯 Python 启发式。**
**没有真实 LLM 参与。"Agnes Agent 闭环"目前是"Python 闭环 + 模仿 Agent 输出结构"。**
