"""E0 REAL_AGNES_NO_PROBE harness bridge.

Bridges src.agent_runner.run_agent_case with AgnesDecisionAdapter
by serializing diagnosis / tool_registry / prior_attempts as text
through a subagent_fork call, parsing structured JSON back out,
and wiring the resulting decision/assess closures into run_agent_case.

Usage:
    python experiments/E0_ablation/bridges/e0_real_agnes_bridge.py <run_id> <source_ply> <target_ply> <gt_npy> <out_dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _run_agent() -> None:
    import src.agent_runner as runner
    from src.agnnes_agent import AgnesDecisionAdapter

    run_id = sys.argv[1]
    source_ply = sys.argv[2]
    target_ply = sys.argv[3]
    gt_npy = sys.argv[4]
    out_dir = sys.argv[5]

    # 1) GT-free diagnosis (Agent stage: no evaluator-only material)
    diagnosis = runner.diagnose(source_ply, target_ply)

    # 2) Build adapter — uses subagent_fork internally
    adapter = AgnesDecisionAdapter()

    def agnes_decide(diag, tools, priors):
        prompt = json.dumps({
            "diagnosis": diag,
            "tools": tools,
            "prior_attempts": priors,
        }, ensure_ascii=False, default=str)
        raw = adapter.decide(prompt)
        return raw

    def agnes_assess(obs, priors=None):
        prompt = json.dumps({
            "observation": obs,
            "prior_attempts": priors or [],
        }, ensure_ascii=False, default=str)
        return adapter.assess(prompt)

    # 3) Drive the real closed loop
    result = runner.run_agent_case(
        source_ply=source_ply,
        target_ply=target_ply,
        run_dir=out_dir,
        gt_npy=gt_npy,
        agnes_decide_fn=agnes_decide,
        agnes_assess_fn=agnes_assess,
    )

    print(json.dumps({
        "run_id": run_id,
        "variant": "REAL_AGNES_NO_PROBE",
        "attempts": result["attempts"],
        "final_decision": result["final_decision"],
        "evaluator": result["evaluator_result"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _run_agent()
