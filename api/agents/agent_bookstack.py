"""
bookstack_wiki - BookStack文档系统 - 书架→章节→页面层级
"""
import logging
logger = logging.getLogger("evo.agent_bookstack")

import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("BOOKSTACK_API_KEY_URL", "") or ""
_API_KEY = os.environ.get("BOOKSTACK_API_KEY_KEY", "") or os.environ.get("BOOKSTACK_API_KEY", "")
_TIMEOUT = 15

def bookstack_wiki(**kwargs):
    """BookStack文档系统 - 通过BookStack API管理文档
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 BOOKSTACK_API_KEY_URL", "message": "未配置"}
        
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


def bookstack_wiki_helper(**kwargs):
    """BookStack文档系统 - 通过BookStack API管理文档 - 辅助操作"""
    return bookstack_wiki(**kwargs)
