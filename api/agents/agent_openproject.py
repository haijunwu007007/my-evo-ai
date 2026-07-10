"""
openproject_mgmt - OpenProject企业项目管理 - 甘特图/成本/工时管理
"""
import logging
logger = logging.getLogger("evo.agent_openproject")

import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("OPENPROJECT_API_KEY_URL", "") or "https://community.openproject.org"
_API_KEY = os.environ.get("OPENPROJECT_API_KEY_KEY", "") or os.environ.get("OPENPROJECT_API_KEY", "")
_TIMEOUT = 15

def openproject_mgmt(**kwargs):
    """OpenProject项目管理 - 通过OpenProject API管理项目
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 OPENPROJECT_API_KEY_URL", "message": "未配置"}
        
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


def openproject_mgmt_helper(**kwargs):
    """OpenProject项目管理 - 通过OpenProject API管理项目 - 辅助操作"""
    return openproject_mgmt(**kwargs)
