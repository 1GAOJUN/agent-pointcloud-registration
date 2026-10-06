# 项目审计报告 PROJECT_AUDIT.md

项目：AGH驱动的点云自动配准智能体
根目录：D:\STUDY\darker\agent-pointcloud-registration
审计日期：2026-10-06
性质：只读审计；未修改、删除、移动、重命名任何已有项目文件；未重新运行配准实验。
证据优先级：Git 历史 / 日志 / 已有输出文件 > 文件修改时间（仅作辅助参考）。

本报告中严格区分四个状态：
A. 代码已经存在（脚本/函数可找到）
B. 实验可能运行过（存在日志、结果文件、图片等副产品，但未必全部完整）
C. 有明确证据证明实验实际运行过（有输出+指标+可对应到脚本/日志）
D. 有明确结果证明实验成功或失败（C 的基础上，且有量化 PASS/FAIL 结论）

---

## 一、仓库事实快照

### 1.1 Git 历史（当前 HEAD）
仓库存在 Git 历史，远程为 origin: https://github.com/1GAOJUN/agent-pointcloud-registration.git，main 分支。
提交记录（本地与 origin/main 同步，4 个提交）：

| 提交 | 时间 | 说明 |
|---|---|---|
| 2a5f229 | 2026-10-03 22:13 | Initial commit |
| 7da9350 | 2026-10-04 23:48 | feat: 完成造轮子和尺子（引入 make_data/evaluate/run_benchmark/configs/L1-L4/测试/outputs 初版） |
| d4c6b55 | 2026-10-04 23:56 | 完成轮子和尺子（补充 docs 工作流程总结） |
| 440dece | 2026-10-06 00:07 | L2,L3闭环（引入 algorithms/pipelines/utils 新算法与闭环、L2/L3 输出、动画、playbook 等，大量新增文件） |

当前工作区状态（git status，未提交）：
- 已修改未提交：README.md、docs/工作流程总结.md、docs/点云配准Agent参赛方案-v1.3.md，以及 outputs/L2/visuals/frames/frame_000~030.png 与 l2_registration_animation.mp4（说明这些帧/视频在 440dece 提交之后又被重新生成过，内容已变）。
- 大量未跟踪新增：data/L3、data/L3_new、docs 的 2 份新文档（v1.4 参赛方案、项目说明 v1.2）、docs/playbook_v1.0.md、docs/status.md、outputs/L3 系列 JSON/NPY、src/algorithms/l3_svd_icp_pipeline.py、outputs/L2/visuals 中 frame_031~079 与 _concat_list.txt、根目录临时文件 _coarse_sim.npy / _gen_preview.py / _tmp_check_rot.py / _tmp_eval_l3.log。

### 1.2 目录结构（排除 .git）
- configs/：L1.yaml L2.yaml L3.yaml L4.yaml
- data/：L1、L2_new、L3、L3_new
- src/：make_data.py evaluate.py run_benchmark.py visualize_all_cases.py organize_outputs.py l2_pipeline.py
- src/algorithms/：__init__.py global_registration_robust.py icp_naive.py icp_naive_new.py icp_robust_outlier.py l3_svd_icp_pipeline.py svd_global_init_new.py；quarantine/：global_registration.py icp_multistart.py
- src/pipelines/：closed_loop_l2.py __init__.py
- src/utils/：visualize_registration_animation.py
- tests/：test_regression_l1.py verify_gt.py verify_story.py test_l2_global_reg.py test_closed_loop_l2.py
- outputs/：ICP/(L1 L2 L3 L4)、L2/、reports/、以及根下 L3 系列 JSON/NPY
- docs/：AGH驱动的点云自动配准智能体_参赛方案_v1.4.md、_项目说明_v1.2.md、playbook_v1.0.md、status.md、工作流程总结.md、点云配准Agent参赛方案-v1.3.md
- quarantine/docs/：playbook_l2.md（旧版 L2 playbook，已隔离）
- 根目录临时文件：_coarse_sim.npy _gen_preview.py _tmp_check_rot.py _tmp_eval_l3.log

