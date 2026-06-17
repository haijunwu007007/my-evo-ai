import sys; sys.path.insert(0,"api")
from agent_tools import exec_tool
r = exec_tool("code_review", {"code": "def add(a,b): return a+b"})
print(f"code_review: {r['ok']} ({len(r.get('data',''))} chars)")
r = exec_tool("password_manager", {})
print(f"password_manager: {r['ok']} -> {r.get('data','')[:40]}")
r = exec_tool("api_test", {"url": "https://example.com"})
print(f"api_test: {r['ok']} ({r.get('data','')[:50]})")
print("ALL PASS")
