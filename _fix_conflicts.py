"""扫描并修复路由冲突"""
import pathlib, re

root = pathlib.Path('D:/AUTO-EVO-AI-V0.1')
routes_dir = root / 'api' / 'routes'

# 扫描所有路由注册
route_map = {}  # key: "METHOD path" → [(file, line)]
for f in sorted(routes_dir.rglob('*.py')):
    if '__pycache__' in str(f) or f.name == 'features/core.py':
        continue
    c = f.read_text('utf-8', errors='ignore')
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        m = re.match(r'\s*@(?:router|app)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', line)
        if m:
            key = f"{m.group(1).upper()} {m.group(2)}"
            if key not in route_map:
                route_map[key] = []
            route_map[key].append((f.name, i))

# 找冲突
conflicts = {k: v for k, v in route_map.items() if len(v) > 1}
print(f"发现 {len(conflicts)} 个路由冲突:\n")

# 按冲突文件分组
from collections import defaultdict
file_conflicts = defaultdict(list)
for route, files in sorted(conflicts.items()):
    for fn, ln in files:
        file_conflicts[fn].append((route, ln))

# 显示每个文件有多少冲突
print("按文件统计冲突数:")
for fn, routes in sorted(file_conflicts.items(), key=lambda x: -len(x[1])):
    print(f"  {len(routes):>2}个  {fn}")
    for route, ln in sorted(routes, key=lambda x: x[1]):
        print(f"       行{ln:>4}  {route}")

print("\n\n修复建议:")
print("="*60)
# routes_services.py 是最大源，看它和哪些文件冲突
if 'routes_services.py' in file_conflicts:
    svc = file_conflicts['routes_services.py']
    for route, ln in svc:
        other = [f for f, _ in conflicts[route] if f != 'routes_services.py']
        print(f"  routes_services.py 行{ln}: {route}")
        print(f"    冲突: {other}")
