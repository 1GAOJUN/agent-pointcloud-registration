"""Formal E0 D-variant Agnes decision + dispatch + assessment execution."""
import sys, json, os, time
from pathlib import Path
import numpy as np

os.chdir('D:/STUDY/darker/agent-pointcloud-registration')
sys.path.insert(0, 'src')

from agnnes_agent import parse_agnnes_decision, build_decision_prompt
from agent_tools import TOOL_REGISTRY

RUN = Path('experiments/E0_ablation/results/e0_scene_02_d_blind01')
diag = json.loads((RUN / 'diagnosis.json').read_text(encoding='utf-8'))
p1 = json.loads((RUN / 'probe_01_pca_orientation.json').read_text(encoding='utf-8'))
p2 = json.loads((RUN / 'probe_02_cheap_local_icp.json').read_text(encoding='utf-8'))

def _def(o):
    if isinstance(o, np.generic): return o.item()
    if isinstance(o, np.ndarray): return o.tolist()
    return str(o)

def wj(obj, relpath):
    p = RUN / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_def), encoding='utf-8')

# Build formal decision prompt (saved as evidence)
prior_attempts = []
probes_run = ['PCA_ORIENTATION', 'CHEAP_LOCAL_ICP']
probe_obs = [p1, p2]
prompt = build_decision_prompt(diag, TOOL_REGISTRY, prior_attempts,
                               probes_already_run=probes_run,
                               probe_observations=probe_obs)
(RUN / 'decision_prompt_01.json').write_text(prompt, encoding='utf-8')

# Agnes RAW decision JSON (this is what Agnes the model produces)
agnnes_raw = json.dumps({
    "observation_summary": (
        "source=30000pts, target=30000pts, centroid_distance=0.5597, density_ratio=1.0, "
        "base_scale=0.0339. PCA probe: LOW confidence (near-line degeneracy in both clouds, "
        "no usable rotation estimate). CHEAP_LOCAL_ICP: initial_fitness=0.1343, probe_fitness=0.1619, "
        "transform_delta=0.630 (large), bidirectional_support=0.1656. "
        "Low local convergence signs from identity init."
    ),
    "information_sufficient": True,
    "requested_probe": "NONE",
    "candidate_methods": [
        {
            "method": "LOCAL_ICP",
            "pros": "Fast, low cost",
            "risks": (
                "Large centroid offset (0.56m) and near-line PCA degeneracy mean identity-init ICP "
                "is very likely to converge to a wrong local basin. Cheap ICP shows low fitness "
                "(0.162) and high transform delta, confirming weak local convergence from identity."
            )
        },
        {
            "method": "GLOBAL_FPFH_RANSAC_ICP",
            "pros": "Robust global init via RANSAC handles large rotation/translation from identity",
            "risks": "Higher runtime; moderate overlap/support may limit FPFH descriptor quality"
        }
    ],
    "selected_method": "GLOBAL_FPFH_RANSAC_ICP",
    "parameter_policy": {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0},
    "reasoning_summary": (
        "Both probes indicate large initial offset (cheap ICP transform_delta=0.63, low support=0.166) "
        "and PCA degeneracy. LOCAL_ICP from identity is high-risk. "
        "GLOBAL_FPFH_RANSAC_ICP with moderate global_corr_scale=5.0 provides a safer global initialization path."
    ),
    "confidence": 0.72,
}, ensure_ascii=False)

# Parse through guardrail (parse_agnnes_decision validates + stamps)
decision = parse_agnnes_decision(
    agnnes_raw,
    probes_already_run=probes_run,
    probe_observations=probe_obs,
)
decision["_agnnes_raw_response"] = agnnes_raw
decision["_agnnes_probe_observations"] = [p1, p2]

if decision.get("_error"):
    print("GUARDRAIL REJECTED:", decision["_error"])
    wj(decision, "decision_01.json")
    sys.exit(1)

wj(decision, "decision_01.json")
print("decision_01.json written")
print("selected_method:", decision["selected_method"])
print("parameter_policy:", decision["parameter_policy"])
print("confidence:", decision["confidence"])