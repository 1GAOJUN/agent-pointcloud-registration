# 04_PARAMETER_AUDIT — 参数自适应真实状态审计

**Phase B1 — 只读审计。**

---

## E1. base_scale 如何计算

**位置**：`src/agent_diagnose.py` 第 92-94 行：

```python
local_scale  = src_median_spacing  # numpy KNN 中位最近邻距离（K=8，采样5000点）
global_scale = bbox_diagonal / 50.0
out["base_scale"] = float(max(local_scale, global_scale))
```

- `local_scale`：源点云中位最近邻距离（局部采样尺度）
- `global_scale`：源点云 bbox 对角线 / 50（全局物体尺度，除以 50 作为保守估计）
- `base_scale = max(两者)`

L1：`src_median_spacing ≈ 0.011133`, `bbox_diagonal/50 ≈ 0.033892` → `base_scale = 0.033892`
L2：`src_median_spacing ≈ 0.010847`, `bbox_diagonal/50 ≈ 0.033885` → `base_scale = 0.033885`

两次运行中，`global_scale`（bbox/50）都比 `local_scale` 大，因此 `base_scale` 实际由全局尺度决定。

---

## E2. `global_corr_scale = 5.0` 和 `icp_max_corr_scale = 2.0` 从哪里来

**来源：`src/agent_runner.py` 第 60-64 行，hard branch 写死的字面量。**

```python
elif not prior_attempts:   # hard branch
    selected = "GLOBAL_FPFH_RANSAC_ICP"
    policy = {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0}
```

同时 easy branch（第 56 行）里 `icp_max_corr_scale = 2.0` 也是写死字面量。
RETRY branch（第 72 行）里 `icp_max_corr_scale = 1.5` 也是写死字面量。

**这些值不是 Agnes 模型自由选择的，也不是从 Prompt 推荐读取的，
而是 Python 代码里预定义的常量。**

| 倍率 | 来源 | 说明 |
|---|---|---|
| `global_corr_scale = 5.0` | hard branch 写死 | `ransac_max_corr = base_scale × 5.0` |
| `icp_max_corr_scale = 2.0` | hard/easy branch 写死 | `icp_max_corr = base_scale × 2.0` |
| `icp_max_corr_scale = 1.5` | RETRY branch 写死 | RETRY 时收紧阈值 |
| `global_corr_scale = 4.0` | RETRY branch（切换至 GLOBAL 时）写死 | 同上 |

---

## E3. 参数归属判断

**是：Python 分支固定值（"branch 固定"）。**

不是 Agnes 自由选择，不是 Prompt 推荐，不是 Python 默认值（这些值是 hard/easy/retry
分支逻辑里写死的，不是函数参数默认值——虽然 `agent_tools.py` 里工具函数
确实有 `global_corr_scale: float = 5.0` 等默认值，但 runner 里是从 `policy` dict
显式传入的，工具默认值只是 fallback）。

---

## E4. Agnes 是否真实能够输出其他倍率

**当前架构下：否。**

`agnnes_decide` 返回的 `policy` dict 在 hard/easy/retry 分支里都是固定字面量，
没有读取任何外部输入或 LLM 输出来决定倍率数值。

若未来 Agnes 是真实 LLM，理论上它可以在 prompt 里被要求输出任意倍率，
但当前代码没有任何这样的接口——`agnnes_decide` 是一个纯 Python 函数，
不接收 LLM 输出。

---

## E5. 程序是否允许其他倍率

**程序允许（`agent_tools.py` 的函数参数是 `float`，接受任意数值），
但 Agnes 决策层（`agnnes_decide`）只输出写死的倍率。**

即：工具层没有倍率上下界约束（除 `max(1e-4, ...)` 下限保护），
但决策层只有 4 种可能的参数组合（easy/hard × RETRY或不RETRY），
每种都是字面量。

`agent_tools.py` 第 80、143、148 行有 `max(1e-4, ...)` 和 `max(1e-3, ...)` 下限，
没有上限。

---

## E6. L1 和 L2 为何参数完全相同

**因为两个 case 都走了同一个 hard branch，而 hard branch 的参数是写死字面量。**

L1 seed_101：`offset_proxy ≈ 11.1 > 3.0` → hard branch → `{5.0, 2.0}`
L2 seed_202：`offset_proxy ≈ 16.5 > 3.0` → hard branch → `{5.0, 2.0}`

两 case 的 `base_scale` 非常接近（0.03389 vs 0.033885），
因此派生的 `ransac_max_corr` 和 `icp_max_corr` 数值也几乎相同：

| 参数 | L1 | L2 |
|---|---|---|
| `base_scale` | 0.033892 | 0.033885 |
| `ransac_max_corr = base_scale × 5.0` | 0.169460 | 0.169425 |
| `icp_max_corr = base_scale × 2.0` | 0.067784 | 0.067770 |

**参数完全相同不是"自适应"的结果，而是"两个 case 走同一 Python 分支"的结果。**

---

## E7. 参数自适应状态结论

**结论：`NOT_IMPLEMENTED`**

参数看起来"自适应"（倍率 × base_scale），但：
- `base_scale` 由诊断确定（有信息量）
- 倍率由 Python 分支写死（无 Agnes 自由度）
- 不同场景（easy vs hard）对应不同倍率组合，但这完全是 Python 规则，不是 Agnes 决策

L1 和 L2 参数完全相同这一事实，
恰恰证明**参数自适应尚未实现**——
真正自适应的系统应该能根据场景不同输出不同倍率，
而不是根据"走哪个 Python 分支"输出不同倍率。

> 注：`NOT_IMPLEMENTED` 指的是 Agnes（LLM）层面的参数自适应未实现；
> Python 层面的"按分支给不同倍率"已实现，但那不是"Agent 决策"。

---

## 证据路径

| 项目 | 位置 | 行号 |
|---|---|---|
| base_scale 公式 | `src/agent_diagnose.py` | 92-94 |
| hard branch 参数 | `src/agent_runner.py` | 60-64 |
| easy branch 参数 | `src/agent_runner.py` | 54-58 |
| RETRY branch 参数 | `src/agent_runner.py` | 66-75 |
| 工具层参数接口 | `src/agent_tools.py` | 72-75, 108-111 |
| 下限保护 | `src/agent_tools.py` | 80, 143, 148 |
| L1 参数实际值 | `outputs/submission_evidence/L1/.../03_TOOL_CHAIN/observation_01.json` | — |
| L2 参数实际值 | `outputs/submission_evidence/L2/.../03_TOOL_CHAIN/observation_01.json` | — |
