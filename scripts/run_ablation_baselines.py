#!/usr/bin/env python3
"""Prepare shared E0 cases/tasks and execute only non-Agnes A/B baselines."""
from __future__ import annotations
import argparse, csv, json, shutil, sys, tempfile, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from agent_diagnose import diagnose
from agent_evaluator import evaluate_agent_result
from agent_runner import heuristic_assess, heuristic_decide
from agent_tools import TOOL_REGISTRY, dispatch
from make_data import generate_case
EXP=ROOT/"experiments"/"E0_ablation"

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x),encoding="utf-8")
def scene_config(name):
    return {
      "L1":dict(level="L1",n_points=30000,rot_x_deg=8.,rot_y_deg=-12.,rot_z_deg=10.,translation=[.3,.1,.2],noise_sigma=0.,outlier_ratio=0.,crop_ratio=0.,crop_axis="z",crop_sign="+"),
      "L2":dict(level="L2",n_points=30000,rot_x_deg=75.,rot_y_deg=120.,rot_z_deg=150.,translation=[.2,.4,.3],noise_sigma=0.,outlier_ratio=0.,crop_ratio=0.,crop_axis="z",crop_sign="+"),
      "L3":dict(level="L3",n_points=30000,rot_x_deg=20.,rot_y_deg=-25.,rot_z_deg=30.,translation=[.4,.2,-.1],noise_sigma=.004,outlier_ratio=.08,crop_ratio=0.,crop_axis="z",crop_sign="+"),
      "L4":dict(level="L4",n_points=30000,rot_x_deg=10.,rot_y_deg=15.,rot_z_deg=-8.,translation=[.3,.15,.25],noise_sigma=0.,outlier_ratio=0.,crop_ratio=.30,crop_axis="z",crop_sign="+")}[name]
def prepare_case(scene):
    case=EXP/"cases"/scene["scene_id"]; src=case/"agent_input/source_cloud.ply"; tgt=case/"agent_input/target_cloud.ply"; gt=case/"evaluator_only/gt_transform.npy"
    if not all(x.is_file() for x in (src,tgt,gt)):
      with tempfile.TemporaryDirectory(prefix="e0-generate-") as temp:
        made=generate_case(scene_config(scene["config"]),int(scene["seed"]),temp); generated=Path(made["case_dir"])
        src.parent.mkdir(parents=True,exist_ok=True); gt.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(generated/"source.ply",src); shutil.copy2(generated/"target.ply",tgt); shutil.copy2(generated/"gt_transform.npy",gt)
      write(case/"evaluator_only/provenance.json",{"scene_id":scene["scene_id"],"config":scene["config"],"seed":scene["seed"],"agent_visible":False})
    return src,tgt,gt
def task_text(scene,variant,run_id):
    scene_id=scene["scene_id"]; expected=run_id
    if scene_id=="scene_01": expected=run_id.replace("blind01","blind02")
    source=EXP/"cases"/scene_id/"agent_input/source_cloud.ply"; target=EXP/"cases"/scene_id/"agent_input/target_cloud.ply"; output=EXP/"results"/expected
    if variant=="REAL_AGNES_NO_PROBE":
      entry="`src.agent_runner.run_agent_case` with `src.agnnes_agent.AgnesDecisionAdapter` supplying the Real Agnes decision and assessment callbacks through this AGH Web session"
      policy="Active Probe is disabled: `requested_probe` must be `NONE`. Real Agnes still chooses method, parameter policy, and ACCEPT/RETRY/ABORT from Basic Diagnosis and Registration Observations. Do not execute the `agent_runner.py` CLI fallback because it is the heuristic baseline."
    else:
      entry="the existing formal Active Probe entrypoints `src.agnnes_agent.build_decision_prompt` / `parse_agnnes_decision`, `src.agent_probes.dispatch_probe`, `src.agent_tools.dispatch`, and `src.agnnes_agent.build_assessment_prompt` / `agnes_assess_from_raw`"
      policy="Real Agnes decides whether and which registered Active Probe to request, then chooses method, parameter policy, and ACCEPT/RETRY/ABORT under the current guardrails."
    return f"# E0 Real Agnes Execution Task\n\n- Project/workspace: `{ROOT}`\n- Variant: `{variant}`\n- Scene ID: `{scene_id}`\n- Frozen seed metadata: `{scene['seed']}`\n- Source: `{source}`\n- Target: `{target}`\n- Expected run ID: `{expected}`\n- Output: `{output}`\n\nExecute only {entry}. {policy} Preserve every Attempt. Keep evaluator-only material inaccessible until the Agent reaches a terminal verdict.\n\nDo not create, modify, delete, or search for code. Do not choose another entrypoint. Do not generate postprocessing scripts, images, or reports. Write only Run evidence under the exact Output directory.\n"
