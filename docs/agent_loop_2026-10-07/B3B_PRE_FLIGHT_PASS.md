# B3B_PRE_FLIGHT_PASS

**Phase:** B3B — Real Agnes + Active Probe, Anonymous Difficult-Pose Frozen Blind Validation
**Date:** 2026-10-07
**Status:** PASS

## Environment Confirmed

| Item | Value |
|------|-------|
| sys.executable | `D:\APP\Anaconda\envs\pointcloud_agh\python.exe` |
| Python version | 3.11.16 |
| conda env | pointcloud_agh |
| Open3D import | OK |
| Open3D version | 0.20.0 |
| NumPy | 2.4.6 |
| matplotlib | 3.11.2 |

## PLY Read Test

- Path: `D:\STUDY\darker\agent-pointcloud-registration\outputs\ICP\L2\L2\seed_202\source.ply`
- Point count: 30,000
- Read time: 0.0078 s
- Status: OK

## Agent Diagnosis Minimal Smoke

- Module: `src.agent_diagnose.diagnose`
- Input: `outputs/ICP/L2/L2/seed_202/source.ply` (source == target, smoke only)
- All expected keys present:
  - `base_scale`
  - `centroid_distance`
  - `density_ratio`
  - `initial_transform_available`
  - `noise_level`
  - `outlier_level`
  - `overlap_ratio`
  - `rotation_magnitude_estimate`
  - `sample_size`
  - `sampling_seed`
  - `source_bbox_diagonal`
  - `source_median_spacing`
  - `source_point_count`
  - `target_bbox_diagonal`
  - `target_median_spacing`
  - `target_point_count`
- Status: OK

## B3 Freeze Verification Summary

All 9 frozen file hashes recomputed and matched `B3_SYSTEM_FREEZE_MANIFEST.json`:

| File | SHA-256 (first 8) | Status |
|------|------------------|--------|
| src/agent_probes.py | B9313989… | MATCH |
| src/agnnes_agent.py | A8149C7A… | MATCH |
| src/agent_tools.py | 8B681CC2… | MATCH |
| src/agent_diagnose.py | 7C1E089E… | MATCH |
| src/agent_evaluator.py | B0A7736F… | MATCH |
| src/agent_runner.py | C567DA59… | MATCH |
| src/evaluate.py | CAF1FF7A… | MATCH |
| tests/test_b2b_probes.py | 75FEB2B8… | MATCH |
| tests/_b2b_smoke_scaffold.py | 7FED41AE… | MATCH |

B2A = COMPLETE, B2B = COMPLETE, ENV_R1 = RECOVERED → **Pre-flight PASS**
