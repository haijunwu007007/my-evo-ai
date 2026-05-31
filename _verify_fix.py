# -*- coding: utf-8 -*-
"""Verify all fixes are in place"""
import re, sys, os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
base = r"D:\AUTO-EVO-AI-V0.1"
ok = True

# P0-1: /metrics
with open(f"{base}/api_server.py", encoding="utf8") as f:
    c = f.read()
m = list(re.finditer(r'@app\.get\("/metrics"', c))
print(f"P0-1: /metrics endpoints = {len(m)} (expect 1)")
if len(m) != 1:
    print("  FAIL")
    ok = False

# P0-2: hardcoded path
with open(f"{base}/core/learning_engine.py", encoding="utf8") as f:
    le = f.read()
has_hard = "D:/AUTO-EVO-AI" in le or "D:\\AUTO-EVO-AI" in le
print(f"P0-2: hardcoded path = {'FAIL' if has_hard else 'OK'}")

# P1-3: bare except
targets = [
    "api/_data_store.py", "api/routes_auth_system.py", "api/infra.py",
    "core/learning_engine.py", "core/unified_registry.py", "core/github_scanner.py"
]
total = 0
for fn in targets:
    with open(f"{base}/{fn}", encoding="utf8") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if s == "except:" or s.startswith("except:") and not s.startswith("except Exception") and not s.startswith("except BaseException"):
                total += 1
                print(f"  BARE {fn}:{i}")
print(f"P1-3: bare excepts = {total} (expect 0)")

# P1-4: dead imports
for name in ["CORSMiddleware", "HTMLResponse", "StructuredLogger"]:
    found = name in c
    print(f"P1-4: {name} = {'FAIL' if found else 'OK'}")

# P2-5: version
has_010 = '"0.1.0"' in c or "'0.1.0'" in c
print(f"P2-5: api_version 0.1.0 = {'FAIL' if has_010 else 'OK'}")

print(f"\n=== ALL {'OK' if total==0 and len(m)==1 and not has_hard and not has_010 and not ('CORSMiddleware' in c or 'HTMLResponse' in c or 'StructuredLogger' in c) else 'FAIL'} ===")
