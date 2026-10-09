# E0 Real Agnes Execution Task

- Project/workspace: `D:\STUDY\darker\agent-pointcloud-registration`
- Variant: `REAL_AGNES_NO_PROBE`
- Scene ID: `scene_03`
- Frozen seed metadata: `1003`
- Source: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_03\agent_input\source_cloud.ply`
- Target: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_03\agent_input\target_cloud.ply`
- Expected run ID: `e0_scene_03_c_blind01`
- Output: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\results\e0_scene_03_c_blind01`

Execute only `src.agent_runner.run_agent_case` with `src.agnnes_agent.AgnesDecisionAdapter` supplying the Real Agnes decision and assessment callbacks through this AGH Web session. Active Probe is disabled: `requested_probe` must be `NONE`. Real Agnes still chooses method, parameter policy, and ACCEPT/RETRY/ABORT from Basic Diagnosis and Registration Observations. Do not execute the `agent_runner.py` CLI fallback because it is the heuristic baseline. Preserve every Attempt. Keep evaluator-only material inaccessible until the Agent reaches a terminal verdict.

Do not create, modify, delete, or search for code. Do not choose another entrypoint. Do not generate postprocessing scripts, images, or reports. Write only Run evidence under the exact Output directory.
