"""全量检查api/目录语法错误"""
import ast
from pathlib import Path

api_dir = Path(r"D:\AUTO-EVO-AI-V0.1\api")
errors = []
for f in sorted(api_dir.rglob("*.py")):
    try:
        ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        errors.append((str(f.relative_to(api_dir.parent)), e.lineno, e.msg))

print(f"Total .py files: {len(list(api_dir.rglob('*.py')))}")
print(f"Syntax errors: {len(errors)}")
for f, line, msg in errors:
    print(f"  {f}:{line} - {msg}")