### 1.3 关键定义核对（L1–L4 当前 configs 事实）
以 configs/ 当前文件为准：
- L1.yaml：rot (8,-12,10) 度，translation (0.3,0.1,0.2)，noise/outlier/crop 全 0，seed 101，阈值 rot<5 度 & fitness>=0.8。
- L2.yaml：rot (75,120,150) 度，translation (0.2,0.4,0.3)，干净数据，seed 202，阈值同上。
- L3.yaml：rot (20,-25,30) 度，translation (0.4,0.2,-0.1)，noise_sigma 0.004、outlier_ratio 0.08、无裁剪，seed 303，阈值同上。
- L4.yaml：rot (10,15,-8) 度，translation (0.3,0.15,0.25)，crop_ratio 0.30（z 半空间删除 30%），干净无噪声，seed 404，阈值同上。

这与 docs/参赛方案 v1.4 与项目说明 v1.2 中“L1小角度干净 / L2大角度 / L3噪声+离群 / L4部分重叠”的定义一致。注意：status.md 提到历史上 README 曾把 L2/L3 语义写反（L2=噪声离群、L3=更大旋转），属于历史标签漂移，需人工确认以当前 configs 为准统一。

---

## 二、已识别实验 / 实验组 台账（简版，完整版见 EXPERIMENT_LEDGER.md）

证据等级：强/中/弱（定义见 EXPERIMENT_LEDGER.md）。

| ID | 实验 | 状态 | 证据等级 |
|---|---|---|---|
| E1 | 最小配准 demo（register_minimal.py） | 代码曾在提交中，但文件已在 440dece 中删除；当前目录无此文件；文档记载“旋转误差≈0.000002 度，前后截图” | 中（历史强、当前无文件） |
| E2 | 朴素 ICP 四关基线（run_benchmark.py） | 已确认运行：outputs/reports/baseline_results.csv + outputs/ICP/L1~L4 的 est/gt/meta/visuals 完整 | 强 |
| E3 | L1 回归测试（test_regression_l1.py） | 有测试脚本与 __pycache__ 编译记录（2026-10-04 21:22），文档记载跑通；独立输出未单独留证 | 中 |
| E4 | 真值自验 verify_gt.py | 有脚本+pyc（10/5 13:03），文档记载“误差1e-16量级” | 中 |
| E5 | 剧情自验 verify_story.py | 有脚本+pyc（10/4 21:22），读 CSV 判定 L1 过 L2 败 | 中 |
| E6 | evaluate.py 自测 | 强：outputs/reports/evaluate_test.txt（4 项 PASS，all_passed True，时间戳 2026-10-04 20:50:56） | 强 |
| E7 | L2 FPFH+RANSAC+ICP 对照（test_l2_global_reg.py + global_registration） | 强：outputs/ICP/L2/l2_global_registration_result.json（朴素 ICP 124.87 度/0.134 vs 实验组 rot≈0/fitness=1.0 PASS） | 强 |
| E8 | L2 闭环调度器（closed_loop_l2.py） | 强：outputs/ICP/L2/l2_closed_loop_result.json（baseline 失败→global 成功，diagnosis/switch_strategy 字段完整，总耗时 6.99s） | 强 |
| E9 | L2 SVD全局初值+ICP 流水线（l2_pipeline.py） | 强：outputs/L2/l2_registration_result.json + l2_registration_log.txt + est_transform.npy（timestamp 2026-10-05 21:20:20，PASS） | 强 |
| E10 | L2 配准动画（visualize_registration_animation.py） | 强：outputs/L2/visuals/l2_registration_animation.mp4 + frames/frame_000~079.png + _concat_list.txt | 强（帧/视频在提交后又重新生成过） |
| E11 | L3 探测（seed_303 三策略） | 强：outputs/L3_probe_existing_seed303.json（icp_naive 败 / icp_robust_outlier 败 / global_registration_robust PASS，rot 0.132 度/fitness 1.0） | 强 |
| E12 | L3 复现（seed 303/505/707 三组） | 强（有完整量化）：outputs/L3_reproduction_summary.json + L3_repro_seeds.json + 3 个 final npy；group1(seed303) PASS，group2(seed505) FAIL，group3(seed707) FAIL | 强 |
| E13 | L3 SVD+ICP 新流水线（l3_svd_icp_pipeline.py） | 仅代码存在，无对应输出 JSON/日志 | 弱 |
| E14 | L2 preview 图（_gen_preview.py） | 仅代码+空目录 outputs/L2/visuals/preview/（无 PNG）；_coarse_sim.npy 存在但无结果证明运行成功 | 弱（疑似运行，未成功/未落盘） |
| E15 | L3 临时评测（_tmp_eval_l3.log） | 日志文件存在但为 0 字节；_tmp_check_rot.py 仅临时脚本 | 无法判断 |

