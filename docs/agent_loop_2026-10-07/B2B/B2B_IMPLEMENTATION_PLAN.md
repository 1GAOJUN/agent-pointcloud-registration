# B2B_IMPLEMENTATION_PLAN

**Phase B2B — Active Observation Probe（实现前计划）**
创建：2026-10-07
状态：已确认 B2A = COMPLETE，L1/L2 数据可用（L1 seed_101 小角度，L2 seed_202 大旋转）

---

## 0. B2A 状态确认（6 项）

| # | 确认项 | 结果 |
|---|---|---|
| 1 | B2A 真实 Agnes 路径存在 | ✅ `src/agnnes_agent.py` + AGH 外层编排（subagent_fork） |
| 2 | heuristic baseline 与 real Agnes 分离 | ✅ `heuristic_decide/assess`（`@deprecated`）只在 `agent_runner.py`；主路径走 `agnnes_decide_fn`/`agnnes_assess_fn` 注入 |
| 3 | selected_method 来自真实 Agnes | ✅ `agnnes_raw_decision.json`（B2A smoke） |
| 4 | parameter_policy 来自真实 Agnes | ✅ 同上，guardrail 范围内 |
| 5 | ACCEPT/RETRY/ABORT 来自真实 Agnes | ✅ `agnnes_raw_assessment.json` |
| 6 | GT 隔离成立 | ✅ GT 仅在 `agent_evaluator.evaluate_agent_result`（Agent 停止后）；`agnnes_agent.py` 主路径无 offset_proxy 映射 |

→ B2A COMPLETE，允许进入 B2B。

## 1. 成本 profile（实测，L2 seed_202）

- 正式 LOCAL_ICP：`max_iteration=100`，wall ≈ 5.06 s（含 normal 估计）
- Probe LOCAL_ICP：`max_iteration=5`，wall ≈ 0.32 s（同 normal 估计）
- **ICP 迭代部分成本比 ≈ 16:1**；Probe 总成本 ≈ 6% 正式 ICP → 满足"明显低于正式 ICP 成本"。
- PCA Probe：numpy `eigh(3x3)`，微秒级，近零成本。

## 2. 新增文件

| 文件 | 内容 |
|---|---|
| `src/agent_probes.py` | `run_pca_orientation_probe`、`run_cheap_local_icp_probe` + `PROBE_REGISTRY` + `PROBE_DISPATCH` + `MAX_PROBES_PER_RUN=2` + `PROBE_WHITELIST` |
| `tests/test_b2b_probes.py` | 单元测试：PCA（明显非对称→HIGH/数值合理；近对称→LOW/ambiguity）、Cheap ICP（输出完整、迭代受限、不读 GT、不修改输入点云、runtime 合理） |
| `tests/_b2b_smoke_scaffold.py` | 冒烟脚手架：写 diagnosis.json + 打印 decision prompt |

## 3. 修改文件

| 文件 | 修改 |
|---|---|
| `src/agnnes_agent.py` | (a) `PROBE_WHITELIST = {"PCA_ORIENTATION","CHEAP_LOCAL_ICP","NONE"}`；(b) `PROBE_REGISTRY` 元数据 + `build_probe_prompt`（probe 白名单、成本说明、`MAX_PROBES_PER_RUN` 注入）；(c) `build_decision_prompt` 扩展 `available_probes` + output schema（`requested_probe`/`probe_reason`；`information_sufficient=true` 时 `selected_method` 必填）；(d) `validate_decision` 增加 probe 请求校验（含重复请求校验，通过 `probes_already_run` 参数）；(e) `build_assessment_prompt` 增加可选 `probe_observations` 段；(f) `AgnesDecisionAdapter.decide` 增加 `probes_already_run` 参数 |
| `tests/_b2b_smoke_scaffold.py` | 冒烟流程（diagnosis → prompt → 写盘） |

**不修改**：`agent_runner.py`（B2B 不扩展正式 runner；B2A 注入接口不变）、`agent_tools.py`（Probe 是独立工具层，不进 `TOOL_REGISTRY` 正式配准工具列表）、`agent_diagnose.py`（Probe 结果不进固定诊断，遵守 B1 禁止事项）。

## 4. Probe 注册方式

- Probe 元数据放 `PROBE_REGISTRY`（`agent_probes.py`），与 `TOOL_REGISTRY` 并列但独立：
  Probe 是"观测工具"，不是配准算法；不得混入 Agnes 的正式算法候选白名单 `ALLOWED_METHODS`。
- dispatch：`agent_probes.PROBE_DISPATCH[probe_name](...)`，仅接受白名单内的名字，其他 → error。
- 每 case 上限 `MAX_PROBES_PER_RUN = 2`（Python guardrail，合法）；**不规定 Probe 顺序**（顺序由 Agnes 选）。

## 5. Agnes 请求 Probe 的协议

decision prompt 新增：

```json
{
  "available_probes": [ {PROBE_REGISTRY 条目}, ... ],
  "probe_policy": {
    "max_probes_per_run": 2,
    "probes_already_run": [...],
    "note": "Probe 只返回可观测指标，不得假设其中含 GT；是否调用、调用哪个、先调哪个由你决定"
  },
  "output_schema": {
    "information_sufficient": "boolean",
    "requested_probe": "NONE | PCA_ORIENTATION | CHEAP_LOCAL_ICP",
    "probe_reason": "string (required when requested_probe != NONE)",
    "selected_method": "tool name, required only when information_sufficient=true",
    ...
  }
}
```

