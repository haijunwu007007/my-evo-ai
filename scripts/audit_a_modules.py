#!/usr/bin/env python3
"""审计 Grade A 但有效代码行 <150 的模块"""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
MODULES_DIR = BASE / "modules"

results = []
for f in sorted(MODULES_DIR.glob("*.py")):
    content = f.read_text(encoding="utf-8", errors="replace")
    meta_grade = re.search(r"""['"]grade['"]\s*:\s*['"]([A-Za-z])['"]""", content)
    grade = meta_grade.group(1) if meta_grade else "?"
    if grade.upper() != "A":
        continue
    lines = content.splitlines()
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith(('#', '"""', "'''"))]
    n_code = len(code_lines)
    if n_code < 150:
        imports = []
        for line in lines:
            if line.startswith("import ") or line.startswith("from "):
                imports.append(line.strip())
        has_execute = "def execute" in content or "async def execute" in content
        results.append((f.stem, n_code, len(content), has_execute, len(imports), imports[:3]))

logger.info(f"Grade A 但 <150有效行的模块: {len(results)} 个\n"))
logger.info(f"{'模块名':35s} {'代码行':>6s} {'文件大小':>8s} {'execute':>8s} {'依赖数':>5s}"))
logger.info("-"*70))
for name, nc, sz, exe, ni, _ in results:
    logger.info(f"{name:35s} {nc:6d} {sz:8d} {'Y' if exe else 'N':>8s} {ni:5d}"))
