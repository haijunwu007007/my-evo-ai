"""
AUTO-EVO-AI V0.1 — Figma MCP 桥接路由
通过 subprocess 调用 figma-mcp-server 读取 Figma 设计信息
"""
import logging, subprocess, json, shutil
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger("routes_figma_mcp")
router = APIRouter(prefix="/api/v1/figma", tags=["figma"])

FIGMA_AVAILABLE = shutil.which("figma-mcp") is not None

@router.get("/status")
def figma_status():
    return {"success": True, "available": FIGMA_AVAILABLE,
            "note": "需要 Figma Personal Access Token 和 figma-mcp-server",
            "install": "npm install -g figma-mcp-server"}

@router.get("/design")
def figma_design(url: str = Query("", description="Figma 设计文件 URL 或 file_key")):
    if not FIGMA_AVAILABLE:
        return {"success": False, "error": "figma-mcp not installed"}
    try:
        key = url.split("/")[-2] if "/" in url else url
        result = subprocess.run(f"figma-mcp get-file --key {key}", shell=True,
                                capture_output=True, text=True, timeout=30)
        out = result.stdout[:3000]
        try:
            data = json.loads(out)
            return {"success": True, "design": data}
        except json.JSONDecodeError:
            return {"success": True, "raw": out[:1000]}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