def prepare_tasks(manifest):
    for scene in manifest["scenes"]:
      for code,variant in (("C","REAL_AGNES_NO_PROBE"),("D","REAL_AGNES_ACTIVE_PROBE")):
        run_id=f"e0_{scene['scene_id']}_{code.lower()}_blind01"; path=EXP/"tasks"/f"{run_id}.md"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(task_text(scene,variant,run_id),encoding="utf-8")
def finish(run_id,variant,scene,attempts,evaluator):
    final=attempts[-1]; row={"run_id":run_id,"system_variant":variant,"scene_id":scene["scene_id"],"seed":scene["seed"],"selected_method":final["selected_method"],"parameter_policy":final["parameter_policy"],"probe_count":0,"attempt_count":len(attempts),"retry_count":sum(a["outcome"]=="RETRY" for a in attempts),"agent_verdict":"NOT_APPLICABLE","fitness":final["fitness"],"rmse":final["rmse"],"runtime_s":sum(float(a["runtime_s"]) for a in attempts),"rotation_error_deg":evaluator["rot_err_deg"],"translation_error":evaluator["trans_err"],"gt_success":evaluator["success"],"false_accept":False,"false_abort":False}
    out=EXP/"results"/run_id; write(out/"attempts.json",attempts); write(out/"evaluator_result.json",evaluator); write(out/"result.json",row)
def run_fixed(scene,src,tgt,gt):
    run_id=f"e0_{scene['scene_id']}_a_fixed"; t=time.perf_counter(); obs=dispatch("LOCAL_ICP",str(src),str(tgt),.04,{"icp_max_corr_scale":1.0}); wall=time.perf_counter()-t
    attempt={"attempt":1,"selected_method":"LOCAL_ICP","parameter_policy":{"base_scale":.04,"icp_max_corr_scale":1.0},"fitness":obs["fitness"],"rmse":obs["rmse"],"runtime_s":wall,"outcome":"NOT_APPLICABLE"}; finish(run_id,"FIXED_PIPELINE",scene,[attempt],evaluate_agent_result(obs["transform"],str(gt)))
def run_heuristic(scene,src,tgt,gt):
    run_id=f"e0_{scene['scene_id']}_b_heuristic"; diag=diagnose(str(src),str(tgt)); attempts=[]; transform=None
    for index in range(3):
      prior=[{"selected_method":a["selected_method"],"decision":a["outcome"]} for a in attempts]; decision=heuristic_decide(diag,TOOL_REGISTRY,prior)
      t=time.perf_counter(); obs=dispatch(decision["selected_method"],str(src),str(tgt),float(diag["base_scale"]),decision["parameter_policy"]); wall=time.perf_counter()-t; assessment=heuristic_assess(obs,prior); transform=obs["transform"]
      attempts.append({"attempt":index+1,"selected_method":decision["selected_method"],"parameter_policy":decision["parameter_policy"],"fitness":obs["fitness"],"rmse":obs["rmse"],"runtime_s":wall,"outcome":assessment["decision"]})
      if assessment["decision"]!="RETRY": break
    finish(run_id,"HEURISTIC_BASELINE",scene,attempts,evaluate_agent_result(transform,str(gt)))
def write_matrix(manifest,complete):
    rows=[]
    for scene in manifest["scenes"]:
      for code,variant in manifest["variants"].items():
        suffix={"A":"a_fixed","B":"b_heuristic","C":"c_blind01","D":"d_blind01"}[code]; rows.append({"scene_id":scene["scene_id"],"seed":scene["seed"],"variant":variant,"run_id":f"e0_{scene['scene_id']}_{suffix}","status":"COMPLETE" if complete and code in "AB" else "TASK_READY" if code in "CD" else "PREPARED"})
    with (EXP/"E0_MATRIX.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--prepare-only",action="store_true");args=ap.parse_args();manifest=load(EXP/"E0_MANIFEST.json"); prepared=[(s,*prepare_case(s)) for s in manifest["scenes"]];prepare_tasks(manifest)
    if not args.prepare_only:
      for scene,src,tgt,gt in prepared: run_fixed(scene,src,tgt,gt);run_heuristic(scene,src,tgt,gt)
    write_matrix(manifest,not args.prepare_only);return 0
if __name__=="__main__":raise SystemExit(main())
