"""
novu_notify - Novu统一通知 - Email/SMS/Push/In-App, 单API发所有通道
"""
import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("NOVU_API_KEY_URL", "") or "https://api.novu.co"
_API_KEY = os.environ.get("NOVU_API_KEY_KEY", "") or os.environ.get("NOVU_API_KEY", "")
_TIMEOUT = 15

def novu_notify(**kwargs):
    """Novu统一通知 - 通过Novu API发送通知
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 NOVU_API_KEY_URL", "message": "未配置"}
        
        headers = {"Content-Type": "application/json"}
        if _API_KEY:
            headers["Authorization"] = f"Bearer {_API_KEY}"
        
        action = kwargs.pop("action", "status")
        params = kwargs.get("params", kwargs)
        
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_API_BASE}/api/{action}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "data": data, "message": f"{action}成功"}
    except Exception as e:
        return {"ok": False, "data": f"{action}失败: {e}", "message": str(e)}


def novu_notify_helper(**kwargs):
    """Novu统一通知 - 通过Novu API发送通知 - 辅助操作"""
    return novu_notify(**kwargs)
