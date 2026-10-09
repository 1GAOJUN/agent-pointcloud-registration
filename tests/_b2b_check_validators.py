import json, sys
sys.path.insert(0, "src")
from agnnes_agent import validate_decision, MAX_PROBES_PER_RUN

cases = [
    ("A_direct_method", dict(information_sufficient=True, requested_probe="NONE",
                              selected_method="LOCAL_ICP",
                              parameter_policy={"icp_max_corr_scale": 2.5}, confidence=0.8), []),
    ("B_probe_request", dict(information_sufficient=False, requested_probe="PCA_ORIENTATION",
                             probe_reason="x", selected_method=None, confidence=0.4), []),
    ("C_duplicate_rejected", dict(information_sufficient=False, requested_probe="PCA_ORIENTATION",
                                  probe_reason="x", selected_method=None), ["PCA_ORIENTATION"]),
    ("D_quota_rejected", dict(information_sufficient=False, requested_probe="CHEAP_LOCAL_ICP",
                              probe_reason="x", selected_method=None),
     ["PCA_ORIENTATION", "CHEAP_LOCAL_ICP"]),
    ("E_second_probe_ok", dict(information_sufficient=False, requested_probe="CHEAP_LOCAL_ICP",
                               probe_reason="y", selected_method=None), ["PCA_ORIENTATION"]),
]
for name, d, done in cases:
    err = validate_decision(d, probes_already_run=done)
    print(name, "=>", "OK" if err is None else "REJECT: " + err)
print("MAX_PROBES_PER_RUN =", MAX_PROBES_PER_RUN)
