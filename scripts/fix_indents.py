"""修复所有路由文件的缩进：移除decorator后的多余缩进"""
import re
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent / "api"
fixed = 0
for f in sorted(api_dir.glob("routes_*.py")):
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 如果当前行是decorator，下一行以4空格开头且是"""或async def，则去掉缩进
        if line.strip().startswith("@") and i + 1 < len(lines):
            next_line = lines[i + 1]
            stripped_next = next_line.lstrip()
            if next_line.startswith("    ") and (stripped_next.startswith('"""') or stripped_next.startswith("async def")):
                lines[i + 1] = next_line[4:]  # 去掉4空格缩进
                fixed += 1
        new_lines.append(line)
        i += 1

    if fixed > 0:
        f.write_text("".join(new_lines), encoding="utf-8")
        logger.info(f"  FIXED: {f.name} ({fixed} changes)"))

logger.info(f"\nTotal fixed: {fixed} indentations across files"))
