# L1 封箱证据包 — REPRODUCE.md

只记录仓库中**真实存在**的复现信息。缺失项一律写 UNKNOWN 或 TODO，
不做猜测（按任务要求）。

## Python 环境（已核实）
- 复现所用的 conda 环境名：`pointcloud_agh`
- 环境路径：`D:\APP\Anaconda\envs\pointcloud_agh`
- Python：3.11.16
- 该环境下实测版本（本次封箱时验证）：
  - open3d: 0.20.0
  - numpy: 2.4.6
  - matplotlib: 3.11.2
- 注意：`requirements.txt` 写的是 `numpy==1.26.4`，与当前 `pointcloud_agh`
  环境里实际装到的 numpy 2.4.6 不一致；本次 L1 运行当时用的是哪个 numpy
  版本没有落盘记录，**无法确认**，按 UNKNOWN 处理（不影响本封箱包已固化
  的结果，只影响"从零重装环境时数值是否逐位复现"这一尚未验证的问题）。

## Open3D 版本
- `requirements.txt` 固定：`open3d==0.20.0`
- 当前 `pointcloud_agh` 环境实测：`open3d.__version__ == 0.20.0`
- 结论：以 `open3d==0.20.0` 为准（requirements 固定值 + 当前环境实测值一致）

## L1 case
- 场景定义（config）：`configs/L1.yaml`
  - level: L1，n_points: 30000
  - rot_x_deg: 8.0，rot_y_deg: -12.0，rot_z_deg: 10.0
  - translation: [0.30, 0.10, 0.20]
  - noise_sigma / outlier_ratio / crop_ratio 全为 0（干净数据）
  - seed: 101
- 由 config 生成的点云（本次 run 实际使用的输入文件）：
  - source: `outputs/ICP/L1/L1/seed_101/source.ply`
  - target: `outputs/ICP/L1/L1/seed_101/target.ply`
  - GT:      `outputs/ICP/L1/L1/seed_101/gt_transform.npy`
  - 元数据:  `outputs/ICP/L1/L1/seed_101/meta.json`
- 备注：`outputs/ICP/L1/` 根目录下还有一份同内容的
  `source.ply/target.ply/gt_transform.npy/meta.json`（非 seed_101 子目录），
  本次 run 实际使用的是 `L1/L1/seed_101/` 这份（`meta.json` 与
  `evaluator_result.json` 里的 `gt_path` 都指向 `L1/L1/seed_101/`）。

## Agent Runner 入口
- 文件：`src/agent_runner.py`
- 可调用的完整闭环函数：`run_agent_case(source_ply, target_ply, run_dir, gt_npy,
  max_retry=2, agent_model_name="agnes-3.0-flash", agent_model_version="2026-10-06")`
- 命令行入口：`main()`（见下方"实际运行命令"）

## 实际运行命令
`src/agent_runner.py` 的 `main()` 用法（摘自源码注释）：
```
python src/agent_runner.py <run_id> [source_ply target_ply gt_npy]
```
本次 L1 run 使用的是默认参数分支（未传 source/target/gt 路径），即：
```
python src/agent_runner.py l1_seed_101
```
- 该命令内部默认使用 `outputs/ICP/L1/L1/seed_101/{source,target}.ply` 和
  `gt_transform.npy`，输出写到 `outputs/agent_runs/l1_seed_101/`。
- 备注：`main()` 是**入口函数定义**，本次 L1 是否真的通过这条命令触发
  （而非在某个 IDE/调试器里直接调用 `run_agent_case`）没有留痕可查，
  按 UNKNOWN 记录（不影响结果本身，只影响"触发方式"这一条信息）。

## Evaluator 运行方式
- Evaluator **不是独立命令**，而是 `run_agent_case` 内部第 5 步直接调用
  `src/agent_evaluator.py::evaluate_agent_result(final_transform, gt_npy)`，
  随后 `save_evaluator_result(...)` 落盘到
  `outputs/agent_runs/l1_seed_101/evaluator_result.json`。
- 没有独立的 `python src/agent_evaluator.py ...` 命令行入口；
  `evaluate.py.tmp`（仓库根目录，非正式代码）不是本次 run 使用的评测器。
- 阈值来源：`configs/L1.yaml` 里 `thresholds.rot_max_deg: 5.0`、
  `fitness_min: 0.8`；`translation_error` 阈值 0.05 是
  `evaluate_agent_result` 的默认参数值（`agent_evaluator.py` 源码），
  没有在 L1.yaml 里单独写死。

## 预期输出目录
运行后应生成（本次 run 实际已生成，逐文件核对一致）：
```
outputs/agent_runs/l1_seed_101/
  diagnosis.json
  input_summary.json
  decision_01.json
  tool_call_01.json
  observation_01.json
  agent_assessment_01.json
  agent_final_assessment.json
  decision_final.json
  parameters.json
  evaluator_result.json
  run_summary.md
  agh_run_log.json
  agh_evidence/   （镜像子目录，内容与主目录对应文件一致）
```

## TODO / UNKNOWN 汇总
- `main()` 是否被真实以命令行方式触发：UNKNOWN（无运行日志留痕）
- 当时实际 numpy 版本（requirements 写 1.26.4，当前环境实测 2.4.6）：
  UNKNOWN（未在本 run 证据中落盘）
- AGH 官方 raw session/execution trace：NOT_AVAILABLE（见
  `01_AGH/AGH_EVIDENCE_README.md`），本文件不做复述，仅在此提示存在此缺口
