"""
AUTO-EVO-AI V0.1 — 模块浏览/搜索/分类 API
上市公司级: 解决535模块认知负担，让用户能发现、搜索、过滤模块
"""
from __future__ import annotations

from core.logging_config import get_logger
import os
import re
from pathlib import Path
from typing import Any
from api.category_map import normalize_category

from fastapi import APIRouter, Query

logger = get_logger("evo.api.modules_browse")

router = APIRouter()

MODULES_DIR = Path(__file__).resolve().parent.parent.parent / "modules"


def _scan_modules() -> list[dict[str, Any]]:
    """扫描 modules/ 目录，返回每个模块的元数据"""
    modules = []
    if not MODULES_DIR.exists():
        return modules
    for f in sorted(MODULES_DIR.iterdir()):
        if not f.name.endswith(".py") or f.name.startswith("_"):
            continue
        # 读取模块元数据
        content = f.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        docstring = ""
        reading_doc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if reading_doc:
                    break
                reading_doc = True
                doc_part = stripped[3:].strip()
                if doc_part:
                    docstring = doc_part
                continue
            if reading_doc:
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    docstring += " " + stripped[:-3]
                    break
                docstring += " " + stripped

        # 提取 module_class 和 execute 方法
        has_execute = "async def execute" in content or "def execute" in content
        has_class = "class module_class" in content or "class Module" in content

        # 提取 grade（从 __module_meta__ 或文件注释）
        grade_match = re.search(r"""["']grade["']\s*:\s*["'](\w)["']""", content)
        grade = grade_match.group(1).upper() if grade_match else 'C'

        # 提取 category（从文件名前缀或 __module_meta__）
        meta_cat = re.search(r"""["']category["']\s*:\s*["']([\w_]+)["']""", content)
        if meta_cat:
            category = normalize_category(meta_cat.group(1))
        else:
            # fallback: 按文件名前缀分类
            parts = f.name[:-3].split('_')
            raw_cat = parts[0].upper() if len(parts) > 1 else f.name[:-3][:10].upper()
            category = normalize_category(raw_cat)

        module_size = len(content)

        # 判断是否真实逻辑（>2KB 或有 execute 方法）
        real_logic = module_size > 2048 or has_execute

        # 提取 actions
        actions = []
        for pattern in [
            r'action\s*=\s*"(\w+)"',
            r'action_lower\s*in\s*\("(\w+)"',
            r'"(\w+)"\s*,\s*#.*action',
        ]:
            actions.extend(re.findall(pattern, content))
        modules.append(
            {
                "name": f.name[:-3],
                "file": f.name,
                "size": module_size,
                "lines": len(lines),
                "has_class": has_class,
                "has_execute": has_execute,
                "grade": grade,
                "category": category,
                "real_logic": real_logic,
                "docstring": docstring[:200] if docstring else "",
                "actions": sorted(set(actions))[:20],
            }
        )
    return modules


@router.get("/api/v1/modules/list")
async def modules_list(
    search: str = Query("", description="搜索关键词（名称或描述）"),
    has_execute: bool | None = Query(None, description="是否包含 execute 方法"),
    min_lines: int = Query(0, description="最小行数"),
    sort_by: str = Query("name", description="排序: name|size|lines"),
    limit: int = Query(50, description="返回数量"),
    offset: int = Query(0, description="偏移量"),
):
    """浏览和搜索模块目录"""
    all_modules = _scan_modules()
    total = len(all_modules)

    # 过滤
    if search:
        q = search.lower()
        all_modules = [m for m in all_modules if q in m["name"].lower() or q in m["docstring"].lower()]
    if has_execute is not None:
        all_modules = [m for m in all_modules if m["has_execute"] == has_execute]
    if min_lines > 0:
        all_modules = [m for m in all_modules if m["lines"] >= min_lines]

    # 排序
    reverse = sort_by.startswith("-")
    key = sort_by.lstrip("-")
    if key in ("name", "size", "lines"):
        all_modules.sort(key=lambda m, k=key: m.get(k, 0) if isinstance(m.get(k, 0), (int, float)) else str(m.get(k, "")), reverse=reverse)

    # 分页
    page = all_modules[offset : offset + limit]
    return {
        "success": True,
        "modules": page,
        "total": total,
        "filtered": len(all_modules),
        "returned": len(page),
        "offset": offset,
        "limit": limit,
    }


@router.get("/api/v1/modules/categories")
async def modules_categories():
    """模块分类统计"""
    all_modules = _scan_modules()
    categories: dict[str, int] = {}
    for m in all_modules:
        # 按文件名首字母/前缀分类
        prefix = m["name"].split("_")[0] if "_" in m["name"] else m["name"][0].upper()
        categories[prefix] = categories.get(prefix, 0) + 1

    size_ranges = {"<1KB": 0, "1-5KB": 0, "5-20KB": 0, ">20KB": 0}
    for m in all_modules:
        if m["size"] < 1024:
            size_ranges["<1KB"] += 1
        elif m["size"] < 5120:
            size_ranges["1-5KB"] += 1
        elif m["size"] < 20480:
            size_ranges["5-20KB"] += 1
        else:
            size_ranges[">20KB"] += 1

    return {
        "success": True,
        "total": len(all_modules),
        "with_execute": sum(1 for m in all_modules if m["has_execute"]),
        "categories": dict(sorted(categories.items(), key=lambda x: -x[1])),
        "size_ranges": size_ranges,
        "largest": sorted(all_modules, key=lambda m: -m["size"])[:5],
    }
