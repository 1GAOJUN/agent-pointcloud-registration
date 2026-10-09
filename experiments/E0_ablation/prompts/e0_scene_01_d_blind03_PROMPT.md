# E0 Formal Real Agnes Run — Self-contained Prompt

Execute one existing formal registration loop. This is an experiment run, not a development task.

- Project/workspace: `D:\STUDY\darker\agent-pointcloud-registration`
- Variant: `REAL_AGNES_ACTIVE_PROBE`
- Scene ID: `scene_01`
- Frozen seed metadata: `1001`
- Anonymous case directory: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_01\agent_input`
- Source: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_01\agent_input\source_cloud.ply`
- Target: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\cases\scene_01\agent_input\target_cloud.ply`
- Expected run ID: `e0_scene_01_d_blind03`
- Output directory: `D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\results\e0_scene_01_d_blind03`

Use the existing loop owner `src.agent_runner.run_agent_case`, with real decision and assessment callbacks supplied by this AGH/Agnes session through `src.agnnes_agent.AgnesDecisionAdapter`. Active Probe is enabled. Only Agnes may decide whether to request a registered probe, which probe to request, the registration method, parameter policy, and `ACCEPT` / `RETRY` / `ABORT`. Existing probe calls go through `src.agent_probes.dispatch_probe`; registration calls go through `src.agent_tools.dispatch`. Preserve every Attempt and the current retry guardrail.

During the Agent stage, provide only Basic Diagnosis, registered-tool descriptions, GT-free probe observations, prior attempts, and registration observations. Do not expose or read evaluator-only data, ground-truth transforms, scene type, or level labels. Only after Agnes reaches a terminal verdict may the existing independent evaluator read the evaluator-only transform and write its result.

Do not open, click, or navigate to any task file. Do not use Computer Use. Do not search for another runner or study the repository structure. Do not develop, modify code, create scripts, generate images, write reports, or fix bugs. Write only this run's core Evidence under the exact output directory. Stop immediately after the core loop and independent evaluation complete; report only the terminal verdict and Evidence path.
