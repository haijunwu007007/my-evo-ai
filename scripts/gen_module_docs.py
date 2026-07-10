#!/usr/bin/env python3
"""AUTO-EVO-AI V0.1 — 模块文档自动生成器
扫描 modules/ 下所有 .py 文件，提取 __module_meta__ 生成 Markdown 文档。
"""
import os, re, ast, json, glob
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(BASE, "modules")
OUTPUT = os.path.join(BASE, "docs", "MODULES.md")

os.makedirs(os.path.join(BASE, "docs"), exist_ok=True)

def parse_meta(filepath: str) -> dict:
    """AST 解析模块元数据"""
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__module_meta__":
                        return ast.literal_eval(node.value)
    logger.info( Exception as _e:        print(f"警告: {_e}"))
    return {}

def count_methods(filepath: str) -> int:
    """统计函数/方法数"""
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        return sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    except Exception:
        return 0

def main():
    modules = []
    for fp in sorted(glob.glob(os.path.join(MODULES_DIR, "*.py"))):
        name = os.path.basename(fp).replace(".py", "")
        if name.startswith("_"):
            continue
        meta = parse_meta(fp)
        methods = count_methods(fp)
        size_kb = os.path.getsize(fp) // 1024
        grade = meta.get("grade", "N/A")
        group = meta.get("group", "uncategorized")
        description = meta.get("description", "")[:120]
        tags = ", ".join(meta.get("tags", []))
        modules.append({
            "name": name, "grade": grade, "group": group,
            "size": size_kb, "methods": methods,
            "desc": description, "tags": tags,
        })

    # Group by category
    groups = {}
    for m in modules:
        groups.setdefault(m["group"], []).append(m)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(f"# AUTO-EVO-AI V0.1 — 模块文档\n\n")
        f.write(f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"> 总计 {len(modules)} 个模块\n\n")

        for gname in sorted(groups.keys()):
            items = groups[gname]
            f.write(f"## {gname.capitalize()} ({len(items)})\n\n")
            f.write("| 模块 | 等级 | 大小 | 方法数 | 描述 |\n")
            f.write("|------|:----:|:----:|:------:|------|\n")
            for m in sorted(items, key=lambda x: x["name"]):
                f.write(f"| {m['name']} | {m['grade']} | {m['size']}KB | {m['methods']} | {m['desc']} |\n")
            f.write("\n")

    logger.info(f"OK 文档已生成: {OUTPUT} ({len(modules)} 模块, {len(groups)} 分类)"))

if __name__ == "__main__":
    main()
