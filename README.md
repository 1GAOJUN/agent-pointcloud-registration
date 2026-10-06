# agent-pointcloud-registration
Agent驱动点云自动配准系统｜2026江苏省AI+科学与工程黑客松

Open3D、numpy、matplotlib


传统点云配准高度依赖人工根据点云质量选择算法、调试参数，在高噪声、低重叠等复杂场景下极易配准失败，需要人工反复试参排查。本项目基于 AGH 智能体构建全自动点云配准系统：通过感知模块提取点云特征，由大模型智能体自主决策配准策略，调用 Open3D 工具链执行 RANSAC 粗配准与 ICP 精配准；配准完成后自动评估结果，若配准失败则诊断原因并更换策略重试，实现无人工干预的闭环配准。实验表明，相比固定参数流水线，本智能体方案在困难场景下可显著提升配准成功率。

## 本地库结构

agent-pointcloud-registration\
├── README.md                        ← 门面文档：项目简介、环境配置、如何运行、快速定位任务
├── requirements.txt                 ← 依赖清单（open3d / numpy / matplotlib）
├── .gitignore                       ← 排除 __pycache__、*.pyc 等生成物
├── register_minimal.py              ← 最简 demo：球+偏移盒 → 已知变换 → ICP → 前后截图（保留作回归纪念）
├── src\                             ← 正式代码（运行环境：conda pointcloud_agh, Python 3.11）
│   ├── make_data.py                 ← 数据生成器：按 configs/L*.yaml 生成四关卡 source/target 点云、真值矩阵、meta
│   ├── evaluate.py                  ← 评测工具：旋转/平移误差、fitness 计算、内置自检与批量 case 评测
│   ├── run_benchmark.py             ← 朴素 ICP 基线主入口：加载配置 → 生成数据 → ICP → 评测 → 写 outputs/reports/baseline_results.csv
│   ├── visualize_all_cases.py       ← 批量可视化：读 outputs 与 CSV，为每关生成 visuals/01_initial.png + 02_final_result.png
│   ├── organize_outputs.py          ← outputs 整理器：把散落在 outputs/ 根目录的 before/after/evaluate_test 移入对应功能子目录
│   └── algorithms/                ← 配准算法包（均为新增，不改动上方任何核心模块）
│       ├── __init__.py            ← 算法包标识
│       └── global_registration.py ← L2 大角度全局粗配准：FPFH 特征 + RANSAC 全局匹配 + 点到面 ICP 精化（可独立运行自检）
├── configs\                         ← 四关卡参数（严格对应 make_data.LevelConfig 字段）
│   ├── L1.yaml                      ← 小角度、干净数据
│   ├── L2.yaml                      ← 更大旋转
│   ├── L3.yaml                      ← 含噪声/离群
│   └── L4.yaml                      ← 部分重叠（target 裁剪 30%）
├── data\                            ← make_data 生成数据目录（按 关卡/seed 组织）
│   ├── L1\seed_001\  └── source.ply / target.ply / gt_transform.npy / meta.json / visualize_before.png
│   ├── L1\seed_002\  └── 同上
│   ├── L1\seed_003\  └── 同上
│   ├── L1\seed_101\  └── 同上（对应 configs/L1 默认 seed）
├── outputs\                         ← 证据仓库（所有可提交/可截图的产物）
│   ├── ICP\                         ← 基线配准输出（run_benchmark）
│   │   ├── L1\est_transform.npy / gt_transform.npy / meta.json / source.ply / target.ply / visuals\01_initial.png / 02_final_result.png
│   │   ├── L2\... L3\... L4\...
│   │   ├── L2\l2_global_registration_result.json  ← L2 对照实验留证（朴素ICP vs FPFH+RANSAC+ICP，由 tests/test_l2_global_reg.py 生成）
│   │   └── Lx\Lx\seed_xxx\  ← 旧结构遗留副本（可删）
│   ├── demo_auto_registration\      ← register_minimal 的 before/after 截图
│   └── reports\                     ← 结果表与评测自测日志
│       ├── baseline_results.csv     ← 四关基准指标（L1 通过，L2/L3/L4 失败 → "失败表"故事线）
│       └── evaluate_test.txt        ← evaluate.py 自测报告
├── tests\                           ← 测试与验证（正常 / 边界 / 失败 三类）
│   ├── test_regression_l1.py        ← L1 回归测试：加载配置 + 临时目录跑 ICP，验证通过
│   ├── verify_gt.py                 ← 真值自检：证明 gt_transform 是合法刚体变换（边界验证）
│   ├── verify_story.py              ← 故事线验证：L1 必须通过、L2 必须失败（失败样例）
│   └── test_l2_global_reg.py      ← L2 大角度对照实验：读 outputs/ICP/L2 已有数据，朴素ICP vs FPFH+RANSAC+ICP，打印对比表并达标判定
└── docs\                            ← 文档、方案、日志
    ├── 点云配准Agent参赛方案-V1.2.md  ← 参赛蓝图 / 交接档案 / 评分维度映射 / 任务排期
    └── 工作流程总结.md               ← 按日工作流：环境切换、AGH 调用、Git 提交流程

## 新增文件说明（L2 大角度场景全局粗配准验证）

- `src/algorithms/__init__.py`：算法包标识，新增算法统一放入此包。
- `src/algorithms/global_registration.py`：FPFH 特征匹配 + RANSAC 全局粗配准 + 点到面 ICP 精化；输入源/目标 PLY 路径，输出最终变换矩阵、fitness、rmse、总耗时。参数全部硬编码保证可复现，可独立运行自检。
- `tests/test_l2_global_reg.py`：L2 对照实验，直接读取 `outputs/ICP/L2/` 已有 source/target/gt，做 ① 朴素ICP（单位阵初值）② RANSAC+ICP 两组对照，调用 `src/evaluate.py` 计算旋转/平移误差，打印对比表并输出达标判定，结果留证到 `outputs/ICP/L2/l2_global_registration_result.json`。

运行命令：
```
cd D:\STUDY\darker\agent-pointcloud-registration
D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\test_l2_global_reg.py
```



