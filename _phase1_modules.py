"""检查模块中有真实外部依赖的比例"""
import ast
import pathlib

base = pathlib.Path(r"D:\AUTO-EVO-AI-V0.1")

REAL_IMPORTS = {
    "requests", "aiohttp", "httpx", "urllib3",
    "sqlite3", "sqlalchemy", "psycopg2", "pymysql", "pymongo",
    "pandas", "numpy", "scipy", "sklearn", "torch", "tensorflow",
    "playwright", "selenium",
    "matplotlib", "plotly", "pillow", "PIL",
    "openpyxl", "xlrd", "python-docx", "reportlab",
    "flask", "fastapi", "django",
    "docker", "kubernetes",
    "celery", "redis", "kafka",
    "pytest",
}

module_dir = base / "modules"
results = {"real": [], "semi": [], "shallow": []}

for f in sorted(module_dir.glob("*.py")):
    if f.name.startswith("_"):
        continue
    try:
        tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        continue

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    real_imports = imports & REAL_IMPORTS

    # 统计行数
    lines = f.read_text(encoding="utf-8", errors="ignore").split("\n")
    line_count = len(lines)

    if real_imports:
        results["real"].append((f.name, line_count, real_imports))
    elif line_count > 200:
        results["semi"].append((f.name, line_count))
    else:
        results["shallow"].append((f.name, line_count))

print(f"模块总数: {len(results['real']) + len(results['semi']) + len(results['shallow'])}")
print(f"有真实外部依赖: {len(results['real'])} ({len(results['real'])/(len(results['real'])+len(results['semi'])+len(results['shallow']))*100:.1f}%)")
print(f"半真实(>200行无外部依赖): {len(results['semi'])}")
print(f"浅层(<200行无外部依赖): {len(results['shallow'])}")
print()
print("--- 有真实外部依赖的模块 ---")
for name, lines, imps in sorted(results["real"], key=lambda x: -x[1]):
    print(f"  {name:40s} {lines:>5d}行  imports: {', '.join(sorted(imps))}")
print()
print(f"--- 浅层模块前20 ---")
for name, lines in results["shallow"][:20]:
    print(f"  {name:40s} {lines:>5d}行")
if len(results["shallow"]) > 20:
    print(f"  ... 共 {len(results['shallow'])} 个")
