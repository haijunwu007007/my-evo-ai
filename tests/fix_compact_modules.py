# -*- coding: utf-8 -*-
"""修复紧凑格式模块的缩进问题"""
import ast, os, sys, re
from pathlib import Path

MODULES_DIR = Path(__file__).parent.parent / "modules"
FIXES = 0

def fix_file(fpath: Path) -> bool:
    global FIXES
    content = fpath.read_text(encoding="utf-8")
    try:
        ast.parse(content)
        return False  # OK, no error
    except SyntaxError as e:
        pass

    # Fix 1: split module_class=ClassName into its own line
    content = re.sub(r'^module_class=(\w+)$', r'module_class = \1', content, flags=re.MULTILINE)
    content = re.sub(r'^(module_class = \w+);(.+)$', r'\1\n\2', content, flags=re.MULTILINE)

    # Fix 2: fix inline for/if that cause indent issues
    # Lines like: for x in y:results.append(...)
    content = re.sub(r'^(\s+)(for .+?):(\s*)([a-z_].+)$', r'\1\2:\n\1    \4', content, flags=re.MULTILINE)
    content = re.sub(r'^(\s+)(if .+?):(\s*)([a-z_].+)$', r'\1\2:\n\1    \4', content, flags=re.MULTILINE)

    # Fix 3: standalone expressions becoming indent
    content = re.sub(r'^\s+except Exception as e:\s*$', '        except Exception as e:', content, flags=re.MULTILINE)

    # Fix 4: fix closing mismatches
    content = re.sub(r"'\]\s*\):'", "']):", content)

    # Fix 5: ensure proper class body indentation
    lines = content.split("\n")
    fixed = []
    in_class = False
    class_indent = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("class ") and stripped.endswith(":"):
            in_class = True
            class_indent = len(line) - len(stripped)
            fixed.append(line)
            continue
        if in_class and stripped.startswith("def ") and stripped.endswith(":"):
            method_indent = len(line) - len(stripped)
            if method_indent != class_indent + 4:
                line = " " * (class_indent + 4) + stripped
            fixed.append(line)
            continue
        if in_class and stripped.startswith("@"):
            decorator_indent = len(line) - len(stripped)
            if decorator_indent != class_indent + 4:
                line = " " * (class_indent + 4) + stripped
            fixed.append(line)
            continue
        fixed.append(line)

    content = "\n".join(fixed)

    # Fix 6: the __module_meta__ compact formatting
    content = re.sub(r'"grade":"A"', '"grade":"A"', content)
    # Fix commas inside brackets
    content = re.sub(r',}', '}', content)
    content = re.sub(r',\]', ']', content)

    # Verify
    try:
        ast.parse(content)
        fpath.write_text(content, encoding="utf-8")
        FIXES += 1
        print(f"  ✅ {fpath.name}")
        return True
    except SyntaxError as e:
        print(f"  ❌ {fpath.name}: {e}")
        return False


def main():
    for fpath in sorted(MODULES_DIR.iterdir()):
        if fpath.suffix != ".py" or fpath.name.startswith("_"):
            continue
        try:
            ast.parse(fpath.read_text(encoding="utf-8"))
        except SyntaxError:
            fix_file(fpath)
    print(f"\n总共修复: {FIXES} 个文件")


if __name__ == "__main__":
    main()
