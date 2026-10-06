# PHASE_A_HANDOFF.md

## 项目目标
用统一 Agent 配准闭环，让 Agnes 在未知输入点云上自主完成诊断→工具选择→参数策略→结果评估→重试的决策链，并在独立 Evaluator 校验后得到可信配准结果。

## 当前阶段已完成
- 新增统一 Agent 框架四件套（GT-free）：`src/agent_tools.py`、`src/agent_diagnose.py`、`src/agent_runner.py`、`src/agent_evaluator.py`。
- 诊断工具已单独 smoke test 通过（L1 seed_101 真实数值、GT-free、NOT_IMPLEMENTED 项明确、记录 sample_size/sampling_seed）。
- L1 正式 case（seed_101）通过同一 runner 真实跑通 1 次：Agent 决策→工具调用→可观测评估 ACCEPT→独立 Evaluator 读 GT 判定 success。
- 完整证据包已落盘：`outputs/agent_runs/l1_seed_101/`。
- 修复了本轮两处失败：①Open3D 0.20.0 KDTree `search_vector_3d` 单点 KNN 不稳定，改为 numpy 向量化最近邻；②确认全部机器标识符（函数名/工具名/常量）符合 AGH 的 `^[A-Za-z_][A-Za-z0-9_]{0,63}$` 规则（E_ENVELOPE 根因是某处把中文/含连字符的 label 当成了 step/tool 机器标识符，本轮源码已全为纯 ASCII）。

## 当前架构
diagnosis(`agent_diagnose.diagnose`) → Agnes decision(`agent_runner.agnes_decide`) → dispatcher(`agent_runner` 内分发) → tool(`agent_tools.run_local_icp` / `run_global_fpfh_ransac_icp`) → observation(`observation_NN.json`) → Agnes assessment(`agent_runner.agnes_assess`) → (RETRY ≤2) → Agent 停止 → independent Evaluator(`agent_evaluator.evaluate_agent_result` 才读 GT)。

## 新增/修改文件
| 路径 | 用途 | 是否稳定 |
|---|---|---|
| src/agent_tools.py | 工具注册表 + 可参数化 ICP/全局配准包装器（GT-free） | 稳定（已过 smoke） |
| src/agent_diagnose.py | 点云结构化诊断（numpy 最近邻，GT-free） | 稳定（smoke 通过） |
| src/agent_runner.py | 统一闭环 runner（决策/重试/证据包/调度 Evaluator） | 稳定（L1 跑通） |
| src/agent_evaluator.py | 独立 GT 评测（仅在 Agent 决策后调用） | 稳定 |

本轮未修改任何既有稳定模块（`algorithms/*`、`l2_pipeline`、`make_data` 等均未动）。

## Agent 当前可选工具
- LOCAL_ICP：入口 `agent_tools.run_local_icp`；参数 `icp_max_corr_scale`（相对 base_scale 的倍率）；输出 transform/fitness/rmse/inlier_rmse/elapsed_s；限制：单位阵初值，小角度/干净/高重叠才稳。
- GLOBAL_FPFH_RANSAC_ICP：入口 `agent_tools.run_global_fpfh_ransac_icp`；参数 `global_corr_scale`、`icp_max_corr_scale`；输出 transform/fitness/rmse/ransac_fitness/ransac_rmse/elapsed_s；限制：成本高，极低重叠仍有限。
- SVD_ICP：`EXPERIMENT_ONLY`，依赖现实中不可保证的“干净且完全重叠”前提，**不提供给 Agent**。

## Agent 当前可控制参数
- `icp_max_corr_scale`：`actual = base_scale × scale`（LOCAL_ICP 与 ICP 精修段）
- `global_corr_scale`：`actual = base_scale × scale`（RANSAC 对应距离）
- `base_scale = max(source 中位最近邻间距, bbox_diagonal/50)`，由诊断给出
- 开放参数仅 2~3 个：Agent 选倍率/档位，不写绝对值。

## GT 隔离机制
- 可读 GT：仅 `agent_evaluator.evaluate_agent_result`（在 Agent 已 ACCEPT/ABORT 后由 runner 调用）。
- 绝对不能读 GT：`agent_diagnose`、`agent_tools`、`agent_runner` 的决策/评估分支（`agnes_decide`/`agnes_assess` 只接收诊断与可观测指标）。
- Agent 的 prompt 输入只含匿名化 `source_cloud`/`target_cloud` + 诊断 + 工具说明；不含磁盘路径、不含 L1/L2/L3/L4 标签。

