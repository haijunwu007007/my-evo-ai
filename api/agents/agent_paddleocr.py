"""PaddleOCR — 百度开源高精度OCR工具包（45K⭐），支持中英文文字识别/表格提取"""
import os, json, tempfile
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def paddleocr_image(image_path: str = "", lang: str = "ch") -> dict:
    """识别图片中的文字"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return {"success": False, "error": "paddleocr 未安装。运行: pip install paddleocr"}
    if not image_path or not os.path.isfile(image_path):
        return {"success": False, "error": "文件不存在"}
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        result = ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return {"success": True, "text": "", "details": []}
        lines = []
        full_text = []
        for line in result[0]:
            box, (text, confidence) = line
            lines.append({"text": text, "confidence": round(confidence, 4)})
            full_text.append(text)
        return {"success": True, "text": "\n".join(full_text), "details": lines,
                "char_count": sum(len(t) for t in full_text)}
    except Exception as e:
        return {"success": False, "error": f"OCR失败: {e}"}

def paddleocr_pdf(pdf_path: str = "", lang: str = "ch") -> dict:
    """识别PDF中的文字（逐页）"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return {"success": False, "error": "paddleocr 未安装"}
    if not pdf_path or not os.path.isfile(pdf_path):
        return {"success": False, "error": "文件不存在"}
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return {"success": False, "error": "pdf2image 未安装。运行: pip install pdf2image"}
    try:
        images = convert_from_path(pdf_path, dpi=200)
        ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        pages = []
        for idx, img in enumerate(images):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                img.save(tmp_path, "PNG")
                result = ocr.ocr(tmp_path, cls=True)
                text = "\n".join([line[1][0] for line in result[0]]) if result and result[0] else ""
                pages.append({"page": idx+1, "text": text, "char_count": len(text)})
            finally:
                os.unlink(tmp_path)
        full = "\n".join(p.get("text","") for p in pages)
        return {"success": True, "pages": pages, "total_pages": len(pages), "full_text": full}
    except Exception as e:
        return {"success": False, "error": f"PDF OCR失败: {e}"}

def paddleocr_extract_table(image_path: str = "") -> dict:
    """从图片中提取表格"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return {"success": False, "error": "paddleocr 未安装"}
    if not image_path or not os.path.isfile(image_path):
        return {"success": False, "error": "文件不存在"}
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        result = ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return {"success": True, "rows": [], "text": ""}
        rows = []
        for line in result[0]:
            box, (text, conf) = line
            rows.append({"text": text, "confidence": round(conf, 4),
                         "y": round(min(p[1] for p in box), 1)})
        rows.sort(key=lambda r: r["y"])
        return {"success": True, "rows": rows, "text": "\n".join(r["text"] for r in rows)}
    except Exception as e:
        return {"success": False, "error": f"表格提取失败: {e}"}
