"""
AUTO-EVO-AI V0.1 — OCR 识别路由
接口：POST /api/v1/ocr/recognize (上传图片) + POST /api/v1/ocr/recognize-pdf
"""

import base64
import logging
from fastapi import APIRouter, UploadFile, File, Form
from modules.ocr_engine import recognize_image, recognize_pdf, analyze_layout

logger = logging.getLogger("routes_ocr")
router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


@router.post("/recognize")
async def ocr_recognize(file: UploadFile = File(...), languages: str = Form("ch_sim,en")):
    """上传图片进行 OCR 识别"""
    try:
        raw = await file.read()
        if not raw:
            return {"success": False, "error": "文件为空"}
        lang_list = [l.strip() for l in languages.split(",")]
        result = recognize_image(raw, lang_list)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.post("/recognize-base64")
async def ocr_recognize_base64(image: str = Form(...), languages: str = Form("ch_sim,en")):
    """base64 图片进行 OCR 识别"""
    try:
        lang_list = [l.strip() for l in languages.split(",")]
        result = recognize_image(image, lang_list)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.post("/recognize-pdf")
async def ocr_recognize_pdf(file: UploadFile = File(...), languages: str = Form("ch_sim,en")):
    """上传 PDF 进行 OCR 识别"""
    try:
        raw = await file.read()
        if not raw:
            return {"success": False, "error": "文件为空"}
        lang_list = [l.strip() for l in languages.split(",")]
        result = recognize_pdf(raw, lang_list)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.post("/analyze-layout")
async def ocr_analyze_layout(file: UploadFile = File(...)):
    """上传图片进行版面分析"""
    try:
        raw = await file.read()
        if not raw:
            return {"success": False, "error": "文件为空"}
        import base64
        b64 = base64.b64encode(raw).decode()
        result = analyze_layout(b64)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
