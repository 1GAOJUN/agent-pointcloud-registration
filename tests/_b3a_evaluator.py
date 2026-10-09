"""B3A GT Evaluator（Agent 已 ACCEPT/ABORT 后才读 GT）。

- 读取 02_AGENT/observation_01.json 的 transform
- 调用 agent_evaluator.evaluate_agent_result()
- 写 02_AGENT/evaluator_result.json
"""
import sys, json
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
src_dir = ROOT / "src"
sys.path.insert(0, str(src_dir))

case = ROOT / "data" / "L1" / "seed_101"
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"
agent_dir = run_dir / "02_AGENT"

obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8"))
T_est = np.asarray(obs["transform"], dtype=np.float64)

# 仅在 Agent 已停止（ACCEPT/ABORT）后才调用
assessment = json.loads((agent_dir / "agent_final_assessment.json").read_text(encoding="utf-8"))
assert assessment["decision"] in ("ACCEPT", "ABORT"), f"Agent not stopped: {assessment['decision']}"

import numpy as _np
from agent_evaluator import evaluate_agent_result, save_evaluator_result

ev = evaluate_agent_result(_np.asarray(obs["transform"], dtype=_np.float64), str(case / "gt_transform.npy"))
agent_dir.mkdir(parents=True, exist_ok=True)
(agent_dir / "evaluator_result.json").write_text(
    json.dumps(ev, indent=2, ensure_ascii=False,
               default=lambda o: o.item() if isinstance(o, _np.generic) else o.tolist() if isinstance(o, _np.ndarray) else o),
    encoding="utf-8")
print(json.dumps(ev, indent=2, ensure_ascii=False))
