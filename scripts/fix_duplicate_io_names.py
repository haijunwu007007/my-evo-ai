#!/usr/bin/env python3
"""批量修复模块 __module_meta__ 中 inputs/outputs 重复 name 问题"""

import ast
import os
import re
import sys
import json
from collections import Counter

MODULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules")


def find_meta_src_range(content: str) -> tuple:
    """
    用 AST 找到 __module_meta__ 赋值语句的行范围。
    返回 (start_line, end_line) 基于 0 的行号，或 None。
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__module_meta__":
                    if isinstance(node.value, (ast.Dict, ast.Call)):
                        # ast 的行号是从 1 开始的
                        return (node.lineno - 1, node.end_lineno)
    return None


def fix_duplicates_in_list(items: list, list_name: str) -> tuple:
    """修复列表中的重复 name，返回 (新列表, 修复计数)"""
    if not items or not isinstance(items, list):
        return items, 0

    seen = {}
    fixed = 0
    new_items = []

    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            new_items.append(item)
            continue

        name = item["name"]
        if name in seen:
            seen[name] += 1
            new_name = f"{name}_{seen[name]}"
            item = dict(item)  # 浅拷贝
            item["name"] = new_name
            fixed += 1
        else:
            seen[name] = 1

        new_items.append(item)

    return new_items, fixed


def format_meta_dict(meta_dict: dict) -> str:
    """将修复后的 dict 格式化为与原始风格接近的字符串（4空格缩进）"""
    return json.dumps(meta_dict, indent=4, ensure_ascii=False)


def replace_meta_block(content: str, start: int, end: int, new_meta_str: str) -> str:
    """替换文件内容中的 __module_meta__ 块"""
    lines = content.splitlines(keepends=True)
    old_meta = "".join(lines[start:end])

    # 保持原始的行尾缩进风格，直接替换
    # 新 meta 字符串的每一行要加上原始 __module_meta__ 块开始的缩进
    # 先计算原始第一行的缩进
    first_line = lines[start]
    indent = re.match(r"^(\s*)", first_line).group(1)
    # 第一行是 "__module_meta__ = " 开头的，不用计算缩进
    # 计算字典内容的缩进：从第二行开始
    # 原始第二行的缩进就是内容的缩进
    if end > start + 1:
        second_line = lines[start + 1]
        inner_indent = re.match(r"^(\s*)", second_line).group(1)
    else:
        inner_indent = indent + "    "

    # 格式化新 block，保持缩进一致
    lines_before = lines[:start]
    lines_after = lines[end:]

    # 输出新 meta block
    new_lines = []
    first_part = f"{indent}__module_meta__ = {new_meta_str.splitlines()[0]}\n"
    new_lines.append(first_part)
    for l in new_meta_str.splitlines()[1:]:
        new_lines.append(f"{inner_indent}{l}\n")

    return "".join(lines_before) + "".join(new_lines) + "".join(lines_after)


def process_file(filepath: str) -> dict:
    """处理单个文件，返回修改统计"""
    result = {"file": filepath, "inputs_fixed": 0, "outputs_fixed": 0}

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # 用 AST 解析
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        result["error"] = f"SyntaxError: {e}"
        return result

    # 找 __module_meta__ = {...} 的节点
    meta_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__module_meta__":
                    meta_node = node
                    break
        if meta_node:
            break

    if not meta_node:
        return result

    # 用 ast.literal_eval 解析值
    try:
        meta_dict = ast.literal_eval(meta_node.value)
    except (ValueError, SyntaxError) as e:
        result["error"] = f"literal_eval failed: {e}"
        return result

    if not isinstance(meta_dict, dict):
        return result

    # 修复 inputs
    modified = False
    if "inputs" in meta_dict:
        new_inputs, fixed_in = fix_duplicates_in_list(meta_dict["inputs"], "inputs")
        if fixed_in > 0:
            meta_dict["inputs"] = new_inputs
            result["inputs_fixed"] = fixed_in
            modified = True

    # 修复 outputs
    if "outputs" in meta_dict:
        new_outputs, fixed_out = fix_duplicates_in_list(meta_dict["outputs"], "outputs")
        if fixed_out > 0:
            meta_dict["outputs"] = new_outputs
            result["outputs_fixed"] = fixed_out
            modified = True

    if not modified:
        return result

    # 格式化为 JSON，然后替换回文件
    new_meta_str = format_meta_dict(meta_dict)

    # 用 AST 节点的行范围替换
    start_line = meta_node.lineno - 1
    end_line = meta_node.end_lineno

    new_content = replace_meta_block(content, start_line, end_line, new_meta_str)

    # 写回文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    result["modified"] = True
    return result


def main():
    stats = {
        "total": 0,
        "modified": 0,
        "skipped": 0,
        "errors": 0,
        "inputs_fixed_total": 0,
        "outputs_fixed_total": 0,
    }

    for filename in sorted(os.listdir(MODULES_DIR)):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue  # 跳过内部文件（_base, _zhipu_helper 等）

        filepath = os.path.join(MODULES_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        stats["total"] += 1
        result = process_file(filepath)

        if result.get("error"):
            logger.info(f"  [ERR] {filename}: {result['error']}"))
            stats["errors"] += 1
        elif result.get("modified"):
            logger.info(f"  [FIX] {filename}: inputs={result['inputs_fixed']}, outputs={result['outputs_fixed']}"))
            stats["modified"] += 1
            stats["inputs_fixed_total"] += result["inputs_fixed"]
            stats["outputs_fixed_total"] += result["outputs_fixed"]
        else:
            stats["skipped"] += 1

    logger.info(f"\n=== 修复统计 ==="))
    logger.info(f"总文件数:     {stats['total']}"))
    logger.info(f"已修复:       {stats['modified']}"))
    logger.info(f"跳过(无问题): {stats['skipped']}"))
    logger.info(f"错误:         {stats['errors']}"))
    logger.info(f"Inputs修复:   {stats['inputs_fixed_total']}"))
    logger.info(f"Outputs修复:  {stats['outputs_fixed_total']}"))


if __name__ == "__main__":
    main()
