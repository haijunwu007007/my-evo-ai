#!/usr/bin/env python3
"""批量修复模块中 __module_meta__ 的 true/false/null → True/False/None"""
import os
import re

MODULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules")

def fix_booleans_in_meta(filepath: str) -> bool:
    """修复文件 __module_meta__ 块中的 true/false/null 为 Python 格式"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 定位 __module_meta__ 所在的逐行范围
    lines = content.splitlines(keepends=True)
    meta_start = None
    meta_end = None
    brace_depth = 0
    in_meta = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("__module_meta__ ="):
            meta_start = i
            in_meta = True
            # 计算第一行的 { 数量
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0 and "}" in stripped:
                meta_end = i + 1
                break
            continue

        if in_meta:
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0:
                meta_end = i + 1
                break

    if meta_start is None or meta_end is None:
        return False

    # 只修改 __module_meta__ 块中的内容
    old_block = "".join(lines[meta_start:meta_end])
    new_block = old_block

    # 替换 JSON 风格的布尔值/null 为 Python 风格
    # 注意：只在字典值位置替换，避免误改字符串内容
    # 用正则：在 : 后面跟 true/false/null
    new_block = re.sub(r':\s*true\b', ': True', new_block)
    new_block = re.sub(r':\s*false\b', ': False', new_block)
    new_block = re.sub(r':\s*null\b', ': None', new_block)
    # 也处理 , 后面的情况（如 true,）
    new_block = re.sub(r'\btrue\s*,', 'True,', new_block)
    new_block = re.sub(r'\bfalse\s*,', 'False,', new_block)
    new_block = re.sub(r'\bnull\s*,', 'None,', new_block)

    if old_block == new_block:
        return False

    lines[meta_start:meta_end] = [new_block]
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def main():
    fixed = 0
    errors = 0
    for filename in sorted(os.listdir(MODULES_DIR)):
        if not filename.endswith(".py"):
            continue
        filepath = os.path.join(MODULES_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            if fix_booleans_in_meta(filepath):
                fixed += 1
        except Exception as e:
            print(f"[ERR] {filename}: {e}")
            errors += 1

    print(f"修复完成: {fixed} 个文件, {errors} 个错误")


if __name__ == "__main__":
    main()
