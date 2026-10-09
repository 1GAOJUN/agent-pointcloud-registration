# Run Summary — d_unknown_20261008_s811_blind01

- Status: **COMPLETE**
- Missing core evidence: None
- Selected method: `LOCAL_ICP`
- Parameter policy: `{"icp_max_corr_scale": 2.0}`
- Derived parameters: `"UNKNOWN"`
- Fitness: `0.6525333333333333`
- RMSE: `0.011754162765814011`
- Runtime: `0.5562597000025562` s
- Agent verdict: **ABORT**
- Independent GT rotation error: `0.02960604434929143` deg
- Independent GT translation error: `0.00034075831604421`
- Final result: **True**

## Attempts

| Attempt | Method | Fitness | RMSE | Runtime (s) | Verdict | Retried |
|---:|---|---:|---:|---:|---|---|
| 1 | GLOBAL_FPFH_RANSAC_ICP | 0.616176354602098 | 0.0073373766124013905 | 127.152 | RETRY | True |

Attempt 1 parameter policy: `{"global_corr_scale": 5.0, "icp_max_corr_scale": 1.5}`
Attempt 1 derived parameters: `{"icp_max_correspondence_distance": 0.05083900452404684, "ransac_max_correspondence_distance": 0.16946334841348945}`
| 2 | LOCAL_ICP | 0.6525333333333333 | 0.011754162765814011 | 0.632 | ABORT | False |

Attempt 2 parameter policy: `{"icp_max_corr_scale": 2.0}`
Attempt 2 derived parameters: `{"max_correspondence_distance": 0.06778533936539578}`

Generated deterministically from existing Run evidence. No Agent, registration, probe, or evaluator was invoked.
