import sys, re
sys.path.insert(0, ".")
with open("api/agent_tools.py") as f:
    code = f.read()
tools = re.findall(r'@tool\("(\w+)",\s*"([^"]+)"', code)
print(f"已注册工具总数: {len(tools)}")
cats = {}
for name, cat in tools:
    cats.setdefault(cat, []).append(name)
for c, ts in sorted(cats.items()):
    print(f"  {c}: {len(ts)}")
