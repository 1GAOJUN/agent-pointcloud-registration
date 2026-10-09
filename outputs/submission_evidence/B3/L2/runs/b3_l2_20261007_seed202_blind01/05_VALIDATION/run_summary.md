# Run Summary — b3_l2_20261007_seed202_blind01 (B3B)

## Case
- Anonymous label: **case_unknown_B**
- Data: seed_202 L2 historical data (path withheld from Agnes)
- Source/target: 30,000 points each, density ratio ≈ 1.0, centroid distance ≈ 0.559

## Agent Behavior
- **Probe chain (Agnes-chosen order):** PCA_ORIENTATION → CHEAP_LOCAL_ICP
- **PCA observation:** `rotation_estimate_deg=null`, `orientation_confidence=LOW`
  (near_line_degeneracy on both clouds — shape is roughly cylindrical/rod-like,
  transverse axes ambiguous; PCA correctly refused to emit an angle)
- **Cheap ICP probe observation:** fitness 0.137 → 0.165 after 5 identity-init
  iterations; weak improvement signals poor local basin
- **Formal method (Agnes round 3):** `GLOBAL_FPFH_RANSAC_ICP`
- **Parameter policy (Agnes):** `global_corr_scale=4.0, icp_max_corr_scale=1.0`
- **Agent final decision:** `ACCEPT` (confidence 0.97)
- **Retries:** none (1 attempt only)

## Agent-Observable Result
- fitness = 1.0
- rmse ≈ 1.63e-16
- ransac_fitness = 1.0
- runtime = 0.582 s

## Independent GT Evaluation (post-Agent-stop only)
- rotation_error_deg = **0.0**
- translation_error = **0.0**
- success = **true**

## Final Status
**PASS** (GT success=true, Agent ACCEPT, no RETRY, no leakage detected in
audit — see 05_VALIDATION/B3B_VALIDATION.md).
