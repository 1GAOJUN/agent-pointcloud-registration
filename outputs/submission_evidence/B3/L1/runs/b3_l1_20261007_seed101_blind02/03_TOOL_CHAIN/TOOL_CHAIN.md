# TOOL_CHAIN — b3_l1_20261007_seed101_blind02

## 调用链

```
Basic Diagnosis (Python GT-free)
  → Agnes decision #1 (subagent_fork, agnes-3.0-flash)
      information_sufficient=false, requested_probe=PCA_ORIENTATION
  → Probe: PCA_ORIENTATION (Python agent_probes)
      observation: rot=16.09° MEDIUM, partial_axis_degeneracy
  → Agnes decision #2 (subagent_fork, agnes-3.0-flash)
      information_sufficient=false, requested_probe=CHEAP_LOCAL_ICP
  → Probe: CHEAP_LOCAL_ICP (Python agent_probes)
      observation: fitness=0.0, no correspondences at identity init
  → Agnes decision #3 (subagent_fork, agnes-3.0-flash) [quota exhausted]
      information_sufficient=true, selected_method=GLOBAL_FPFH_RANSAC_ICP
      parameter_policy={"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0}
  → Tool: GLOBAL_FPFH_RANSAC_ICP (Python agent_tools)
      fitness=1.0, rmse=0.0014233424366097808, elapsed_s=287.8276557999998
  → Agnes assessment (subagent_fork, agnes-3.0-flash)
      decision=ACCEPT, confidence=0.99
  → GT Evaluator (Python, GT read only after Agent stop)
      rot_err_deg=0.9483414645974396, trans_err=0.0008369475893995273, success=True
```

## Probe 轨迹

| Round | Probe | Key Observation |
|-------|-------|-----------------|
| 1 | PCA_ORIENTATION | rot_estimate=16.09°, MEDIUM confidence, partial_axis_degeneracy |
| 2 | CHEAP_LOCAL_ICP | initial/probe fitness=0.0, zero correspondences at identity init |

## 文件对照

| 文件 | 位置 |
|------|------|
| Agnes raw decisions | 01_AGH/agnnes_raw_decision_0(1, 2, 3).json |
| Agnes raw assessment | 01_AGH/agnnes_raw_assessment.json |
| Parsed decisions | 02_AGENT/agnnes_decision_0(1, 2, 3)_parsed.json |
| Probe observations | 02_AGENT/probe_observation_0(1, 2).json |
| Tool call record | 03_TOOL_CHAIN/tool_call_01.json |
| Observation | 02_AGENT/observation_01.json |
| Assessment | 02_AGENT/agent_final_assessment.json |
| GT evaluator result | 02_AGENT/evaluator_result.json |
| Parameters | 04_CONFIG/parameters.json |
