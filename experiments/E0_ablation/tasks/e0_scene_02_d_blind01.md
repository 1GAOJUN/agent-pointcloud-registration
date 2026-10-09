# E0 Real Agnes Execution Task

- Project/workspace: `D:\STUDY\darker\agent-pointcloud-registration`
- Variant: `REAL_AGNES_ACTIVE_PROBE`
- Scene ID: `scene_02`
- Frozen seed metadata: `1002`
- Source: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_02\agent_input\source_cloud.ply`
- Target: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_02\agent_input\target_cloud.ply`
- Expected run ID: `e0_scene_02_d_blind01`
- Output: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\results\e0_scene_02_d_blind01`

Execute only the existing formal Active Probe entrypoints `src.agnnes_agent.build_decision_prompt` / `parse_agnnes_decision`, `src.agent_probes.dispatch_probe`, `src.agent_tools.dispatch`, and `src.agnnes_agent.build_assessment_prompt` / `agnes_assess_from_raw`. Real Agnes decides whether and which registered Active Probe to request, then chooses method, parameter policy, and ACCEPT/RETRY/ABORT under the current guardrails. Preserve every Attempt. Keep evaluator-only material inaccessible until the Agent reaches a terminal verdict.

Do not create, modify, delete, or search for code. Do not choose another entrypoint. Do not generate postprocessing scripts, images, or reports. Write only Run evidence under the exact Output directory.
