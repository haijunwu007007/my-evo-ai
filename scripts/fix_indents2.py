"""V2: 修复async def在decorator后缩进的问题"""
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent / "api"
fixed = 0
for f in sorted(api_dir.glob("routes_*.py")):
    text = f.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    changed = False
    for i in range(len(lines) - 1):
        line = lines[i]
        if line.strip().startswith("@router."):
            next_line = lines[i + 1]
            # 检查下一行是否以4空格开头
            if next_line.startswith("    "):
                stripped = next_line[4:]
                # 处理 async def
                if stripped.startswith("async def") or stripped.startswith('"""'):
                    lines[i + 1] = stripped
                    changed = True
    if changed:
        f.write_text("".join(lines), encoding="utf-8")
        fixed += 1
        print(f"  FIXED: {f.name}")

print(f"\nFixed {fixed} files")
