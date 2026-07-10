"""扫描真实路由冲突 — 两个文件注册同一路由"""
import pathlib, re, json
ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1/api/routes")

# 收集所有注册路由
routes = {}  # method+path -> [files]
for f in sorted(ROOT.glob("routes_*.py")):
    name = f.name
    c = f.read_text("utf-8", errors="ignore")
    for m in re.finditer(r'@router\.(get|post|put|delete|patch|options)\(["\']([^"\']+)["\']', c):
        method, path = m.group(1).upper(), m.group(2)
        key = f"{method} {path}"
        # 标准化路径
        key_norm = key.replace("//", "/").rstrip("/") or key
        routes.setdefault(key_norm, []).append(name)

# 输出冲突
conflicts = {k: v for k, v in sorted(routes.items()) if len(v) > 1}
logger.info(f"=== 路由冲突: {len(conflicts)} 个 ==="))
for k, v in conflicts.items():
    logger.info(f"  {k}: {', '.join(v)}"))

# 核心冲突 - 两个真实路由文件冲突(排除static.py的兜底)
core_conflicts = {}
for k, v in conflicts.items():
    real = [f for f in v if "static" not in f]
    if len(real) >= 2:
        core_conflicts[k] = v
logger.info(f"\n=== 核心冲突(非兜底): {len(core_conflicts)} 个 ==="))
for k, v in core_conflicts.items():
    logger.info(f"  {k}: {', '.join(v)}"))
