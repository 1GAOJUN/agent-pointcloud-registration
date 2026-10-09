#!/usr/bin/env python3
"""Aggregate existing E0 result JSON without running experiments."""
import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXP=ROOT/"experiments"/"E0_ablation"
FIELDS=["run_id","system_variant","scene_id","seed","selected_method","parameter_policy","probe_count","attempt_count","retry_count","agent_verdict","fitness","rmse","runtime_s","rotation_error_deg","translation_error","gt_success","false_accept","false_abort"]
def write_csv(path,rows,fields):
    with path.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
def main():
    rows=[]
    for path in sorted((EXP/"results").glob("*/result.json")):
      row=json.loads(path.read_text(encoding="utf-8"));row["parameter_policy"]=json.dumps(row.get("parameter_policy"),sort_keys=True);rows.append(row)
    write_csv(EXP/"E0_RESULTS.csv",rows,FIELDS);summary=[];cal=[]
    for variant in sorted({r["system_variant"] for r in rows}):
      g=[r for r in rows if r["system_variant"]==variant];n=len(g);fa=sum(bool(r["false_accept"]) for r in g);fb=sum(bool(r["false_abort"]) for r in g)
      summary.append({"system_variant":variant,"run_count":n,"gt_success_rate":sum(bool(r["gt_success"]) for r in g)/n,"median_rotation_error":statistics.median(float(r["rotation_error_deg"]) for r in g),"median_translation_error":statistics.median(float(r["translation_error"]) for r in g),"median_runtime":statistics.median(float(r["runtime_s"]) for r in g),"mean_probe_count":statistics.mean(float(r["probe_count"]) for r in g),"mean_retry_count":statistics.mean(float(r["retry_count"]) for r in g),"false_accept_count":fa,"false_accept_rate":fa/n,"false_abort_count":fb,"false_abort_rate":fb/n})
      cal.append({"system_variant":variant,"agent_verdict_applicable":any(r["agent_verdict"]!="NOT_APPLICABLE" for r in g),"false_accept_count":fa,"false_accept_rate":fa/n,"false_abort_count":fb,"false_abort_rate":fb/n})
    write_csv(EXP/"E0_SUMMARY.csv",summary,list(summary[0]) if summary else ["system_variant"]);write_csv(EXP/"E0_CALIBRATION.csv",cal,list(cal[0]) if cal else ["system_variant"]);print(json.dumps({"runs":len(rows),"variants":sorted({r['system_variant'] for r in rows})}));return 0
if __name__=="__main__":raise SystemExit(main())