校验规则（`validate_decision`，纯 schema + 白名单，无指标阈值）：

- `requested_probe` ∈ `{NONE, PCA_ORIENTATION, CHEAP_LOCAL_ICP}`
- `information_sufficient=true` → `selected_method` ∈ `ALLOWED_METHODS` 且 `requested_probe=NONE`
- `information_sufficient=false` → `requested_probe` ≠ NONE，且不在 `probes_already_run` 中；`selected_method` 必须为 null
- `len(probes_already_run) >= MAX_PROBES_PER_RUN` → 禁止再请求（schema error，提示"probe 配额已用尽，必须选择正式方法"）

## 6. Probe 结果回灌

```
Agnes decision (information_sufficient=false, requested_probe=X)
  → Python: validate → dispatch(X) → probe_observation dict（GT-free 指标）
  → 落盘 probe_observation_01.json
  → 二次 decision prompt：diagnosis + available_probes + probes_already_run=[X]
     + probe_observations（含本次 observation）
  → Agnes 二次 decision（information_sufficient=true → selected_method + parameter_policy）
  → 正常工具执行 + Agnes assessment（ACCEPT/RETRY/ABORT）
```

## 7. 避免 Python 自动触发 Probe

- `agent_probes.py` 与 `agnnes_agent.py` 中**不存在**任何基于 diagnosis 指标（offset_proxy、
  rotation estimate、fitness 等）自动决定调用哪个 Probe 的代码。
- Probe 仅在 Agnes 输出的 `requested_probe`（经白名单 + 配额 + 去重校验）后 dispatch。
- 防伪检查（写入 05/07 文档）：注释掉 `subagent_fork` 调用路径后，Python 侧无任何代码
  能产生 `requested_probe` 值 → PASS。

## 8. PCA 歧义处理（写入 `agent_probes.py`，数值化阈值文档化）

- 采样：各取 min(N, 1000) 点（RandomState(seed=101)，与 diagnose 风格一致）
- 去均值 → 协方差（3×3）→ `np.linalg.eigh` → 特征值降序 (λ0≥λ1≥λ2)、特征向量
- anisotropy：`λ0/λ2`（各向异性比）
- 置信度分级（几何稳定性判据，不用 GT）：
  - `λ1/λ2 < 1.5` 且 `λ0/λ1 < 1.5`（近各向同性/球形）→ LOW + `ambiguity_reason="near_isotropic"`
  - `λ0/λ1 < 1.25`（主轴+次主轴接近 → 平面/近平面歧义）或 `λ1/λ2 < 1.25`（次+最小接近 → 线状/细长歧义）→ LOW + 对应 reason
  - 双接近 → 更严格阈值（均 < 1.5）仍不满足时 MEDIUM + "partial_axis_degeneracy"
  - 否则 HIGH
- rotation_estimate_deg：仅当至少一侧为 HIGH 且两侧均非 LOW 时计算。
  对目标侧每个特征向量，在源侧做符号消歧：`v ← v·(v·ref)>0 ? v : -v`（ref = 源侧当前向量，
  逐轴贪心，即"几何一致性最大"的确定性候选对齐）；再枚举 6 种轴排列，取 |trace(R)| 最大
  （= 相对旋转角最小、几何一致性最高）的 (排列, 符号组合)；记录所用方法
  （`ambiguity_handling: "per_axis_sign_greedy + permutation_argmax_trace"`）。
  任一方向 LOW → `rotation_estimate_deg=null`。

## 9. Cheap ICP Probe 参数

- 复用 `agent_tools._load/_ensure_normals`
- `max_iteration=5`，`icp_max_corr_scale=2.0`（固定，非 Agnes 可调；Probe 是固定低成本观测工具）
- 不做 Global 初始化、不做 SOR（成本最小化；正式 ICP 才做完整 pipeline）
- initial_fitness/rmse：identity 初值下同一 max_corr 的对应关系（Open3D `registration_icp`
  在第一次迭代前已可用；用一次 0 迭代的对照调用取得）；无法取得时置 null
- 输出：`probe_name, initial_fitness, probe_fitness, initial_rmse, probe_rmse,
  fitness_improvement, correspondence_count(null), iterations=5, runtime_s,
  transform_delta_magnitude`
- 不输出 rotation_error/translation_error/GT transform。

## 10. 验证与文档

1. `tests/test_b2b_probes.py` 单测（L1 非对称 / 对称构造云 / L2 cheap ICP 全项）
2. `B2B_ACTIVE_PROBE_SMOKE`：L1 seed_101（diagnosis→Agnes 决策→Probe→二次决策→工具→评估→Evaluator），
   落盘 `outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/`，不进 RUN_INDEX
3. 文档：`01_PCA_PROBE`、`02_CHEAP_ICP_PROBE`、`03_ACTIVE_PROBE_SCHEMA`、`04_TOOL_TESTS`、
   `05_ACTIVE_PROBE_SMOKE`、`06_GT_ISOLATION`、`07_REAL_AGNES_PROBE_VALIDATION`、
   `B2B_HANDOFF`、`B2B_STATE.json`
