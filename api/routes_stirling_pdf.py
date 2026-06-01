"""AUTO-EVO-AI V0.1 — Stirling-PDF 工具箱桥接路由"""
from fastapi import APIRouter
import urllib.request, json as _json

router = APIRouter()
B = "/api/tools/pdf"

STIRLING_HOST = "http://127.0.0.1:8081"

def _req(method, path, body=None):
    try:
        url = f"{STIRLING_HOST}{path}"
        data = _json.dumps(body).encode() if body else None
        r = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(r, timeout=5) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "application/json" in ct:
                return _json.loads(resp.read())
            return {"status": resp.status, "body": resp.read().decode()[:300]}
    except Exception as e:
        return {"error": str(e)[:200]}

@router.get(B)
async def pdf_status():
    if "error" in _req("GET", "/api/v1/info"):
        return {"success": True, "available": False, "host": STIRLING_HOST}
    return {"success": True, "available": True, "host": STIRLING_HOST, "operations": 60}

_OPERATIONS = [
    {"id": "merge", "name": "合并PDF", "desc": "合并多个PDF文件为一个"},
    {"id": "split", "name": "拆分PDF", "desc": "按页拆分PDF"},
    {"id": "compress", "name": "压缩PDF", "desc": "优化PDF文件大小"},
    {"id": "convert-to-pdf", "name": "转PDF", "desc": "Office/图片转为PDF"},
    {"id": "ocr", "name": "OCR识别", "desc": "扫描件文字识别"},
    {"id": "rotate", "name": "旋转页面", "desc": "旋转PDF页面方向"},
    {"id": "sign", "name": "电子签名", "desc": "添加签名到PDF"},
]

@router.get(B + "/operations")
async def pdf_operations():
    return {"success": True, "operations": _OPERATIONS}
