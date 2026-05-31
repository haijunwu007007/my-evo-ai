"""列出所有 API 路由"""
import os, re

api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
for fname in sorted(os.listdir(api_dir)):
    if fname.startswith("routes_") and fname.endswith(".py"):
        filepath = os.path.join(api_dir, fname)
        content = open(filepath, encoding="utf-8").read()
        routes = re.findall(r'@router\.(?:get|post|put|delete)\([\'\"]([^\'\"]+)[\'\"]', content)
        print(f"\n=== {fname} ({len(routes)} routes) ===")
        for r in routes:
            print(f"  {r}")
