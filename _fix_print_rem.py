"""修复剩余print()在非_开头的核心文件中"""
import re, pathlib

ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")

files = [
    "api/tools/code.py",
    "modules/agent_orchestrator.py",
    "modules/atom_code.py",
    "modules/openhands_agent.py",
    "modules/permission_guard.py",
    "modules/second_brain/core.py",
    "modules/soul_identity.py",
    "modules/token_budget.py",
]

for rel in files:
    fp = ROOT / rel
    if not fp.exists():
        continue
    c = fp.read_text("utf-8", errors="ignore")
    new = c
    lines = c.split("\n")
    changed = False
    for i, line in enumerate(lines):
        s = line.strip()
        if "print(" in s and "logger" not in s:
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = f"{indent}# print({s.split('print(')[1]}"
            changed = True
    if changed:
        fp.write_text("\n".join(lines), "utf-8")
        print(f"fixed: {rel}")

# 验证
pr = 0
for rel in files:
    fp = ROOT / rel
    if not fp.exists(): continue
    c = fp.read_text("utf-8", errors="ignore")
    for line in c.split("\n"):
        s = line.strip()
        if "print(" in s and "logger" not in s and not s.startswith("#"):
            pr += 1
print(f"\n剩余print() (非注释): {pr}")
