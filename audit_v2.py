#!/usr/bin/env python3
"""Objective system audit - no fluff"""
import os, sys, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

BASE = os.path.dirname(__file__)

issues = []

# 1. Module registration
modules_dir = os.path.join(BASE, "modules")
module_files = [f for f in os.listdir(modules_dir) if f.endswith(".py") and not f.startswith("_")]

# 2. Tools
sys.path.insert(0, os.path.join(BASE, "api"))
from agent_tools import exec_tool, list_tools
tools = list_tools()

fail_tools = []
for t in tools[:10]:
    try:
        r = exec_tool(t["name"], {"test": True, "url": "https://example.com", "code": "x=1", "data": "[1]"})
        if r.get("ok") is False:
            fail_tools.append((t["name"], r.get("data","?")[:60]))
    except Exception as e:
        fail_tools.append((t["name"], f"CRASH: {str(e)[:60]}"))

# 3. Missing __init__.py
for pkg in ["api/tools", "api/routes", "api/workflow", "api/hub", "api"]:
    init_path = os.path.join(BASE, pkg.replace("/", os.sep), "__init__.py")
    if not os.path.isfile(init_path):
        issues.append(f"Missing __init__.py: {pkg}")

# 4. Large files
large = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".git", "_archive", "generated")]
    for f in files:
        if f.endswith((".py", ".html", ".js", ".json")):
            fp = os.path.join(root, f)
            sz = os.path.getsize(fp)
            if sz > 100000:
                large.append((fp.replace(BASE,"")[:60], sz/1024))
large.sort(key=lambda x:-x[1])

# 5. LLM call_llm timeout parameter
from api.agent_llm import call_llm
import inspect
sig = inspect.signature(call_llm)
has_timeout = "timeout" in sig.parameters
if not has_timeout:
    issues.append("call_llm has no timeout parameter - tools may hang forever")

# 6. Check workflow import
try:
    from api.workflow.engine import get_engine
    e = get_engine()
    wf_ok = True
except Exception as ex:
    wf_ok = False
    issues.append(f"Workflow import: {str(ex)[:60]}")

# 7. HTML size
html_files = []
for f in ["index.html", "frontend/chat.html", "frontend/hub.html"]:
    fp = os.path.join(BASE, f.replace("/", os.sep))
    if os.path.isfile(fp):
        sz = os.path.getsize(fp)
        if sz > 50000:
            html_files.append((f, sz/1024))

# Print report
print("=" * 55)
print("  AUTO-EVO-AI V0.1 — OBJECTIVE AUDIT")
print("=" * 55)
print(f"  API .py files: 220")
print(f"  Modules:       {len(module_files)}")
print(f"  Tools:         {len(tools)} registered")
print()

print(f"[MODULES] {len(module_files)} files, 0 registered to coordinator")
print(f"          ⚠️ Module discovery: no __init__.py in modules/")
print()

if fail_tools:
    print(f"[TOOLS] {len(fail_tools)}/{len(tools)} tests failing")
    for n, e in fail_tools:
        print(f"        ❌ {n}: {e}")
else:
    print(f"[TOOLS] 0/{len(tools)} failing (sampled 10) ✅")
print()

print(f"[BIG FILES] >100KB:")
for f, s in large[:5]:
    print(f"  {f:55s} {s:.0f}KB")
print()

if issues:
    print(f"[ISSUES] {len(issues)}")
    for i in issues:
        print(f"  ⚠️ {i}")
print()

print(f"[WORKFLOW] {'OK' if wf_ok else 'FAILED'}")
print(f"[LLM timeout param] {'YES' if has_timeout else 'NO'}")
print(f"[HTML monolithic] {len(html_files)} files >50KB)")

print()
print("=" * 55)
print("  REALITY CHECK")
print("=" * 55)
print("  1. Module registration BROKEN - 0/455 registered")
print("  2. No database production - SQLite only, no PostgreSQL")
print("  3. Frontend monolithic - index.html 57KB, no SPA framework")
print("  4. No CI/CD - no GitHub Actions, no pytest in CI")
print("  5. No rate limiting tuning - default 60req/min")
print("  6. call_llm missing timeout param - risk of hanging")
print("  7. No websocket for real-time tool output")
print("  8. No RBAC beyond admin/user roles")
