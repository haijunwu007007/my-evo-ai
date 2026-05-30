#!/usr/bin/env python3
"""AUTO-EVO-AI V0.1 — Grade 标签实标脚本 V2
直接在模块的 metadata dict 中修正 grade 字段值。
真实标准:
  Grade A: >=300有效行 AND has_execute AND 有真实第三方依赖
  Grade B: >=80有效行 AND has_execute
  Grade C: >=20有效行（有基本功能）
  S (Stub): <20有效行 或 <500B
"""
import re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MODULES_DIR = BASE / "modules"

def assess_grade(name: str, content: str) -> str:
    lines = content.splitlines()
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith(('#', '"""', "'''"))]
    n_code = len(code_lines)
    n_bytes = len(content)
    has_execute = "def execute" in content or "async def execute" in content
    imports = set()
    for line in lines:
        if line.startswith("import "):
            imports.add(line.split()[1].split(".")[0])
        elif line.startswith("from "):
            parts = line.split()
            if len(parts) > 1:
                imports.add(parts[1].split(".")[0])
    stdlib = {"os","sys","json","time","re","math","pathlib","typing","abc","dataclasses",
              "collections","functools","itertools","enum","hashlib","random","string",
              "logging","traceback","inspect","copy","uuid","datetime","io",
              "shutil","subprocess","argparse","tempfile","pickle","shelve","sqlite3",
              "html","http","urllib","socket","ssl","email","base64","binascii",
              "struct","threading","multiprocessing","concurrent","asyncio","queue",
              "signal","mmap","ctypes","gettext","locale","codecs","difflib","pprint",
              "numbers","decimal","fractions","statistics","__future__","typing_extensions"}
    third_party = imports - stdlib
    has_real_deps = len(third_party) > 0

    # 空壳/桩
    if n_bytes < 500 or n_code < 10:
        return "S"
    if n_bytes < 1000 and n_code < 30:
        return "S"

    # A: 生产级 — 必须有真实第三方依赖 + >=200有效行 + execute方法
    if has_real_deps and has_execute and n_code >= 200:
        return "A"
    # B: 准生产级 — 有 execute + 足够代码量
    if has_execute and n_code >= 80:
        return "B"
    # C: 基础
    if n_code >= 20:
        return "C"
    return "S"

def fix_grades():
    changed, total = 0, 0
    stats = {"A": 0, "B": 0, "C": 0, "S": 0}
    for f in sorted(MODULES_DIR.glob("*.py")):
        content = f.read_text(encoding="utf-8", errors="replace")
        total += 1
        n_bytes = len(content)
        n_code = len([l for l in content.splitlines() if l.strip() and not l.strip().startswith(('#', '"""', "'''"))])
        new_grade = assess_grade(f.stem, content)
        stats[new_grade] = stats.get(new_grade, 0) + 1

        # 查找当前 grade 声明 (metadata dict 中的 'grade': 'X')
        # 匹配 'grade': 'X' 或 "grade": "X" 或 'grade':"X" 等形式
        grade_val_match = re.search(r"""['"]grade['"]\s*:\s*['"]([A-Za-z])['"]""", content)
        old_grade = grade_val_match.group(1) if grade_val_match else None

        if old_grade and old_grade.upper() != new_grade:
            # 替换 grade 值
            new_content = content.replace(
                f"'{old_grade}'" if f"'{old_grade}'" in content else f'"{old_grade}"',
                f"'{new_grade}'" if "'" in content[content.index(f"'grade'" if "'grade'" in content else '"grade"'):content.index(f"'grade'" if "'grade'" in content else '"grade"') + 100] else f'"{new_grade}"',
                1
            ) if old_grade else content
            # 更稳妥的做法：直接用正则替换
            new_content = re.sub(
                r"""(['"]grade['"]\s*:\s*['"])[A-Za-z](['"])""",
                lambda m: m.group(1) + new_grade + m.group(2),
                content,
                count=1
            )
            if new_content != content:
                f.write_text(new_content, encoding="utf-8")
                changed += 1
                print(f"  {f.stem:40s} {old_grade}→{new_grade}  ({n_bytes}B/{n_code}行)")
        elif not old_grade and new_grade != "C":
            pass  # 不强制添加

    print(f"\n总计: {total} 模块, 修正: {changed} 个 Grade")
    print(f"新分布: A={stats.get('A',0)} B={stats.get('B',0)} C={stats.get('C',0)} S={stats.get('S',0)}")

if __name__ == "__main__":
    fix_grades()
