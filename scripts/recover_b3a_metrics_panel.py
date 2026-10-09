"""B3A-R2 — Offline metrics_panel.png recovery using PIL (matplotlib broken in this env)."""
import json, os
from PIL import Image, ImageDraw, ImageFont

RUN_DIR = r"D:\STUDY\darker\agent-pointcloud-registration\outputs\submission_evidence\B3\L1\runs\b3_l1_20261007_seed101_blind02"

with open(os.path.join(RUN_DIR, "00_INDEX", "metrics_summary.json"), encoding="utf-8") as f:
    ms = json.load(f)
with open(os.path.join(RUN_DIR, "04_CONFIG", "parameters.json"), encoding="utf-8") as f:
    params = json.load(f)
with open(os.path.join(RUN_DIR, "02_AGENT", "agent_final_assessment.json"), encoding="utf-8") as f:
    assessment = json.load(f)
with open(os.path.join(RUN_DIR, "02_AGENT", "evaluator_result.json"), encoding="utf-8") as f:
    ev = json.load(f)

obs = ms["observable_metrics"]
gt = ms["gt_evaluator"]
policy = params.get("agnnes_multiplier", {})
final_method = params.get("final_selected_method", obs.get("tool_name", ""))

probe_chain = list(ms.get("probe_metrics", {}).keys())
probe_chain_str = " \u2192 ".join(probe_chain) if probe_chain else "(none)"

# Try to find a usable font
font_paths = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\consola.ttf",
]
def get_font(size):
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
    return ImageFont.load_default()

f_title = get_font(16)
f_bold = get_font(11)
f_normal = get_font(11)
f_small = get_font(9)
f_big = get_font(18)

# Figure size
W, H = 800, 520
img = Image.new("RGB", (W, H), "#f5f5f5")
draw = ImageDraw.Draw(img)

# Title
draw.text((20, 12), "B3A — Real Agnes + Active Probe", font=f_title, fill="#1a1a2e")
draw.line([(20, 40), (W - 20, 40)], fill="#1a1a2e", width=2)

y = 52

def section_header(text, color="#333333"):
    global y
    draw.text((20, y), text, font=f_bold, fill=color)
    draw.line([(20, y + 16), (W - 20, y + 16)], fill="#cccccc", width=1)
    y += 22

def kv(key, val, val_color="#333333"):
    global y
    draw.text((30, y), key, font=f_normal, fill="#555555")
    draw.text((260, y), val, font=f_normal, fill=val_color)
    y += 18

def blank():
    global y
    y += 6

# --- Agent Probe Path ---
section_header("Agent Probe Path")
kv("Probe chain:", probe_chain_str)
kv("Probe 1:", "PCA_ORIENTATION  |  rot_est=16.09°, conf=MEDIUM")
kv("Probe 2:", "CHEAP_LOCAL_ICP  |  fitness=0.0, transform_delta=0.0")
blank()

# --- Selected Method ---
section_header("Selected Method")
kv("Method:", final_method, val_color="#0a7a0a")
kv("Rounds:", "3 (Agnes requested probes in rounds 1-2, sufficient in round 3)")
blank()

# --- Parameter Policy ---
section_header("Parameter Policy")
kv("global_corr_scale:", str(policy.get("global_corr_scale", "N/A")))
kv("icp_max_corr_scale:", str(policy.get("icp_max_corr_scale", "N/A")))
kv("derived ransac_max_corr:", str(params.get("derived_actual_parameters", {}).get("ransac_max_corr", "N/A")))
kv("base_scale:", str(params.get("base_scale", "N/A")))
blank()

# --- Agent Final Decision ---
section_header("Agent Final Decision")
kv("Decision:", assessment.get("decision", "N/A"), val_color="#0a7a0a" if assessment.get("decision") == "ACCEPT" else "#b00020")
kv("Confidence:", str(assessment.get("confidence", "N/A")))
kv("Reason:", assessment.get("reason", "N/A"))
blank()

# Divider
draw.line([(20, y), (W - 20, y)], fill="#999999", width=2)
draw.text((W // 2 - 120, y + 2), "Gt Evaluation (Independent)", font=f_small, fill="#888888")
y += 22

# --- Agent Observable Metrics ---
section_header("Agent Observable Metrics")
kv("fitness:", str(obs.get("fitness", "N/A")))
kv("RMSE:", str(round(obs.get("rmse", 0), 6)))
kv("RANSAC fitness:", str(obs.get("ransac_fitness", "N/A")))
kv("RANSAC RMSE:", str(round(obs.get("ransac_rmse", 0), 6)))
kv("runtime:", str(round(obs.get("elapsed_s", 0), 1)) + " s")
kv("tool:", obs.get("tool_name", "N/A"))
blank()

# --- Independent GT Evaluation ---
section_header("Independent GT Evaluation")
kv("rotation error:", str(round(gt.get("rot_err_deg", 0), 4)) + " deg  (threshold " + str(gt.get("rot_thr_deg", "")) + "°)")
kv("translation error:", str(round(gt.get("trans_err", 0), 6)) + "  (threshold " + str(gt.get("trans_thr", "")) + ")")
kv("success:", str(gt.get("success")), val_color="#0a7a0a" if gt.get("success") else "#b00020")
kv("GT path:", gt.get("gt_path", "N/A"))
blank()

# --- FINAL RESULT ---
draw.line([(20, y), (W - 20, y)], fill="#0a7a0a", width=2)
draw.text((20, y + 6), "FINAL RESULT:", font=f_bold, fill="#1a1a2e")
result = "PASS" if ms.get("gt_evaluator", {}).get("success") else "FAIL"
draw.text((160, y + 2), result, font=f_big, fill="#0a7a0a" if result == "PASS" else "#b00020")
y += 28
draw.text((20, y + 4), "Run: b3_l1_20261007_seed101_blind02  |  B3A Frozen Blind  |  2026-10-07", font=f_small, fill="#888888")

out_path = os.path.join(RUN_DIR, "06_VISUALS", "metrics_panel.png")
img.save(out_path, "PNG")
print("Wrote:", out_path)
print("Size:", os.path.getsize(out_path), "bytes")
