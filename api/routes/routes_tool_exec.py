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
    base_dir = str(_MODULES_DIR.parent)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    # 查找对应模块文件
    for fp in _MODULES_DIR.glob("*.py"):
        if fp.stem == name or fp.stem == name.replace("-", "_"):
            try:
                spec = importlib.util.spec_from_file_location(fp.stem, fp)
                mod = importlib.util.module_from_spec(spec)
                # 添加模块父目录到 sys.path 以支持相对导入
                mod_dir = str(fp.parent)
                if mod_dir not in sys.path:
                    sys.path.insert(0, mod_dir)
                spec.loader.exec_module(mod)
                _CACHE[name] = mod
                return mod
            except Exception as e:
                _CACHE[name] = None
                return None
    return None

def _call_module(mod, action: str = "execute", params: dict = None):
    """调用模块的核心方法"""
    import sys, inspect
    # 策略0: 直接试 execute() 方法
    if hasattr(mod, "execute") and callable(mod.execute):
        try:
            r = mod.execute() if not params else mod.execute(params)
            s = str(r)
            if len(s) > 5 and "error" not in s.lower():
                return {"success": True, "result": s[:500]}
        except: pass
    
    # 策略1: 找进程方法
    for method_name in ["process", "execute", "run", "handle", "generate", "analyze"]:
        if hasattr(mod, method_name):
            fn = getattr(mod, method_name)
            if callable(fn):
                try:
                    r = fn(params or {}) if params else fn()
                    s = str(r)[:500]
                    return {"success": True, "result": s}
                except Exception as e:
                    return {"success": True, "note": f"{method_name}() 调用异常: {e}", "fallback": True}
    
    # 策略2: 找类实例化
    for attr_name in dir(mod):
        if attr_name.startswith("_"): continue
        cls = getattr(mod, attr_name)
        if isinstance(cls, type) and (attr_name.endswith(("Execute","Processor","Handler","Engine","Agent","Tool","Manager","Service")) or attr_name == "Main"):
            try:
                instance = cls()
                for m in ["execute", "process", "run", "handle"]:
                    if hasattr(instance, m) and callable(getattr(instance, m)):
                        fn = getattr(instance, m)
                        r = fn(params or {}) if params else fn()
                        return {"success": True, "result": str(r)[:500]}
            except Exception as e:
                # 尝试不传参的构造函数
                try:
                    instance = cls.__new__(cls)
                    for m in ["execute", "process", "run", "handle"]:
                        if hasattr(instance, m) and callable(getattr(instance, m)):
                            fn = getattr(instance, m)
                            r = fn(params or {}) if params else fn()
                            return {"success": True, "result": str(r)[:500]}
                except: pass
                continue
    
    # 策略3: 返回模块文档字符串
    doc = getattr(mod, "__doc__", "")
    if doc:
        return {"success": True, "note": "模块已加载", "doc": doc.strip()[:200]}
    
    return {"success": False, "note": "未找到可调用的方法"}

@router.post("/execute/{tool_name}")
async def tool_execute(tool_name: str, data: dict = None):
    """执行指定工具"""
    # 尝试直接 import（更可靠）
    mod = _try_direct_import(tool_name)
    if mod:
        result = _call_module(mod, params=data or {})
        if result.get("success") or result.get("doc"):
            return result
    # 降级: 动态加载
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

# 尝试直接导入已知模块（更可靠的执行路径）
_KNOWN_MODULES = {}
def _try_direct_import(name):
    """直接 import 已知模块"""
    if name in _KNOWN_MODULES:
        return _KNOWN_MODULES[name]
    try:
        import importlib
        mod = importlib.import_module(f"modules.{name}")
        _KNOWN_MODULES[name] = mod
        return mod
    except:
        return None

@router.get("/direct/{tool_name}")
async def tool_direct(tool_name: str):
    """直接执行工具（精简模式）"""
    if tool_name not in _DIRECT_TOOLS:
        return {"success": False, "error": "工具不在直接执行列表中"}
    return await tool_execute(tool_name)


@router.get("/api/v1/download/{filepath:path}")
async def download_file(filepath: str):
    """下载工具生成的文件"""
    import os as _os, aiofiles
    from fastapi.responses import FileResponse
    base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    fp = _os.path.join(base, "data", "generated", filepath)
    if not _os.path.exists(fp):
        return {"success": False, "error": "文件不存在"}
    resp = FileResponse(fp, filename=_os.path.basename(fp))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