强证据确认运行：E2 E6 E7 E8 E9 E10 E11 E12（共 8 项）。

---

## 三、L1 / L2 / L3 / L4 单独审计

### L1
- 当前配置：configs/L1.yaml，rot(8,-12,10) 度，平移(0.3,0.1,0.2)，干净数据，seed 101。
- 已存在代码：run_benchmark.py 通用；test_regression_l1.py；make_data.default_l1_configs()（注意：默认 3 seed 带轻噪声/离群/裁剪，与 configs/L1.yaml 的“干净”不一致，二者不是同一组数据）。
- 实际跑过的实验：E2（基线，seed_101）强证据；E3 回归测试中（有 pyc 与文档记载）。
- 结果：baseline_results.csv L1 行：rot_err≈1.2e-06 度，trans≈1.7e-16，fitness=1.0，PASS。
- 图片：outputs/ICP/L1/visuals/01_initial.png、02_final_result.png；data/L1/seed_001/visualize_before.png（来自 make_data 默认 3-seed 生成）。
- 日志：baseline 结果写入 CSV（无独立 L1 日志文件）。
- playbook：无 L1 专用 playbook（playbook_v1.0.md 只覆盖 L2/L3）。
- 缺口：L1 的“Agent 识别简单场景、避免重型算法”论证（v1.4 的 P0/P1 目标）尚无独立证据；L1 正式 case 包（diagnosis/decision_trace/before-after-compare）未成形。
- 证据等级：基线强；Agent 决策层证据弱/无。

### L2
- 当前配置：configs/L2.yaml，rot(75,120,150) 度，平移(0.2,0.4,0.3)，干净，seed 202。
- 已存在代码：global_registration.py（quarantine，被 E7/E8 调用）；svd_global_init_new.py + icp_naive_new.py（l2_pipeline.py 调用）；closed_loop_l2.py；visualize_registration_animation.py；icp_naive.py。
- 实际跑过：E7 E8 E9 E10（全部强证据）。
- 结果：
  - E7 对照：朴素 ICP FAIL（rot 124.87 度/fitness 0.134）→ FPFH+RANSAC+ICP PASS（rot≈0/fitness 1.0）。
  - E8 闭环：baseline FAIL → global PASS，含 diagnosis 文本与 switch_strategy=True。
  - E9 SVD+ICP 流水线：PASS（rot 2.4e-06 度/trans 0/fitness 1.0）。
  - E10 动画：80 帧 + mp4。
