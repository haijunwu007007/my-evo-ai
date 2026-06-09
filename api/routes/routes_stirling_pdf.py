"""AUTO-EVO-AI V0.1 — Stirling-PDF 工具箱桥接路由"""
from fastapi import APIRouter
import urllib.request, json as _json
router = APIRouter()
B = "/api/v1/tools/pdf"
HOST = "http://127.0.0.1:8081"

def _alive():
    try:
        r = urllib.request.urlopen(f"{HOST}/api/v1/info", timeout=2)
        return r.status == 200 or r.status == 302
    except Exception:
        return False

@router.get(B)
async def pdf_status():
    ok = _alive()
    return {"success": True, "available": ok, "host": HOST, "name": "Stirling-PDF (76k⭐) PDF工具箱"}

_OPS = [
    {"id": "merge","name":"合并PDF"},{"id":"split","name":"拆分PDF"},
    {"id":"compress","name":"压缩PDF"},{"id":"convert","name":"转PDF"},
    {"id":"ocr","name":"OCR识别"},{"id":"sign","name":"电子签名"},
]

@router.get(B + "/operations")
async def pdf_ops():
    return {"success": True, "operations": _OPS}
