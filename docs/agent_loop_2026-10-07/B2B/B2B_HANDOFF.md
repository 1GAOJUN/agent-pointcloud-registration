# B2B_HANDOFF — Active Observation Probe（一页）

**Phase B2B 完成时间：2026-10-07**
**审计范围**：`src/agent_probes.py`（新增）、`src/agnnes_agent.py`（扩展）、
`tests/test_b2b_probes.py` + `tests/_b2b_smoke_scaffold.py`（新增）、
`outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/`

---

## B2B 结论

**Phase B2B 完成（COMPLETE），未阻塞。**

核心成果：**真实 Agnes 获得"主动获取额外专业观测信息"的能力。**
Agnes 在 Basic Diagnosis 后判断信息不足时，可自主请求 `PCA_ORIENTATION` /
`CHEAP_LOCAL_ICP` Probe；Python 只做白名单+去重+配额校验与工具调度，
**不存在任何基于诊断指标自动触发 Probe 的分支**。

---

## B2B 真正由 Agnes（LLM）控制什么

| 决策点 | 执行位置 | 说明 |
|---|---|---|
| 是否请求 Probe | `agnnes_raw_decision_NN.json` 的 `information_sufficient` + `requested_probe` | 信息不足时 Agnes 选择调哪个 Probe（或 NONE 直接进正式方法） |
| Probe 顺序 | 多轮 Agnes 决策链 | 本轮：PCA（round 1）→ CHEAP_LOCAL_ICP（round 2），由 Agnes 两轮独立决定，Python 不规定顺序 |
| 识别 Probe 低置信度 | `agnnes_raw_decision_02.json` | PCA LOW → Agnes 判"仍不足"，转请求 ICP probe |
| 配额耗尽后选正式方法 | `agnnes_raw_decision_03.json` | `LOCAL_ICP` + `icp_max_corr_scale=2.5`（Agnes 基于 Probe 观测自选） |
| ACCEPT/RETRY/ABORT | `agnnes_raw_assessment.json` | 真实 Agnes 评估（本轮 ACCEPT） |

## B2B 真正由 Python 控制什么（deterministic guardrail，非 Agnes 决策）

| 决策点 | 执行位置 | 说明 |
|---|---|---|
| Probe 白名单 | `agnnes_agent.PROBE_WHITELIST` / `agent_probes.PROBE_DISPATCH` | 只接受 `NONE/PCA_ORIENTATION/CHEAP_LOCAL_ICP` |
| Probe 去重 | `validate_decision(probes_already_run=...)` | 不得重复请求已执行 Probe |
| Probe 配额 | `MAX_PROBES_PER_RUN=2` | 合法上限，防无限探测；**不规定顺序** |
| Probe 数值计算 | `agent_probes.run_pca_orientation_probe` / `run_cheap_local_icp_probe` | 纯几何/ICP 计算，输出可观测指标，无 GT |
| Cheap ICP 固定参数 | `agent_probes._CHEAP_ICP_MAX_ITER=5`、`_CHEAP_ICP_CORR_SCALE=2.0` | 低成本约定，不随 Agnes 参数策略变化 |
| 参数范围 | `agnnes_agent.PARAMETER_RANGE`（B2A 沿用） | global_corr_scale∈[2,10]，icp_max_corr_scale∈[0.5,5] |

---

## 新增 Probe 一览

### Probe A：PCA_ORIENTATION（`agent_probes.run_pca_orientation_probe`）

纯 numpy（1000 点采样 + 3×3 协方差 eigh），<10 ms。
输出：`rotation_estimate_deg`（float 或 null）、`orientation_confidence`（HIGH/MEDIUM/LOW）、
`ambiguity_detected`、`ambiguity_reason`、`source_anisotropy`、`target_anisotropy`、
特征值、`selected_axis_permutation`、`runtime_s`。

**PCA 歧义处理（§5/§6 要求全覆盖）：**
- **sign ambiguity**：逐轴贪心符号消歧（`v ← ±v` 使与源 frame 对应轴点积最大）
- **axis permutation**：枚举 6 种排列，取 `|trace(R)|` 最大（几何一致性最高）的组合
- **对称/近对称（λ1≈λ2 或 λ2≈λ3）**：`LOW` + `near_isotropic_or_symmetric` / `near_line_degeneracy` / `near_planar_degeneracy`，`rotation_estimate_deg=null`
- **球状/近球状**：各向异性比 < 阈值 → LOW，**不硬给角度**
- 只有主轴结构足够稳定（两侧均非 LOW）才输出数值角度，并记录所用 ambiguity_handling 方法
- **不读 GT 选择候选组合**（纯几何 trace 准则）

### Probe B：CHEAP_LOCAL_ICP（`agent_probes.run_cheap_local_icp_probe`）

复用 `agent_tools._load/_ensure_normals`，identity 初值、**固定 5 次迭代**、无 Global 初始化、无 SOR。
输出：`initial_fitness`、`probe_fitness`、`initial_rmse`、`probe_rmse`、`fitness_improvement`、
`correspondence_count`（Open3D API 不暴露时置 null，不伪造）、`iterations=5`、`runtime_s`、
`transform_delta_magnitude`、`max_correspondence_distance`。
**禁止字段（不输出）**：`rotation_error`、`translation_error`、`gt_transform`。

**成本验证（§9）：** 迭代 5 vs 100（20×）；wall 0.32 s vs 5.06 s（≈16×，≈6% 正式成本）
→ Probe 确实低成本，不触发 NEEDS_REDESIGN。

