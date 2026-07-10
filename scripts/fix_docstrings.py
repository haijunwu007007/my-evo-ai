"""删除装饰器和async def之间的独立docstring行"""
import re
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent / "api"
fixed = 0
for f in sorted(api_dir.glob("routes_*.py")):
    text = f.read_text(encoding="utf-8", errors="replace")
    # 删除 @router.xxx(...) 和 async def 之间的 """xxx""" 独立行
    new_text = re.sub(
        r'(@router\.\w+\([^)]*\)\n)\s*""".*?"""\n',
        r'\1',
        text,
        flags=re.DOTALL
    )
    # 也处理单行情况
    new_text = re.sub(
        r'(@router\.\w+\([^)]*\))\s*""".*?"""\n',
        r'\1\n',
        new_text,
    )
    if new_text != text:
        f.write_text(new_text, encoding="utf-8")
        fixed += 1
        diff = len(text) - len(new_text)
        logger.info(f"  FIXED: {f.name} (-{diff} chars)"))

logger.info(f"\nFixed {fixed} files"))
