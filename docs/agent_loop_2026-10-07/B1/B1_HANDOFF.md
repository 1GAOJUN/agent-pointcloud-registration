# B1 HANDOFF — Observation & Decision Audit（一页）

**Phase B1 完成时间：2026-10-07**
**审计范围**：`src/agent_runner.py`、`src/agent_diagnose.py`、`src/agent_tools.py`、`src/agent_evaluator.py` + L1/L2 证据包

---

## B1 结论

**Phase B1 完成（COMPLETE），未阻塞。**

核心发现：**当前系统里不存在真实 LLM 决策。**
`agnnes_decide` / `agnnes_assess` 是纯 Python 启发式，
输出结构模仿"Agent 决策"，但所有算法选择、参数、ACCEPT/RETRY 均由 Python 分支写死。

---

## 当前真正由 Agnes（LLM）控制什么

**目前：0 项。**

Agnes 模型没有被调用。所有"Agnes 决策"是 Python `if/elif/else` 的产物。
"agnes" 只是函数名和 JSON 字段标签。

---

## 当前被 heuristic / Python 控制什么

| 决策点 | 执行位置 | 具体逻辑 |
|---|---|---|
| 场景难度 | `agent_runner.py:52` | `offset_proxy < 3.0 AND 0.5 < ratio < 2.0` → easy，否则 hard |
| 算法选择 | `agent_runner.py:54-64` | easy → LOCAL_ICP，hard → GLOBAL_FPFH_RANSAC_ICP（写死字面量） |
| 参数倍率 | `agent_runner.py:56,62,72` | 各分支写死 `{5.0, 2.0}` / `{2.0}` / `{4.0, 1.5}` |
| ACCEPT/RETRY | `agent_runner.py:101-108` | `fitness >= 0.8` → ACCEPT，否则 RETRY（Python 阈值，无 LLM） |
| ABORT | **未实现** | RETRY 耗尽 max_retry=2 后循环自然结束，无 ABORT 状态 |

---

## 是否存在 GT 泄露

**PASS。**
`gt_transform.npy` 只在 `agent_evaluator.evaluate_agent_result` 里读取，
该函数在 Agent 循环结束后（ACCEPT/RETRY/ABORT）才被调用，时序正确。
`tool_call_01.json` 记录 `gt_read: false`，与代码一致。

`initial_transform_available = True` **不是 GT 泄露**——它是 LOCAL_ICP 工具
固定使用 `np.eye(4)` 初值的固有属性，与 `gt_transform.npy` 无关。
但字段命名有语义误导风险（详见 `02_INITIAL_TRANSFORM_AUDIT.md`）。

---

## 最大 Observation 缺口

**`rotation_magnitude_estimate`（NOT_IMPLEMENTED）**

当前诊断里没有旋转量估计，导致：
- L1（8° 小角度）和 L2（120° 大旋转）都被判为 hard → GLOBAL
- 两个 case 走同一 Python 分支，参数完全相同，无法证明 scenario-adaptive 决策
- 无法区分"小旋转+大平移"（LOCAL 可能够）与"大旋转+相似平移"（GLOBAL 必需）

次级缺口：`overlap_ratio`（NOT_IMPLEMENTED），L4 必需。

---

## 参数自适应真实状态

**NOT_IMPLEMENTED（Agnes 层面）。**

L1 和 L2 参数完全相同（`global_corr_scale=5.0, icp_max_corr_scale=2.0`），
原因是两个 case 都走 hard branch，而参数是 Python 字面量，不是 Agnes 选择。
"参数自适应"目前只体现在 `base_scale × scale` 的乘法结构里，
scale 本身是写死的。

---

## ACCEPT/RETRY 真实状态

**Python 阈值判断，非 Agent 决策。**

`fitness >= 0.8` → ACCEPT，完全由 `agnnes_assess` 里的 Python `if` 执行。
Agnes（LLM）没有参与。ABORT 路径未实现（循环耗尽后自然结束，无显式 ABORT 状态）。

---

## B2 最小方案

**推荐组合：Probe A（PCA Orientation）+ Probe B（Cheap Local ICP Probe）**

- Probe A：numpy PCA 估计粗旋转量，输出 `rotation_estimate_deg` + `orientation_confidence`
- Probe B：`np.eye(4)` 初值跑 5 次 ICP 迭代，输出 `probe_fitness` + `improvement` + `correspondence_count`
- 两个 Probe 代码量各约 40-50 行，合计约 90 行
- Probe 作为 Agnes 主动调用的工具，不是 Python 自动触发的固定 heuristic

B2 必须实施的前置工作：
1. 将 `agnnes_decide` / `agnnes_assess` 替换为真实 LLM 调用（保留可审计的函数签名）
2. 实现 Probe A/B 函数，注册进工具列表
3. runner 支持 Agnes 调用 Probe 的循环

---

## B2 禁止事项

- 不得在 Probe 结果到算法之间加固定阈值判断（如 `rotation > 30° → GLOBAL`）
- 不得在 Probe 里读 GT
- 不得在 `agent_diagnose.py` 的固定诊断里加 Probe 结果（Probe 是 Agnes 工具，不是诊断字段）
- 不得把 Probe B 做成与正式 `run_local_icp` 完全相同（必须是 cheap 版，`max_iteration=5`）
- 不得修改 L1/L2 Frozen 证据包

---

## B2 必须读取的文件

1. `docs/agent_loop_2026-10-07/B1/07_ARCHITECTURE.md`（目标架构 Mermaid + 确定性/Agnes 边界）
2. `docs/agent_loop_2026-10-07/B1/06_PROBE_PLAN.md`（Probe A/B 详细设计）
3. `src/agent_runner.py`（当前 `agnnes_decide` / `agnnes_assess` 实现）
4. `src/agent_tools.py`（现有工具注册表 + ICP/FPFH 代码复用参考）
5. `src/agent_diagnose.py`（PCA 实现参考，numpy 点集处理框架）
6. `docs/agent_loop_2026-10-06/PHASE_A_HANDOFF.md`（GT 隔离约束，不变）
7. `outputs/submission_evidence/L1/RUN_INDEX.csv`（L1 参考值，用于 B2 回归验证）