- 图片：ICP/L2/visuals 2 张静态；L2/visuals/frames 80 张 + mp4。
- 日志：L2/l2_registration_log.txt；ICP/L2 两个 JSON。
- playbook：quarantine/docs/playbook_l2.md（旧，仅 L2）；docs/playbook_v1.0.md（含 L2+L3）。
- 缺口：L2 真正“无标签、无 GT、无预设答案”的 Agent 自主闭环（v1.4 P1）尚未实现——当前 E7/E8/E9 都是脚本/调度器内写死“先朴素 ICP 失败→再全局”，属于“写死条件/固定脚本”，不是模型自主判断。
- 证据等级：算法与闭环跑通强证据；Agent 自主决策无证据。

### L3
- 当前配置：configs/L3.yaml，rot(20,-25,30) 度，平移(0.4,0.2,-0.1)，noise 0.004、outlier 0.08、无裁剪，seed 303。
- 已存在代码：icp_robust_outlier.py；global_registration_robust.py；l3_svd_icp_pipeline.py（新，无输出）；icp_multistart.py（quarantine，被 playbook 推荐但当前 L3 流水线未用）。
- 实际跑过：E11（seed303 探测，强）、E12（seed303/505/707 复现，强）、E13（仅代码，弱）。
- 结果：
  - E11：icp_naive FAIL（rot 30.64 度/fitness 0.323）、icp_robust_outlier FAIL（rot 29.37 度/fitness 0.199）、global_registration_robust PASS（rot 0.132 度/fitness 1.0/ransac_fitness 1.0）。
  - E12：group1 seed303 最终 PASS（global+候选姿态检查）；group2 seed505 FAIL（选到 inverse，rot 96.58 度）；group3 seed707 FAIL（rot 22.63 度）。
- 图片：ICP/L3/visuals 2 张静态（基线 ICP 的 before/after）。无 L3 专属 after/compare 成功图。
- 日志：L3_probe/L3_reproduction JSON 内含各步指标；无独立 L3 文本日志（_tmp_eval_l3.log 为 0 字节）。
- playbook：docs/playbook_v1.0.md 覆盖 L3（推荐 icp_multistart，但实测 L3 复现用的是 global_registration_robust+候选检查，未用 multistart——存在 playbook 与实际实现不一致）。
- 缺口：L3 尚未稳定达标（seed505/707 FAIL）；playbook 推荐策略与实际实现不一致；L3 无成功 after/compare 图；l3_svd_icp_pipeline 未验证。
- 证据等级：探测/复现强证据；稳定性与 playbook 一致性弱。

### L4
- 当前配置：configs/L4.yaml，rot(10,15,-8) 度，平移(0.3,0.15,0.25)，crop_ratio 0.30（target 裁剪 30%），干净，seed 404。
- 已存在代码：仅 run_benchmark.py 通用路径会跑 L4；无 L4 专属算法/闭环。
- 实际跑过：E2 基线 L4（强证据：baseline_results.csv L4 行 + ICP/L4 全套）。
- 结果：L4 baseline FAIL（rot_err 0.0053 度 但 fitness 0.633 < 0.8，trans≈9.6e-05）。注意：L4 的旋转误差其实很小，失败仅因 fitness 未达 0.8（部分重叠导致对应点少）。
- 图片：ICP/L4/visuals 01_initial/02_final 两张。
- 日志：CSV 行（无独立 L4 日志）。
- playbook：无 L4 专用 playbook。
- 缺口：L4 无任何“补救/成功”实验（无重叠率估计、截断 ICP、兜底策略的实际运行证据）；仅有基线失败。
- 证据等级：基线强；补救/达标无证据。

---

## 四、重复、过期、幽灵成果、标签混乱

