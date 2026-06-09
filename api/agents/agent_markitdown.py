"""MarkItDown — 微软通用文档转 Markdown（PDF/Office/图片→LLM可读）"""
import os, json
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def convert_to_markdown(file_path: str = "", text: str = "", file_type: str = "auto") -> dict:
    """将任意文档转为Markdown
    Args:
        file_path: 文件路径（优先）
        text: 文本内容（当file_path为空时）
        file_type: 文件类型 hint (pdf/docx/xlsx/pptx/image/auto)
    Returns:
        {"success": bool, "markdown": str, "error": str}
    """
    try:
        from markitdown import MarkItDown
    except ImportError:
        return {"success": False, "error": "markitdown 未安装。运行: pip install markitdown[all]"}

    try:
        md = MarkItDown()
        if file_path:
            fp = Path(file_path)
            if not fp.exists():
                return {"success": False, "error": f"文件不存在: {file_path}"}
            result = md.convert(str(fp))
            return {"success": True, "markdown": result.text_content, "file": file_path, "format": fp.suffix}
        elif text:
            # 写临时文件再转换
            import tempfile
            ext_map = {"pdf": ".pdf", "docx": ".docx", "xlsx": ".xlsx", "pptx": ".pptx", "html": ".html",
                       "md": ".md", "txt": ".txt", "csv": ".csv", "json": ".json", "xml": ".xml",
                       "image": ".png", "jpg": ".jpg", "auto": ".txt"}
            ext = ext_map.get(file_type, ".txt")
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False, mode='w', encoding='utf-8') as tmp:
                tmp.write(text)
                tmp_path = tmp.name
            try:
                result = md.convert(tmp_path)
                return {"success": True, "markdown": result.text_content, "format": ext}
            finally:
                os.unlink(tmp_path)
        else:
            return {"success": False, "error": "请提供 file_path 或 text 参数"}
    except Exception as e:
        return {"success": False, "error": f"转换失败: {e}"}

def batch_convert(file_paths: list) -> dict:
    """批量转换多个文件"""
    results = []
    for fp in file_paths:
        r = convert_to_markdown(file_path=fp)
        results.append({"file": fp, "ok": r["success"], "markdown_len": len(r.get("markdown",""))})
    return {"success": True, "total": len(results), "results": results}