---

## 集成模式（B2A 沿用 + Probe 扩展）

**AGH 外层编排**：
- Python（shell 工具）执行 diagnosis + Probe dispatch + 正式工具执行
- AGH 会话（`subagent_fork`）调用 Agnes 做 3 轮决策 + 1 轮评估
- 每轮 Agnes 原始输出落盘 `agnnes_raw_decision_NN.json` / `agnnes_raw_assessment.json`
- Probe 结果通过 `probes.observations` + `probes.already_executed` 回灌下一轮 prompt

---

## Heuristic Baseline 保留说明（§14）

`heuristic_decide()` / `heuristic_assess()` / `offset_proxy` 保留在 `src/agent_runner.py`
（`@deprecated`），B2B **未修改**该文件。真实 Agnes 主路径（`agnnes_real`）不经过
`offset_proxy >= 3 → GLOBAL` 的固定映射，也不存在任何 Python 自动 Probe 分支。

---

## GT 隔离（§16）

Probe A / B 与 Agnes 均不读 `gt_transform` / `rotation_error` / `translation_error`。
Evaluator 仅在 Agent 循环（含全部 Probe + 正式工具 + assessment）结束后运行。
冒烟证据文件 12 个 `agnnes_*.json` 关键词扫描 0 命中 → **GT 隔离 PASS**。

---

## 11 项完成标准核对（§21）

| # | 标准 | 结果 |
|---|---|---|
| 1 | PCA Probe 可调用 | ✅ `PROBE_DISPATCH["PCA_ORIENTATION"]` |
| 2 | PCA 能识别对称/低置信度 | ✅ 单测 T2/T2b + L1 冒烟（`near_line_degeneracy` → LOW/null） |
| 3 | Cheap ICP Probe 可调用 | ✅ `PROBE_DISPATCH["CHEAP_LOCAL_ICP"]` |
| 4 | Cheap ICP 确实低成本 | ✅ 迭代 5/100，wall ≈6% 正式（`_cost_profile.json`） |
| 5 | Agnes 自主决定是否调用 Probe | ✅ `agnnes_raw_decision_01` 真实 Agnes 输出 `information_sufficient=false` |
| 6 | Agnes 自主决定调用哪个 Probe | ✅ 两轮独立 Agnes 决策（PCA → ICP），Python 无顺序约束 |
| 7 | Python 没有固定 Probe 分支 | ✅ grep 全 `src/`，无指标触发的 Probe 分支 |
| 8 | Probe 结果能反馈给 Agnes | ✅ `agnnes_decision_prompt_02/03.json` 含 Probe 观测 |
| 9 | Agnes 基于新增信息重新决策 | ✅ 第 3 轮 Agnes 选 LOCAL_ICP + icp_scale=2.5（基于 ICP probe 观测） |
| 10 | GT 隔离 PASS | ✅ 关键词扫描 0 命中 + Evaluator 时序正确 |
| 11 | Active Probe Smoke Test PASS | ✅ `B2B_SMOKE_EVIDENCE.json` 10/10 项 PASS |

**全部满足 → B2B_COMPLETE**

---

## 下一步（B3 入口）

B3 进行**新 Agent 版本（含 Active Probe 能力）的正式 L1/L2 盲测**：
1. 在 L1/L2 Frozen 数据上跑完整 B2B Agent 流程（含 Probe）
2. 记录每 case 的 Probe 调用轨迹（Agnes 选了哪些 Probe、观测是什么、最终方法/参数）
3. 与 B2A 版本（无 Probe）A/B 对比场景适应性
4. **本轮 B2B 不做任何 L1/L2 正式实验**（原则 §22）

**B2A → 真实 Agnes 决策接通；B2B → 真实 Agnes 主动观测；Probe 轨迹的正式场景验证属 B3。**

---

## B2B 禁止事项（已遵守）

- 不得修改 L1/L2 Frozen 证据包 ✅
- 不得把 Probe 结果映射成固定算法选择（`rotation > X → 某算法`）✅
- 不得在 Probe 里读 GT ✅
- 不得把 Probe 结果写进 `agent_diagnose` 固定诊断字段 ✅（Probe 独立注册于 `agent_probes.py`）
- 不得把 Cheap ICP Probe 做成与正式 ICP 相同 ✅（迭代 5 vs 100）
- 不得重新跑正式 L1/L2（属 B3）✅
- 不得在 Python 里写死 Probe 顺序 ✅（Agnes 决定）

---

## 必须读取的文件（B3 入口）

1. `docs/agent_loop_2026-10-07/B2B/B2B_HANDOFF.md`（本文件）
2. `docs/agent_loop_2026-10-07/B2B/03_ACTIVE_PROBE_SCHEMA.md`（Agnes Probe 决策协议 + guardrail）
3. `docs/agent_loop_2026-10-07/B2B/05_ACTIVE_PROBE_SMOKE.md`（冒烟轨迹 + 防伪检查）
4. `docs/agent_loop_2026-10-07/B2B/07_REAL_AGNES_PROBE_VALIDATION.md`（真实 Agnes 证据）
5. `src/agent_probes.py`（两个 Probe 实现 + `PROBE_DISPATCH` + `MAX_PROBES_PER_RUN`）
6. `src/agnnes_agent.py`（`validate_decision` / `build_decision_prompt` 的 B2B 扩展）
7. `outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/`（冒烟证据包）