【可保留】
- outputs/ICP/L1~L4（基线全套）、outputs/reports/baseline_results.csv、evaluate_test.txt
- outputs/L2/l2_registration_result.json + log + est_transform.npy（E9 强证据）
- outputs/ICP/L2/l2_global_registration_result.json、l2_closed_loop_result.json（E7/E8）
- outputs/L3_probe_existing_seed303.json、L3_reproduction_summary.json、L3_repro_seeds.json、3 个 final npy（E11/E12）
- outputs/L2/visuals/l2_registration_animation.mp4 + frames + _concat_list.txt（E10）
- configs/L1~L4.yaml、src 核心 make_data/evaluate/run_benchmark、src/algorithms 各实现、src/pipelines/closed_loop_l2.py、src/utils/visualize_registration_animation.py
- docs/参赛方案 v1.4、项目说明 v1.2、playbook_v1.0、status.md、工作流程总结.md

【疑似过期 / 已被取代】
- outputs/ICP/L1/L1/seed_101、outputs/ICP/L2/L2/seed_202 等“Lx\Lx\seed_xxx”嵌套副本：README 明确标注“旧结构遗留副本（可删）”，是 run_benchmark 早期把 case 目录直接落到 outputs/Lx 下、后来组织成 ICP 结构后的遗留。
- quarantine/docs/playbook_l2.md：旧版 L2 专用 playbook，已被 docs/playbook_v1.0.md 取代，仍保留在 quarantine。
- src/algorithms/quarantine/{global_registration.py, icp_multistart.py}：quarantine 命名暗示被“隔离”，但 E7/E8 实际 import 的是 global_registration（quarantine 里），icp_multistart 被 playbook 推荐却未在实际 L3 流水线中调用。命名与使用情况存在混淆。

【重复】
- data/L2_new 与 data/L3_new：目录名与 data/L3 等并存。data/L2_new/L2/seed_303、seed_404（L2 参数，seed 303/404）与 configs/L2.yaml 的 seed 202 不一致（是“用 L2 参数但换了 seed 的额外数据”）。data/L3_new/L3/seed_505/seed_606 与 data/L3/seed_505/seed_707 部分重叠（seed_505 两边都有，参数一致）。存在同参数多份数据。
- outputs/L2/visuals/frames 的 frame_000~030 已在 440dece 提交进 git，frame_031~079 与 mp4 为提交后重新生成（git status 显示 modified/untracked）——同一动画存在“提交版”和“重跑版”两代帧。

【来源不明 / 未落盘】
- 根目录 _coarse_sim.npy、_gen_preview.py、_tmp_check_rot.py、_tmp_eval_l3.log：临时探索文件，_gen_preview.py 对应 outputs/L2/visuals/preview/ 但目录为空（运行未成功或未落盘）；_tmp_eval_l3.log 为 0 字节。

【需要人工确认】
- L2/L3 历史标签：status.md 指出“方案里 L2=大角度、L3=噪声离群；README 曾写反”，当前 configs 已统一为 L2=大角度、L3=噪声离群。需确认旧文档/旧图是否仍按旧标签表述。
- data/L2_new 与 configs/L2 seed 不一致，需确认 L2_new 数据用于哪次实验。
- icp_multistart 是否应作为 L3 正式策略（playbook 推荐 vs 实际跑通用 global_registration_robust）。

---

## 五、当前真实能力（不宣传未来能力）

1. 已能稳定完成：
   - 合成数据生成（make_data，含噪声/离群/裁剪退化，可复现）；
   - 四关朴素 ICP 基线 + 量化评测（旋转/平移误差、fitness、耗时，PASS/FAIL 判定）；
   - L2 大角度：FPFH+RANSAC+ICP 与 SVD全局初值+ICP 两条路线，均可从失败救到达标（强证据）；
   - L2 闭环调度器（朴素 ICP 失败→自动诊断→切换全局→复验），有结构化报告（强证据）；
   - L2 配准过程动画（80 帧+mp4）；
   - L3 脏数据探测与复现（3 策略对照 + 3 seed 复现，含候选姿态检查，量化完整）。
