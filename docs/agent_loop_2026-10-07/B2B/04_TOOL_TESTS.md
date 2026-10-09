# 04_TOOL_TESTS — B2B Probe 工具级单元测试

**Phase B2B — Active Observation Probe**
创建：2026-10-07
测试文件：`tests/test_b2b_probes.py`（8/8 PASS，2026-10-07）
结果落盘：`outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/probe_unit_test/unit_test_summary.json`

---

## 测试清单与结果

| # | 测试 | 输入 | 期望 | 结果 |
|---|---|---|---|---|
| T1 | PCA Test A：明显非对称、可稳定估计 orientation | 构造椭球（各向异性 1:0.4:0.15）绕 z 旋转 45°，source/target 各 2000 点 | `rotation_estimate_deg` 非 null 且落在 [30°,60°]（真实 45°），confidence ∈ {HIGH, MEDIUM}，无歧义 | ✅ PASS：`45.0°` HIGH，精确命中 |
| T2 | PCA Test B：近对称点云 | 球壳（各向同性，λ 近似相等） vs 椭球 | LOW confidence 或 ambiguity_detected，`rotation_estimate_deg=null`，**不得假装高置信度** | ✅ PASS：`null` LOW `near_isotropic_or_symmetric` |
| T2b | 球壳 vs 球壳（双侧各向同性） | 两个近各向同性球壳 | 同上，LOW/null | ✅ PASS |
| T3a | Cheap ICP 输出完整 | L2 seed_202 真实点云 | 10 个必需字段齐全（probe_name/initial_fitness/probe_fitness/initial_rmse/probe_rmse/fitness_improvement/correspondence_count/iterations/runtime_s/transform_delta_magnitude） | ✅ PASS：无缺失字段 |
| T3b | 迭代受限 | 同上 | `iterations == 5` | ✅ PASS |
| T3c | 不修改输入点云 | Probe 前后各读一次 source/target PLY | 点集逐点相等 | ✅ PASS |
| T3d | 不读 GT | Probe 输出字段扫描 | 无 `rotation_error`/`translation_error`/`gt_transform` 等 GT 字段 | ✅ PASS |
| T3e | runtime 合理（成本验证） | L2 上同时跑正式 `run_local_icp`(100 iter) 与 Probe(5 iter) | Probe wall < 0.5× 正式 wall 且 < 2 s | ✅ PASS：0.475 s vs 5.075 s（≈9%） |

## 结论

- **PCA Probe 能识别对称/低置信度**（Test B/Bb：LOW + null + ambiguity_reason），不伪造角度
- **PCA Probe 在稳定几何下能给出数值**（Test A：45° 精确命中，HIGH）
- **Cheap ICP Probe 确实低成本**（迭代 5 vs 100；wall ≈ 9% 正式），输出完整，不改输入，不碰 GT

## 运行方式

```
cd D:\STUDY\darker\agent-pointcloud-registration
D:\APP\Anaconda\envs\pointcloud_agh\python.exe tests\test_b2b_probes.py
```

不依赖 pytest（直接 `main()` 断言 + 汇总 JSON 落盘）。
构造点云写入 `outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/probe_unit_test/`（临时，不进 RUN_INDEX）。
