# run_summary — b3_l1_20261007_seed101_blind02

- **Run ID**: b3_l1_20261007_seed101_blind02
- **Phase**: B3A — Real Agnes + Active Probe, L1 Frozen Blind Validation
- **Anonymous Case**: case_unknown_A
- **Agnes Model**: agnes-3.0-flash
- **GH Session**: f2adfac5-8193-400e-8ba7-e7ccdb4f8476
- **Timestamp**: 2026-10-07T20:16:54

## Agent Decision Trace

| Round | information_sufficient | requested_probe | selected_method | confidence |
|-------|----------------------|-----------------|-----------------|------------|
| 1 | False | PCA_ORIENTATION | null | 0.45 |
| 2 | False | CHEAP_LOCAL_ICP | null | 0.60 |
| 3 | True | NONE | GLOBAL_FPFH_RANSAC_ICP | 0.72 |

## Probe Observations

- **PCA_ORIENTATION**: rot_estimate=16.09°, conf=MEDIUM, reason=partial_axis_degeneracy (one eigenvalue pair close; estimate usable but reduced confidence)
- **CHEAP_LOCAL_ICP**: initial_fitness=0.0, probe_fitness=0.0, transform_delta=0.0

## Final Registration

- **Method**: GLOBAL_FPFH_RANSAC_ICP
- **Policy**: {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0}
- **Fitness**: 1.0
- **RMSE**: 0.0014233424366097808
- **Elapsed**: 287.8276557999998s

## Agent Assessment

- **Decision**: ACCEPT
- **Confidence**: 0.99
- **Reason**: fitness=1.0 with RMSE 0.0014 is an essentially perfect registration; no further retry needed.

## GT Evaluator (Agent 停止后)

- **rot_err_deg**: 0.9483414645974396
- **trans_err**: 0.0008369475893995273
- **success**: True

## Run Status: **PASS**
