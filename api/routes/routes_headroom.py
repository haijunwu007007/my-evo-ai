"""AUTO-EVO-AI V0.1 — Headroom 上下文压缩 API"""
from fastapi import APIRouter, Body
from modules.headroom_compress import compress_json, compress_code, compress_logs, compress_history, get_status, compute_compression_ratio
router = APIRouter(prefix="/api/v1/headroom", tags=["headroom"])
import json

@router.get("/status")
def status():
    return get_status()

@router.post("/compress/json")
def api_compress_json(data: dict = Body(...)):
    _raw = json.dumps(data.get("data", {}))
    result = compress_json(data.get("data", {}), data.get("max_depth", 3))
    stats = compute_compression_ratio(_raw, json.dumps(result))
    return {"success": True, "result": result, "stats": stats}

@router.post("/compress/code")
def api_compress_code(data: dict = Body(...)):
    result = compress_code(data.get("code", ""), data.get("keep_imports", True), data.get("max_lines", 100))
    stats = compute_compression_ratio(data.get("code", ""), result)
    return {"success": True, "result": result, "stats": stats}

@router.post("/compress/logs")
def api_compress_logs(data: dict = Body(...)):
    result = compress_logs(data.get("logs", ""), data.get("max_entries", 50))
    stats = compute_compression_ratio(data.get("logs", ""), result)
    return {"success": True, "result": result, "stats": stats}

@router.post("/compress/history")
def api_compress_history(data: dict = Body(...)):
    result = compress_history(data.get("messages", []), data.get("max_turns", 6))
    return {"success": True, "result": result}
