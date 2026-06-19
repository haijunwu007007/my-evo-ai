"""
路由文件: routes_docs.py — 文档办公套件 API

提供 Word/PDF/PPT/Excel 4 套文档处理工具的 RESTful API，
调用 modules/ 下对应的模块执行实际操作。
"""

from __future__ import annotations

import json, os, sys, tempfile, time, base64, mimetypes
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from api.infra import BASE_DIR, logger

router = APIRouter(tags=["docs"], prefix="/api/v1/docs")

OUTPUT_DIR = BASE_DIR / "output" / "docs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

async def _call_module(module_name: str, action: str, params: dict = None) -> dict:
    """调用模块并返回统一结果
    绕过 _execute_module_internal（签名不匹配问题），直接导入模块调用 execute
    """
    import importlib
    try:
        mod_obj = importlib.import_module(f"modules.{module_name}")
    except Exception:
        raise HTTPException(404, f"模块 {module_name} 不存在")
    cls = None
    for attr_name in dir(mod_obj):
        attr = getattr(mod_obj, attr_name)
        if isinstance(attr, type) and hasattr(attr, 'execute') and attr_name != 'EnterpriseModule':
            cls = attr
            break
    if not cls:
        raise HTTPException(500, f"模块 {module_name} 无可执行类")
    inst = cls()
    if hasattr(inst, 'initialize') and callable(inst.initialize):
        init_r = inst.initialize()
        if hasattr(init_r, '__await__'):
            await init_r
    # 模块 execute(action, path, data) 签名：action 和 data 是分离的
    result = inst.execute(action=action, path=params.get("path", ""), data=params)
    if hasattr(result, '__await__'):
        result = await result
    if isinstance(result, dict):
        if result.get("success") or result.get("status") == "success":
            return result
        raise HTTPException(status_code=422, detail=result.get("error", str(result.get("message", result))[:200]))
    return {"success": True, "result": result}


def _save_temp(data: Any, suffix: str) -> str:
    """保存临时文件，返回路径"""
    with tempfile.NamedTemporaryFile(
        dir=str(OUTPUT_DIR), suffix=suffix, delete=False
    ) as f:
        if isinstance(data, bytes):
            f.write(data)
        elif isinstance(data, str):
            f.write(data.encode("utf-8"))
        path = f.name
    return path


