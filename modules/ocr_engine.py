"""
AUTO-EVO-AI V0.1 — OCR 引擎模块（真实 EasyOCR 实现）
Grade: A | Category: 媒体处理
职责：图片/PDF文字识别、文档版面分析、多语言OCR
"""

__module_meta__ = {
    "id": "ocr-engine",
    "name": "OCR Engine",
    "version": "V0.1",
    "group": "media",
    "grade": "A",
    "description": "基于 EasyOCR 的多语言图片文字识别引擎",
}

import os
import base64
import logging
import tempfile
from io import BytesIO

logger = logging.getLogger("ocr_engine")

_ocr_reader = None

def _get_reader(languages=None):
    global _ocr_reader
    if languages is None:
        languages = ['ch_sim', 'en']
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(languages, gpu=False)
            logger.info(f"EasyOCR 加载成功: languages={languages}")
        except Exception as e:
            logger.error(f"EasyOCR 加载失败: {e}")
            return None
    return _ocr_reader


def recognize_image(image_data: str | bytes, languages: list = None) -> dict:
    """
    识别图片中的文字
    image_data: base64字符串 或 bytes
    languages: ['ch_sim','en'] 等
    返回: {success, text, items:[{text,confidence,bbox}], language, char_count}
    """
    reader = _get_reader(languages)
    if not reader:
        return {"success": False, "error": "OCR引擎未加载"}

    try:
        # 解码输入
        if isinstance(image_data, str):
            if image_data.startswith("data:image"):
                image_data = image_data.split(",")[-1]
            raw = base64.b64decode(image_data)
        else:
            raw = image_data

        # EasyOCR 接受 bytes
        import numpy as np
        import cv2

        # 转为 numpy array
        nparr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            # 尝试用 PIL 打开
            from PIL import Image
            img_pil = Image.open(BytesIO(raw))
            img = np.array(img_pil)

        results = reader.readtext(img)
        items = []
        full_text = []
        total_conf = 0.0
        for bbox, text, conf in results:
            items.append({
                "text": text,
                "confidence": round(float(conf), 4),
                "bbox": [[int(x), int(y)] for x, y in bbox],
            })
            full_text.append(text)
            total_conf += conf

        text = "\n".join(full_text)
        char_count = len(text.replace("\n", "").replace(" ", ""))

        return {
            "success": True,
            "text": text,
            "items": items,
            "total_items": len(items),
            "avg_confidence": round(total_conf / max(len(items), 1), 4),
            "char_count": char_count,
            "language": languages or ["ch_sim", "en"],
        }

    except Exception as e:
        logger.error(f"OCR 识别错误: {e}")
        return {"success": False, "error": str(e)[:200]}


def recognize_pdf(pdf_data: bytes, languages: list = None, dpi: int = 200) -> dict:
    """
    识别 PDF 中的文字（每页作为一图处理）
    pdf_data: PDF 文件 bytes
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {"success": False, "error": "需要安装 PyMuPDF: pip install PyMuPDF"}

    reader = _get_reader(languages)
    if not reader:
        return {"success": False, "error": "OCR引擎未加载"}

    try:
        import numpy as np
        import cv2

        doc = fitz.open(stream=pdf_data, filetype="pdf")
        pages_result = []
        total_text = []
        total_items = 0
        total_conf = 0.0

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 渲染为图片
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            results = reader.readtext(img)
            page_text = []
            for bbox, text, conf in results:
                page_text.append(text)
                total_items += 1
                total_conf += float(conf)

            page_str = "\n".join(page_text)
            total_text.append(f"--- 第{page_num+1}页 ---\n{page_str}")
            pages_result.append({
                "page": page_num + 1,
                "text": page_str,
                "items": len(page_text),
            })

        doc.close()
        return {
            "success": True,
            "text": "\n\n".join(total_text),
            "pages": pages_result,
            "total_pages": len(doc),
            "total_items": total_items,
            "avg_confidence": round(total_conf / max(total_items, 1), 4),
        }

    except Exception as e:
        logger.error(f"PDF OCR 错误: {e}")
        return {"success": False, "error": str(e)[:200]}


def analyze_layout(image_data: str | bytes) -> dict:
    """版面分析（基于 OCR 结果的简单布局推断）"""
    result = recognize_image(image_data)
    if not result.get("success"):
        return result

    lines = result.get("text", "").split("\n")
    blocks = []
    current = {"type": "text", "start": 0, "lines": 0, "chars": 0}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if current["lines"] > 0:
                blocks.append(current)
                current = {"type": "text", "start": i + 1, "lines": 0, "chars": 0}
            continue
        current["lines"] += 1
        current["chars"] += len(stripped)
        if stripped.startswith("#") or stripped.startswith("=="):
            current["type"] = "heading"
        elif "|" in stripped and stripped.count("|") >= 2:
            current["type"] = "table"
    if current["lines"] > 0:
        blocks.append(current)

    return {
        "success": True,
        "total_lines": len(lines),
        "total_blocks": len(blocks),
        "headings": sum(1 for b in blocks if b["type"] == "heading"),
        "tables": sum(1 for b in blocks if b["type"] == "table"),
        "text_blocks": sum(1 for b in blocks if b["type"] == "text"),
        "blocks": blocks[:20],
    }


# === EnterpriseModule 兼容接口 ===
class OcrEngineManager:
    """OCR 引擎管理器 - 兼容旧版接口"""
    def __init__(self):
        self._reader = None

    def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        if action == "recognize":
            return recognize_image(params.get("image", ""), params.get("languages"))
        elif action == "recognize_pdf":
            return recognize_pdf(params.get("pdf", b""), params.get("languages"))
        elif action == "analyze_layout":
            return analyze_layout(params.get("image", ""))
        elif action == "status":
            return self.get_status()
        return self.get_status()

    def get_status(self) -> dict:
        reader = _get_reader()
        return {
            "success": True,
            "module": "OCR Engine",
            "status": "active" if reader else "error",
            "engine": "EasyOCR",
            "languages": ["ch_sim", "en"],
        }

module_class = OcrEngineManager
