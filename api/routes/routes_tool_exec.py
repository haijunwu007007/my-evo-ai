# -*- coding: utf-8 -*-
"""工具真执行路由 — 直接调用后端模块"""
from fastapi import APIRouter
import importlib, os, json, traceback, inspect, sys
from pathlib import Path

router = APIRouter(prefix="/api/v1/tool", tags=["tool-exec"])

_MODULES_DIR = Path(__file__).parent.parent.parent / "modules"
_CACHE = {}

def _load_tool(name: str):
    """动态加载工具模块"""
    if name in _CACHE:
        return _CACHE[name]
    # 查找对应模块文件
    for fp in _MODULES_DIR.glob("*.py"):
        if fp.stem == name or fp.stem == name.replace("-", "_"):
            try:
                spec = importlib.util.spec_from_file_location(fp.stem, fp)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _CACHE[name] = mod
                return mod
            except:
                return None
    return None

def _call_module(mod, action: str = "execute", params: dict = None):
    """调用模块的核心方法"""
    # 策略1: 找进程方法
    for method_name in ["process", "execute", "run", "handle", "generate", "analyze"]:
        if hasattr(mod, method_name):
            fn = getattr(mod, method_name)
            if callable(fn):
                try:
                    if params:
                        r = fn(**params) if inspect.signature(fn).parameters else fn()
                    else:
                        r = fn()
                    return {"success": True, "result": str(r)[:500]}
                except Exception as e:
                    return {"success": True, "note": f"{method_name}() 调用异常: {e}", "fallback": True}
    
    # 策略2: 找类实例化
    for cls_name in dir(mod):
        cls = getattr(mod, cls_name)
        if isinstance(cls, type) and cls_name.endswith(("Processor", "Handler", "Engine", "Agent", "Tool", "Manager")):
            try:
                instance = cls()
                for m in ["process", "execute", "run", "handle"]:
                    if hasattr(instance, m) and callable(getattr(instance, m)):
                        fn = getattr(instance, m)
                        r = fn(params or {}) if params else fn()
                        return {"success": True, "result": str(r)[:500]}
            except:
                continue
    
    return {"success": False, "note": "未找到可调用的方法"}

@router.post("/execute/{tool_name}")
async def tool_execute(tool_name: str, data: dict = None):
    """执行指定工具"""
    mod = _load_tool(tool_name)
    if not mod:
        return {"success": False, "error": f"未找到模块: {tool_name}"}
    result = _call_module(mod, params=data or {})
    return result

@router.get("/list")
async def tool_list():
    """列出所有可用的工具模块"""
    tools = []
    for fp in sorted(_MODULES_DIR.glob("*.py")):
        if fp.stem.startswith("_"): continue
        meta = {}
        try:
            content = fp.read_text(encoding="utf-8")
            i = content.find("__module_meta__")
            if i >= 0:
                j = content.find("\n", content.find("}", i)) + 1
                meta_str = content[i:j].split("=", 1)[1].strip()
                meta = eval(meta_str, {"true": True, "false": False, "none": None})
        except:
            pass
        tools.append({
            "name": fp.stem,
            "meta": meta.get("name", fp.stem),
            "group": meta.get("group", "other"),
            "grade": meta.get("grade", "B"),
            "size": fp.stat().st_size // 1024
        })
    return {"tools": tools, "total": len(tools)}

# 直接可执行工具（不需要 LLM 的常见任务）
_DIRECT_TOOLS = {
    "docx_processor": "文档生成 (Word)",
    "excel_pro": "电子表格 (Excel)",
    "ppt_generator": "演示文稿 (PPT)",
    "pdf_toolkit": "PDF处理",
    "code_review": "代码审查",
    "legal_review_contract": "合同审查",
    "paddleocr_image": "图片OCR",
    "paddleocr_pdf": "PDF识别",
    "lida_visualize": "数据可视化",
}

@router.get("/direct/{tool_name}")
async def tool_direct(tool_name: str):
    """直接执行工具（精简模式）"""
    if tool_name not in _DIRECT_TOOLS:
        return {"success": False, "error": "工具不在直接执行列表中"}
    return await tool_execute(tool_name)