2. 仅在代码层存在（未确认成功运行）：
   - l3_svd_icp_pipeline.py（L3 新流水线）——无任何输出证据；
   - icp_multistart.py（L3 多初值 ICP）——playbook 推荐，但当前 L3 实际结果由 global_registration_robust 产生，multistart 无独立运行证据；
   - _gen_preview.py（L2 preview 图）——目录为空，疑似未成功；
   - G-ICP、参数自适应、点云诊断器、held-out 组合 case——文档规划中存在，仓库无代码/无运行证据。
3. 有单次成功证据、未复跑验证：
   - L2 各成功结果（E7/E8/E9）单次通过，未做多 seed 复跑（L2_new 有数据但未跑实验证据）。
   - L3 seed303 成功为单次；seed505/707 失败。
4. 已有量化结果的实验：E2（四关 CSV）、E6（evaluate 自测）、E7、E8、E9、E11、E12。
5. 已有可视化结果的实验：E2（四关 before/after 静态图）、E10（L2 动画）。
6. 当前有无真正的 Agent 自主决策：无。
   - 所有“闭环”（closed_loop_l2、l2_pipeline、L3 复现脚本）均为 Python 脚本/调度器内部写死流程（if 朴素 ICP 失败 → 调全局），不是 Agnes 模型在运行时自主判断。
   - 没有 AGH 模型调用记录 / decision trace / 工具调用链 落盘在仓库中。docs 里把“AGH 自主决策”列为目标与待办，但仓库内没有一条可验证的 Agnes 模型参与核心配准决策的证据文件。
7. 当前 Agent 决策性质：固定脚本 / 写死条件（不是模型自主判断）。
8. 参数自适应：无。所有算法参数均为硬编码固化（各 algorithms 文件 SEED/阈值写死），文档中的“参数自适应/倍率档位”尚未实现。
9. 完整闭环（诊断→决策→工具调用→反馈→验证→重试）：
   - 算法层有“执行→失败→切换→复验”的闭环（L2 closed_loop、L3 probe/repro）；
   - 但“诊断”环节缺少独立诊断工具输出，“决策”环节不是模型自主而是写死分支；GT 仍直接参与脚本评测（未做 Agent 与 Evaluator 隔离）。因此“v1.4 意义上的完整智能体闭环”未实现。
10. 最接近“完整交付”的场景：L2。
   - L2 已有：基线失败证据、两种全局补救成功、闭环调度报告、动画、playbook。最完整。但仍是“脚本固化”而非“模型自主”，且未做无标签/无 GT 的正式 Agent 闭环。

---

## 六、最大历史混乱点（Top 3）
1. L2/L3 标签漂移：status.md 与 README 历史上把 L2/L3 语义写反过，现 configs 已定死 L2=大角度、L3=噪声离群；旧文档/图可能仍按旧标签。
2. 数据目录重复且 seed 不一致：data/L2_new（seed303/404，L2 参数）、data/L3_new（seed505/606）与 data/L3（seed505/707）、configs（L1=101 L2=202 L3=303 L4=404）并存，同一关卡多份数据、多 seed，易混淆。
3. “quarantine”命名与真实使用矛盾：global_registration.py 被放在 quarantine 里却是 E7/E8 实际调用的核心算法；icp_multistart 在 quarantine 且被 playbook 推荐却未在实际 L3 流水线使用。

## 七、最大证据缺口（Top 3）
1. 无任何 Agnes/AGH 模型参与配准决策的落盘证据（无 decision trace、无工具调用链、无模型调用记录）。这是项目核心主张（“AGH 驱动自主决策”）与仓库现状之间最大的证据断层。
2. L3 未稳定达标：seed505/707 失败，且 playbook 推荐策略（icp_multistart）与实际成功策略（global_registration_robust）不一致，L3 成功仅有 seed303 单次。
3. L4 与 L1 的“Agent 能力”证据缺失：L4 仅基线失败、无补救成功实验；L1 缺少“识别简单场景、避免重型算法”的论证证据；且 v1.4 要求的多 seed 复跑、角度扫描、消融、参数自适应均无运行证据。