## L1 正式运行结果
- 输入 case：`outputs/ICP/L1/L1/seed_101`（source.ply / target.ply / gt_transform.npy），configs/L1.yaml（rot 8/-12/10°, trans .3/.1/.2, 干净, seed 101）。
- diagnosis：source/target 各 30000 点，centroid_distance≈0.376，density_ratio≈1.0，base_scale≈0.0339。
- selected_method：`GLOBAL_FPFH_RANSAC_ICP`（Agent 判据：初值偏移大/密度比失衡 → 偏难场景用全局兜底）。
- selected_parameters：`{global_corr_scale:5.0, icp_max_corr_scale:2.0}`。
- 是否 retry：否（首次即 ACCEPT）。
- Agent 最终判断：ACCEPT（可观测 fitness=1.0 ≥ 0.8）。
- GT 最终指标：rot_err=0.0°, trans_err≈1.4e-17, success=True。
- 证据目录：`outputs/agent_runs/l1_seed_101/`。

## 当前遗留问题
1. L1 选了偏重型的 GLOBAL 工具而非最低成本 LOCAL_ICP——因为诊断判据把“centroid_distance 大”读成了偏难场景；这是诊断判据偏保守，属可接受但非“最省”的选择，下一轮可加“小角度快速通道”判据。
2. before/after/compare 三张图未生成（本轮未做可视化，记 TODO，不阻塞主线）。
3. `agh_run_log.json` 为可审计的模型决策链路记录（模型名/版本/时间戳/各步引用），但**不是**真实 AGH 会话日志的原始导出——真实 AGH 会话日志在 AGH 侧，需另行导出到仓库才算“官方 AGH 证据”。

## 下一阶段唯一目标
在全新 AGH 对话中，不修改总体架构，使用相同 Agent Runner，在一个未知 L2 case 上完成自主决策闭环。

## 下一阶段开始前必须阅读的文件
1. docs/agent_loop_2026-10-06/PHASE_A_STATE.json
2. docs/agent_loop_2026-10-06/PHASE_A_HANDOFF.md（本文件）
3. src/agent_runner.py（主入口与决策器）
4. src/agent_tools.py（工具注册表与可参数化入口）
5. src/agent_diagnose.py（诊断字段与 base_scale 定义）
6. configs/L2.yaml（L2 关卡定义）
7. docs/audit_2026-10-06/HANDOFF.md（全局事实与能力边界）

## 下一阶段禁止事项
- 不新增算法；不碰 L3/L4；不给 Agent 读 GT；不写死 L2→算法映射；不重做 L1 架构（复用同一 runner）；不在 Prompt 里暗示“请选 ICP”；机器标识符必须保持纯 ASCII（中文只用于显示文本）。

---

## 本次 L1 运行：会话与模型信息（证据归档补充）
- 会话 key（AGH 运行时）：49486ac2-0a14-4ea2-b46e-7ec573d4d46e
- run_id：l1_seed_101
- 实际参与决策的 Agnes 模型名：agnes-3.0-flash
- 模型版本标识：2026-10-06
- 运行时间（AGH 侧 UTC）：2026-10-06T17:31:24；GT 评测落盘 2026-10-06 17:31:28（+08:00）
- 路由/slot：account-acct-72beee64-f559-4c9c-8096-306373f6c35c / primary

## 官方 AGH 原始执行记录：NOT_AVAILABLE
- 当前 AGH 环境未提供可导出到仓库的官方会话日志 / execution record / trace /
  tool-call history（已检查 AGH 工作区与运行时用户数据目录，均无本次运行产物）。
- 因此未放入“AGH 官方原始日志”，未重写任何伪日志。
- 当前可保留的“最接近原始证据”已逐字节拷存至：
  outputs/agent_runs/l1_seed_101/agh_evidence/
  （agh_run_log.json、diagnosis_input.json、decision_01.json、tool_call_01.json、
    observation_01.json、agent_assessment_01.json、agent_final_assessment.json、
    evaluator_result.json、run_summary.md、agh_evidence_README.md）
- 该目录内含 agh_evidence_README.md：说明 NOT_AVAILABLE 的核查依据、会话/模型
  事实、GT 隔离与“Evaluator 晚于 Agent 停止”的顺序证明。