def _read_file_bytes(path: str) -> str:
    """读取文件并返回 base64"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════════
# Word 文档 (docx_processor)
# ═══════════════════════════════════════════════════════════════════

@router.post("/docx/create")
async def docx_create(request: Request):
    """创建 Word 文档"""
    body = await request.json()
    result = await _call_module("docx_processor", "create", {
        "title": body.get("title", "未命名文档"),
        "headings": body.get("headings", []),
        "content": body.get("content", "Hello World"),
        "output": body.get("output", ""),
    })
    # 如果返回了文件路径，返回文件
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    return JSONResponse(result)


@router.post("/docx/read")
async def docx_read(request: Request):
    """读取 Word 文档"""
    body = await request.json()
    file_path = body.get("path", "")
    result = await _call_module("docx_processor", "read", {"path": file_path})
    return JSONResponse(result)


@router.post("/docx/edit")
async def docx_edit(request: Request):
    """编辑 Word 文档（查找替换）"""
    body = await request.json()
    result = await _call_module("docx_processor", "edit", {
        "path": body.get("path", ""),
        "replacements": body.get("replacements", {}),
    })
    # 返回编辑后的文件
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    return JSONResponse(result)


@router.post("/docx/merge")
async def docx_merge(request: Request):
    """合并多个 Word 文档"""
    body = await request.json()
    result = await _call_module("docx_processor", "merge", {
        "paths": body.get("paths", []),
        "output": body.get("output", "merged.docx"),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    return JSONResponse(result)


@router.post("/docx/convert")
async def docx_convert(request: Request):
    """转换 Word 为其他格式"""
    body = await request.json()
    action_map = {"to_md": "to_md", "to_txt": "to_txt", "to_html": "to_md"}
    act = action_map.get(body.get("format", "to_md"), "to_md")
    result = await _call_module("docx_processor", act, {
        "path": body.get("path", ""),
    })
    return JSONResponse(result)


# ═══════════════════════════════════════════════════════════════════
# PDF 处理 (pdf_toolkit)
# ═══════════════════════════════════════════════════════════════════

@router.post("/pdf/merge")
async def pdf_merge(request: Request):
    """合并 PDF"""
    body = await request.json()
    result = await _call_module("pdf_toolkit", "merge", {
        "paths": body.get("paths", []),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/pdf")
    return JSONResponse(result)


@router.post("/pdf/split")
async def pdf_split(request: Request):
    """拆分 PDF"""
    body = await request.json()
    result = await _call_module("pdf_toolkit", "split", {
        "path": body.get("path", ""),
        "pages": body.get("pages", ""),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/pdf")
    return JSONResponse(result)


@router.post("/pdf/extract-text")
async def pdf_extract_text(request: Request):
    """提取 PDF 文本"""
    body = await request.json()
    result = await _call_module("pdf_toolkit", "extract_text", {
        "path": body.get("path", ""),
    })
    return JSONResponse(result)


@router.post("/pdf/extract-tables")
async def pdf_extract_tables(request: Request):
    """提取 PDF 表格"""
    body = await request.json()
    result = await _call_module("pdf_toolkit", "extract_tables", {
        "path": body.get("path", ""),
    })
    return JSONResponse(result)


@router.post("/pdf/info")
async def pdf_info(request: Request):
    """PDF 文件信息"""
    body = await request.json()
    result = await _call_module("pdf_toolkit", "info", {
        "path": body.get("path", ""),
    })
    return JSONResponse(result)


# ═══════════════════════════════════════════════════════════════════
# PPT 演示 (ppt_generator)
# ═══════════════════════════════════════════════════════════════════

@router.post("/ppt/create")
async def ppt_create(request: Request):
    """创建 PPT"""
    body = await request.json()
    result = await _call_module("ppt_generator", "create", {
        "title": body.get("title", "演示文稿"),
        "pages": body.get("pages", []),
        "theme": body.get("theme", "default"),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    return JSONResponse(result)


@router.post("/ppt/read")
async def ppt_read(request: Request):
    """读取 PPT 内容"""
    body = await request.json()
    result = await _call_module("ppt_generator", "read", {
        "path": body.get("path", ""),
    })
    return JSONResponse(result)


@router.post("/ppt/chart")
async def ppt_chart(request: Request):
    """在 PPT 中插入图表"""
    body = await request.json()
    result = await _call_module("ppt_generator", "chart", {
        "path": body.get("path", ""),
        "chart_type": body.get("chart_type", "bar"),
        "title": body.get("title", "图表"),
        "categories": body.get("categories", []),
        "series": body.get("series", []),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    return JSONResponse(result)


# ═══════════════════════════════════════════════════════════════════
# Excel 高级处理 (excel_pro)
# ═══════════════════════════════════════════════════════════════════

@router.post("/excel/create")
async def excel_create(request: Request):
    """创建 Excel 文件"""
    body = await request.json()
    raw_sheets = body.get("sheets", {"Sheet1": [["标题", "值"]]})
    # 兼容两种格式：dict of {name: [rows]} 或 list of {name, headers, rows}
    if isinstance(raw_sheets, dict):
        sheets = []
        first = True
        for sname, srows in raw_sheets.items():
            sheet_def = {"name": sname}
            if first and srows and len(srows) > 0:
                sheet_def["headers"] = srows[0]
                sheet_def["rows"] = srows[1:]
            else:
                sheet_def["rows"] = srows
            sheets.append(sheet_def)
            first = False
    else:
        sheets = raw_sheets
    result = await _call_module("excel_pro", "create", {
        "sheets": sheets,
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return JSONResponse(result)


@router.post("/excel/read")
async def excel_read(request: Request):
    """读取 Excel"""
    body = await request.json()
    result = await _call_module("excel_pro", "read", {
        "path": body.get("path", ""),
        "sheet_name": body.get("sheet_name", ""),
    })
    return JSONResponse(result)


@router.post("/excel/chart")
async def excel_chart(request: Request):
    """在 Excel 中插入图表"""
    body = await request.json()
    result = await _call_module("excel_pro", "chart", {
        "path": body.get("path", ""),
        "chart_type": body.get("chart_type", "bar"),
        "title": body.get("title", "图表"),
        "data_range": body.get("data_range", ""),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return JSONResponse(result)


@router.post("/excel/pivot")
async def excel_pivot(request: Request):
    """创建数据透视表"""
    body = await request.json()
    result = await _call_module("excel_pro", "pivot", {
        "path": body.get("path", ""),
        "data": body.get("data", []),
        "rows": body.get("rows", []),
        "values": body.get("values", []),
        "agg_func": body.get("agg_func", "sum"),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return JSONResponse(result)


@router.post("/excel/formula")
async def excel_formula(request: Request):
    """在 Excel 中设置公式"""
    body = await request.json()
    result = await _call_module("excel_pro", "formula", {
        "path": body.get("path", ""),
        "formulas": body.get("formulas", {}),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return JSONResponse(result)


@router.post("/excel/merge")
async def excel_merge(request: Request):
    """合并多个 Excel"""
    body = await request.json()
    result = await _call_module("excel_pro", "merge", {
        "paths": body.get("paths", []),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return JSONResponse(result)


@router.post("/excel/convert")
async def excel_convert(request: Request):
    """Excel 格式转换"""
    body = await request.json()
    result = await _call_module("excel_pro", "convert", {
        "path": body.get("path", ""),
        "target_format": body.get("target_format", "csv"),
        "output": body.get("output", ""),
    })
    _path = result.get("path") or (result.get("result") or {}).get("path")
    if _path and Path(_path).exists():
        return FileResponse(str(_path), filename=Path(_path).name)
    return JSONResponse(result)


# ═══════════════════════════════════════════════════════════════════
# 统一的 docs 管理端点
# ═══════════════════════════════════════════════════════════════════

@router.get("/list")
async def docs_list():
    """列出所有已生成的文档"""
    files = []
    if OUTPUT_DIR.exists():
        for f in sorted(OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
            mime, _ = mimetypes.guess_type(str(f))
            files.append({
                "name": f.name,
                "size": f"{f.stat().st_size / 1024:.1f} KB",
                "path": str(f.relative_to(BASE_DIR) if f.is_relative_to(BASE_DIR) else f),
                "mtime": time.ctime(f.stat().st_mtime),
                "type": mime or "application/octet-stream",
            })
    return {"success": True, "files": files}


@router.get("/download")
async def docs_download(path: str = Query(..., description="文件路径")):
    """下载生成的文档"""
    abs_path = Path(path)
    if not abs_path.is_absolute():
        abs_path = BASE_DIR / path
    if not abs_path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(str(abs_path))
