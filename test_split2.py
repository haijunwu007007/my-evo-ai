import sys; sys.path.insert(0,"api")
from agent_tools import exec_tool, list_tools
print(f"Total: {len(list_tools())}")
r = exec_tool("code_review", {"code": "def add(a,b): return a+b"})
print(f"code_review: ok={r.get('ok')}, len={len(r.get('data',''))}, data={r.get('data','')[:80]}")
r = exec_tool("deep_research", {"topic": "量子计算"})
print(f"deep_research: ok={r.get('ok')}, len={len(r.get('data',''))}, data={r.get('data','')[:80]}")
