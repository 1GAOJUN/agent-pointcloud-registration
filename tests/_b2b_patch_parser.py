"""One-shot patch: make agnnes_agent JSON parsing robust to BOM and surrounding prose."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "src" / "agnnes_agent.py"
src = p.read_text(encoding="utf-8")

old_dec = """    try:
        # 尝试从 raw response 中提取 JSON
        # Agnes 可能输出 ```json ... ``` 包裹
        text = raw_response.strip()
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        decision = json.loads(text)"""
new_dec = """    try:
        # 尝试从 raw response 中提取 JSON
        # Agnes 可能输出 ```json ... ``` 包裹，或带 BOM / 前后说明文字
        text = raw_response.strip().lstrip("\\ufeff")
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        if not text.startswith("{"):
            i, j = text.find("{"), text.rfind("}")
            if i >= 0 and j > i:
                text = text[i:j + 1]
        decision = json.loads(text)"""

old_ass = """    try:
        text = raw_response.strip()
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        assessment = json.loads(text)"""
new_ass = """    try:
        text = raw_response.strip().lstrip("\\ufeff")
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        if not text.startswith("{"):
            i, j = text.find("{"), text.rfind("}")
            if i >= 0 and j > i:
                text = text[i:j + 1]
        assessment = json.loads(text)"""

assert old_dec in src, "old_dec not found"
assert old_ass in src, "old_ass not found"
src = src.replace(old_dec, new_dec).replace(old_ass, new_ass)
p.write_text(src, encoding="utf-8")
print("patched OK")
