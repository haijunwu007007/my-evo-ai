"""扫描 Python 文件中 await 在非 async def 中的情况"""
import re
import pathlib

base = pathlib.Path(r"D:\AUTO-EVO-AI-V0.1")
errors = []

for py_file in base.rglob("*.py"):
    try:
        text = py_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    lines = text.split("\n")
    in_async = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # 检测函数定义
        if re.match(r"^async\s+def\s+", stripped):
            in_async = True
        elif re.match(r"^\s*def\s+", stripped):
            in_async = False
        # 检测 await
        if "await " in stripped and not in_async:
            # 排除注释和字符串
            code_part = stripped
            if "#" in code_part:
                code_part = code_part.split("#")[0]
            if "await " in code_part:
                errors.append(
                    f"{py_file.relative_to(base)}:{i}: {stripped[:120]}"
                )

print(f"总扫描 .py 文件: {sum(1 for _ in base.rglob('*.py'))}")
print(f"发现 await 在非 async def 中: {len(errors)} 处")
print()
for e in errors[:30]:
    print(e)
if len(errors) > 30:
    print(f"... 共 {len(errors)} 处")
